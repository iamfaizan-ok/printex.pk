import hashlib
from decimal import Decimal
from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone
from apps.common.validators import (
    validate_pdf_file,
    validate_print_settings,
    parse_page_range,
)
from apps.common.storage import private_storage
from apps.devices.models import PrintStation
from apps.audit.services import record_audit_event
from .models import PrintJob, PrintJobAttempt
from .state_machine import transition_job_status


# Server-side pricing rates in PKR (never trust client prices!)
PRICING_RATES = {
    'bw_per_impression': Decimal('5.00'),       # PKR 5 per B&W impression
    'colour_per_impression': Decimal('25.00'),   # PKR 25 per Color impression
    'paper_surcharge': {
        'A4': Decimal('0.00'),
        'Letter': Decimal('0.00'),
        'Legal': Decimal('2.00'),
        'A3': Decimal('15.00'),
    },
    'delivery': {
        'pickup': Decimal('0.00'),
        'standard_delivery': Decimal('150.00'),
        'express_delivery': Decimal('300.00'),
    },
    'tax_rate': Decimal('0.00'),  # 0% standard tax for student/doc printing
}


def calculate_server_price(
    total_impressions: int,
    estimated_sheets: int,
    colour_mode: str,
    paper_size: str,
    delivery_method: str = 'pickup'
) -> Dict[str, Decimal]:
    """
    Server-authoritative pricing calculation. Never trust client prices!
    """
    base_rate = (
        PRICING_RATES['colour_per_impression']
        if colour_mode == 'colour'
        else PRICING_RATES['bw_per_impression']
    )
    paper_extra = PRICING_RATES['paper_surcharge'].get(paper_size, Decimal('0.00'))
    delivery_fee = PRICING_RATES['delivery'].get(delivery_method, Decimal('0.00'))

    impression_cost = (base_rate + paper_extra) * Decimal(total_impressions)
    subtotal = impression_cost
    tax = (subtotal * PRICING_RATES['tax_rate']).quantize(Decimal('0.01'))
    total = subtotal + delivery_fee + tax

    return {
        'subtotal': subtotal.quantize(Decimal('0.01')),
        'delivery_fee': delivery_fee.quantize(Decimal('0.01')),
        'tax': tax.quantize(Decimal('0.01')),
        'total_amount': total.quantize(Decimal('0.01')),
        'unit_rate': (base_rate + paper_extra).quantize(Decimal('0.01')),
    }


def create_print_job_from_upload(
    uploaded_file,
    settings_data: Dict[str, Any],
    customer_data: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    client_ip: Optional[str] = None
) -> PrintJob:
    """
    Full server-side job creation workflow:
    1. Check idempotency.
    2. Validate PDF signature, parse page count, check corruption/encryption.
    3. Validate print settings (copies, range, duplex, color, paper).
    4. Calculate server-side impressions, sheets, and authoritative price.
    5. Save file in private storage with unguessable key.
    6. Persist PrintJob atomically within database transaction.
    7. Record security audit event.
    """
    # 1. Idempotency check
    if idempotency_key:
        existing = PrintJob.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing

    # 2. PDF validation
    page_count, file_bytes = validate_pdf_file(uploaded_file)
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()

    # 3. Settings validation
    validated_settings = validate_print_settings(settings_data, total_pages=page_count)
    selected_pages_count = validated_settings['selected_pages_count']
    copies = validated_settings['copies']
    sides = validated_settings['sides']
    colour_mode = validated_settings['colour_mode']
    paper_size = validated_settings['paper_size']

    # Calculations
    total_impressions = selected_pages_count * copies
    if sides == 'double':
        estimated_sheets = -(-selected_pages_count // 2) * copies  # ceiling division
    else:
        estimated_sheets = selected_pages_count * copies

    delivery_method = customer_data.get('delivery_method', 'pickup')
    pricing = calculate_server_price(
        total_impressions=total_impressions,
        estimated_sheets=estimated_sheets,
        colour_mode=colour_mode,
        paper_size=paper_size,
        delivery_method=delivery_method
    )

    # 4. Save into private document storage
    storage_key = private_storage.save_file(file_bytes, file_extension='.pdf')

    # 5. Persist inside transaction
    with transaction.atomic():
        job = PrintJob.objects.create(
            job_number=PrintJob.generate_job_number(),
            access_token=PrintJob.generate_access_token(),
            idempotency_key=idempotency_key,
            customer_name=customer_data.get('full_name', 'Customer'),
            customer_email=customer_data.get('email', ''),
            customer_phone=customer_data.get('phone', '0300-0000000'),
            delivery_method=delivery_method,
            delivery_address=customer_data.get('shipping_address', ''),
            notes=customer_data.get('notes', ''),
            original_filename=getattr(uploaded_file, 'name', 'document.pdf'),
            storage_key=storage_key,
            file_size_bytes=len(file_bytes),
            file_sha256=file_sha256,
            page_count=page_count,
            selected_pages_count=selected_pages_count,
            paper_size=paper_size,
            colour_mode=colour_mode,
            orientation=validated_settings['orientation'],
            sides=sides,
            copies=copies,
            page_range=validated_settings['page_range'],
            total_impressions=total_impressions,
            estimated_sheets=estimated_sheets,
            subtotal=pricing['subtotal'],
            delivery_fee=pricing['delivery_fee'],
            tax=pricing['tax'],
            total_amount=pricing['total_amount'],
            currency='PKR',
            status='queued',
            payment_status='cash_pending' if customer_data.get('payment_method') in ['cash_on_delivery', 'cash', 'cod', None] else 'unpaid'
        )

        record_audit_event(
            event_type='job_created',
            actor_type='customer',
            actor_identifier=job.customer_phone or job.customer_name,
            job_id=str(job.id),
            ip_address=client_ip,
            metadata={
                'job_number': job.job_number,
                'impressions': total_impressions,
                'total_amount': str(pricing['total_amount']),
                'storage_key': storage_key
            }
        )

    return job


def claim_next_job_for_station(station: PrintStation) -> Optional[PrintJob]:
    """
    Atomic job claim using select_for_update() row-locking:
    Prevents two agents or concurrent workers from claiming the same job.
    """
    with transaction.atomic():
        # Find oldest eligible queued job that is approved and paid (never blocked)
        job = (
            PrintJob.objects.select_for_update(skip_locked=True)
            .filter(
                status='queued',
                approval_status='approved',
                payment_status__in=['cash_received', 'paid']
            )
            .order_by('created_at')
            .first()
        )

        if not job or job.approval_status == 'blocked':
            return None


        # Check if station supports required capabilities (e.g. colour)
        capabilities = station.capabilities or {}
        if job.colour_mode == 'colour' and not capabilities.get('colour', True):
            return None  # Cannot handle colour

        # Perform atomic claim
        job.assigned_station = station
        transition_job_status(job, 'claimed', actor=f"Station:{station.station_code}")

        # Record attempt
        attempt_num = job.attempts.count() + 1
        PrintJobAttempt.objects.create(
            job=job,
            station=station,
            attempt_number=attempt_num,
            status='claimed'
        )

        record_audit_event(
            event_type='job_claimed',
            actor_type='agent',
            actor_identifier=station.station_code,
            job_id=str(job.id),
            station_id=str(station.id),
            metadata={'job_number': job.job_number, 'attempt': attempt_num}
        )

        return job
