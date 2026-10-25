import os
import re
import time
import hashlib
from decimal import Decimal
from typing import Dict, Any, Optional
from django.db import transaction, OperationalError
from apps.common.validators import (
    validate_pdf_file,
    validate_print_settings,
    parse_page_range,
)
from apps.common.storage import private_storage
from apps.devices.models import PrintStation
from apps.audit.services import record_audit_event
from .models import Order, PrintJob, PrintJobAttempt
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


def create_order_with_files(
    files_list: list,
    settings_list: list,
    customer_data: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    client_ip: Optional[str] = None
) -> Order:
    """
    Creates ONE Order record and attaches MULTIPLE uploaded PDF files (PrintJobs)
    under that same Order ID, all within a single reliable database transaction.
    """
    for attempt in range(20):
        try:
            return _create_order_with_files_impl(
                files_list=files_list,
                settings_list=settings_list,
                customer_data=customer_data,
                idempotency_key=idempotency_key,
                client_ip=client_ip
            )
        except OperationalError as err:
            if "locked" in str(err).lower() and attempt < 19:
                time.sleep(0.04 * (attempt + 1))
                continue
            raise


def _create_order_with_files_impl(
    files_list: list,
    settings_list: list,
    customer_data: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    client_ip: Optional[str] = None
) -> Order:
    from apps.shops.models import Shop
    from apps.shops.services import get_or_create_default_shop

    delivery_method = customer_data.get('delivery_method', 'pickup')
    payment_method = customer_data.get('payment_method', 'cash_on_delivery')
    payment_status = 'cash_pending' if payment_method in ['cash_on_delivery', 'cash', 'cod', None] else 'unpaid'

    # Resolve destination shop
    shop_identifier = customer_data.get('shop_id') or customer_data.get('shop')
    shop = None
    if shop_identifier:
        shop = Shop.objects.filter(shop_id=shop_identifier, is_active=True).first()
        if not shop:
            try:
                shop = Shop.objects.filter(id=shop_identifier, is_active=True).first()
            except Exception:
                pass
    if not shop:
        shop = get_or_create_default_shop()

    with transaction.atomic():
        order = Order.create_with_unique_number(
            shop=shop,
            access_token=PrintJob.generate_access_token(),
            customer_name=customer_data.get('full_name', 'Customer'),
            customer_email=customer_data.get('email', ''),
            customer_phone=customer_data.get('phone', '0300-0000000'),
            delivery_method=delivery_method,
            delivery_address=customer_data.get('shipping_address', ''),
            notes=customer_data.get('notes', ''),
            status='queued',
            approval_status='awaiting_review',
            payment_status=payment_status,
        )

        total_impressions_sum = 0
        total_sheets_sum = 0
        subtotal_sum = Decimal('0.00')

        for idx, uploaded_file in enumerate(files_list):
            file_settings = (
                settings_list[idx]
                if idx < len(settings_list) and isinstance(settings_list[idx], dict)
                else {}
            )

            page_count, file_bytes = validate_pdf_file(uploaded_file)
            file_sha256 = hashlib.sha256(file_bytes).hexdigest()

            validated_settings = validate_print_settings(file_settings, total_pages=page_count)
            selected_pages_count = validated_settings['selected_pages_count']
            copies = validated_settings['copies']
            sides = validated_settings['sides']
            colour_mode = validated_settings['colour_mode']
            paper_size = validated_settings['paper_size']

            file_impressions = selected_pages_count * copies
            if sides == 'double':
                file_sheets = -(-selected_pages_count // 2) * copies
            else:
                file_sheets = selected_pages_count * copies

            file_pricing = calculate_server_price(
                total_impressions=file_impressions,
                estimated_sheets=file_sheets,
                colour_mode=colour_mode,
                paper_size=paper_size,
                delivery_method='pickup'
            )

            storage_key = private_storage.save_file(file_bytes, file_extension='.pdf')

            raw_name = getattr(uploaded_file, 'name', f'document_{idx+1}.pdf')
            clean_name = os.path.basename(str(raw_name)).replace('\\', '/').split('/')[-1]
            clean_name = re.sub(r'[\r\n\t"\'<>]', '', clean_name).strip()[:180] or f'document_{idx+1}.pdf'

            PrintJob.objects.create(
                order=order,
                shop=order.shop,
                job_number=order.order_number,  # Same unique Order ID for all PDFs!
                access_token=order.access_token,
                customer_name=order.customer_name,
                customer_email=order.customer_email,
                customer_phone=order.customer_phone,
                delivery_method=order.delivery_method,
                delivery_address=order.delivery_address,
                notes=order.notes,
                original_filename=clean_name,
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
                total_impressions=file_impressions,
                estimated_sheets=file_sheets,
                subtotal=file_pricing['subtotal'],
                delivery_fee=Decimal('0.00'),
                tax=file_pricing['tax'],
                total_amount=file_pricing['total_amount'],
                currency='PKR',
                status=order.status,
                approval_status=order.approval_status,
                payment_status=order.payment_status,
            )

            total_impressions_sum += file_impressions
            total_sheets_sum += file_sheets
            subtotal_sum += file_pricing['subtotal']

        delivery_fee = PRICING_RATES['delivery'].get(delivery_method, Decimal('0.00'))
        tax = (subtotal_sum * PRICING_RATES['tax_rate']).quantize(Decimal('0.01'))
        total_amount = subtotal_sum + delivery_fee + tax

        order.total_impressions = total_impressions_sum or 1
        order.estimated_sheets = total_sheets_sum or 1
        order.subtotal = subtotal_sum
        order.delivery_fee = delivery_fee
        order.tax = tax
        order.total_amount = total_amount
        order.save()

        record_audit_event(
            event_type='order_created',
            actor_type='customer',
            actor_identifier=order.customer_phone or order.customer_name,
            job_id=str(order.id),
            ip_address=client_ip,
            metadata={
                'order_number': order.order_number,
                'files_count': len(files_list),
                'impressions': total_impressions_sum,
                'total_amount': str(total_amount),
            }
        )

    return order


def create_print_job_from_upload(
    uploaded_file,
    settings_data: Dict[str, Any],
    customer_data: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    client_ip: Optional[str] = None
) -> PrintJob:
    """
    Creates a single-file print job wrapped cleanly in an Order.
    """
    order = create_order_with_files(
        files_list=[uploaded_file],
        settings_list=[settings_data],
        customer_data=customer_data,
        idempotency_key=idempotency_key,
        client_ip=client_ip
    )
    return order.files.first()


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
