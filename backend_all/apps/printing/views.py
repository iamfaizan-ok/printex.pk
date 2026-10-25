import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.common.validators import (
    ALLOWED_PAPER_SIZES,
    ALLOWED_COLOUR_MODES,
    ALLOWED_ORIENTATIONS,
    ALLOWED_SIDES,
    MAX_COPIES_PER_DOCUMENT,
    MIN_COPIES_PER_DOCUMENT,
    MAX_FILE_SIZE_BYTES,
)
from apps.devices.models import PrintStation
from apps.audit.services import record_audit_event
from .models import Order, PrintJob
from .serializers import (
    PrintJobCreateSerializer,
    PrintJobDetailsSerializer,
    PrintJobStatusSerializer,
)
from .services import (
    create_print_job_from_upload,
    create_order_with_files,
    calculate_server_price,
    PRICING_RATES,
)
from .printer_service import execute_immediate_print_for_job
from .state_machine import transition_job_status

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="System health check", responses={200: dict})
    def get(self, request):
        return Response({
            "status": "online",
            "service": "printx-backend",
            "version": "1.0.0"
        })


class PrintOptionsView(APIView):
    """
    GET /api/v1/print-options/
    Returns supported paper sizes, color modes, duplex settings, copy limits, and printer capabilities.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Get available print options & printer capabilities")
    def get(self, request):
        active_stations = PrintStation.objects.filter(is_enabled=True, status='online')
        available_printers = []
        for station in active_stations:
            for printer_name in (station.allowed_printers or []):
                available_printers.append({
                    "station": station.name,
                    "printer_name": printer_name,
                    "capabilities": station.capabilities,
                })

        return Response({
            "paper_sizes": ALLOWED_PAPER_SIZES,
            "colour_modes": ALLOWED_COLOUR_MODES,
            "orientations": ALLOWED_ORIENTATIONS,
            "sides": ALLOWED_SIDES,
            "copy_limits": {
                "min": MIN_COPIES_PER_DOCUMENT,
                "max": MAX_COPIES_PER_DOCUMENT,
            },
            "max_file_size_bytes": MAX_FILE_SIZE_BYTES,
            "pricing_rates": {
                "currency": "PKR",
                "bw_per_impression": float(PRICING_RATES['bw_per_impression']),
                "colour_per_impression": float(PRICING_RATES['colour_per_impression']),
                "delivery": {
                    k: float(v) for k, v in PRICING_RATES['delivery'].items()
                }
            },
            "active_printers": available_printers,
        })


class PrintJobListCreateView(APIView):
    """
    POST /api/v1/print-jobs/
    Accepts multipart/form-data containing PDF and settings.
    Returns HTTP 202 Accepted with job ID and status URL.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(summary="Create a new print job", request=PrintJobCreateSerializer)
    def post(self, request):
        serializer = PrintJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        uploaded_file = data['file']

        settings_data = {
            'paper_size': data.get('paper_size', 'A4'),
            'colour_mode': data.get('colour_mode', 'bw'),
            'orientation': data.get('orientation', 'portrait'),
            'sides': data.get('sides', 'single'),
            'copies': data.get('copies', 1),
            'page_range': data.get('page_range', 'all'),
        }

        customer_data = {
            'full_name': data.get('customer_name', 'Customer'),
            'email': data.get('customer_email', ''),
            'phone': data.get('customer_phone', '0300-0000000'),
            'delivery_method': data.get('delivery_method', 'pickup'),
            'shipping_address': data.get('delivery_address', ''),
            'notes': data.get('notes', ''),
            'payment_method': data.get('payment_method', 'cash_on_delivery'),
            'shop_id': data.get('shop_id') or data.get('shop'),
        }

        idempotency_key = request.headers.get('Idempotency-Key')
        client_ip = request.META.get('REMOTE_ADDR')

        job = create_print_job_from_upload(
            uploaded_file=uploaded_file,
            settings_data=settings_data,
            customer_data=customer_data,
            idempotency_key=idempotency_key,
            client_ip=client_ip
        )

        # Dispatch directly to printer for immediate physical print
        is_cash = customer_data.get('payment_method') in ['cash_on_delivery', 'cash', 'cod']
        auto_print_param = request.data.get('auto_print')

        should_print = False
        if auto_print_param in ['false', 'False', False, '0', 0]:
            should_print = False
        elif is_cash or auto_print_param in ['true', 'True', True, '1', 1]:
            should_print = True

        print_success = False
        print_message = ""
        if should_print:
            print_success, print_message = execute_immediate_print_for_job(job)

        response_serializer = PrintJobDetailsSerializer(job, context={'request': request})
        res_data = dict(response_serializer.data)
        res_data['printer_dispatched'] = print_success
        res_data['printer_message'] = print_message
        res_data['target_printer'] = job.target_printer_name

        return Response(
            {
                "success": True,
                "message": (
                    f"Print job accepted and dispatched to physical printer '{job.target_printer_name}'."
                    if print_success
                    else "Print job accepted and queued for processing."
                ),
                "data": res_data,
            },
            status=status.HTTP_202_ACCEPTED
        )


class PrintJobDirectPrintView(APIView):
    """
    POST /api/v1/print-jobs/{job_id}/print/
    Immediately dispatches an existing print job to the physical printer.
    """
    permission_classes = [AllowAny]

    def post(self, request, job_id):
        try:
            job = PrintJob.objects.get(id=job_id)
        except (PrintJob.DoesNotExist, ValueError):
            job = PrintJob.objects.filter(job_number=job_id).first()
            if not job:
                from rest_framework.exceptions import NotFound
                raise NotFound("Print job not found.")

        printer_name = request.data.get('printer_name')
        success, message = execute_immediate_print_for_job(job, printer_name=printer_name)

        return Response({
            "success": success,
            "message": message,
            "job_number": job.job_number,
            "status": job.status,
            "target_printer": job.target_printer_name,
        })


class PrintJobDetailView(APIView):
    """
    GET /api/v1/print-jobs/{job_id}/
    GET /api/v1/orders/{order_id}/
    GET /api/v1/orders/track/?number=ORD id 123
    Returns full details of an order or print job.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Get print job or order tracking details")
    def get(self, request, job_id=None):
        lookup_id = job_id if job_id != 'track' else None
        if not lookup_id:
            lookup_id = (
                request.query_params.get('number')
                or request.query_params.get('orderNumber')
                or request.query_params.get('trackingNumber')
                or request.query_params.get('id')
            )

        if not lookup_id:
            return Response(
                {"success": False, "message": "Missing order or job identifier."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if matches an Order
        order = None
        try:
            order = Order.objects.filter(id=lookup_id).first()
        except Exception:
            pass
        if not order:
            order = Order.objects.filter(order_number=lookup_id).first()

        if order:
            files_data = [
                {
                    "id": str(f.id),
                    "originalFilename": f.original_filename,
                    "pageCount": f.page_count,
                    "copies": f.copies,
                    "colourMode": f.colour_mode,
                    "paperSize": f.paper_size,
                    "sides": f.sides,
                    "status": f.status,
                    "totalImpressions": f.total_impressions,
                    "estimatedSheets": f.estimated_sheets,
                    "amount": float(f.total_amount),
                }
                for f in order.files.all()
            ]
            # Protect customer privacy against enumeration on public tracking queries
            token_param = (
                request.query_params.get('token')
                or request.headers.get('X-Access-Token')
                or ''
            )
            is_authorized = bool(
                (request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))
                or (order.access_token and token_param == order.access_token)
            )

            def mask_phone(phone: str) -> str:
                if not phone:
                    return ""
                clean = re.sub(r'\D', '', phone)
                if len(clean) >= 7:
                    return f"{clean[:4]}****{clean[-3:]}"
                return "***"

            display_phone = order.customer_phone if is_authorized else mask_phone(order.customer_phone)
            display_name = order.customer_name if is_authorized else (order.customer_name[:1] + "***" if order.customer_name else "Customer")

            return Response({
                "success": True,
                "data": {
                    "id": str(order.id),
                    "orderNumber": order.order_number,
                    "jobNumber": order.order_number,
                    "status": order.status,
                    "customerName": display_name,
                    "customerPhone": display_phone,
                    "deliveryMethod": order.delivery_method,
                    "paymentStatus": order.payment_status,
                    "approvalStatus": order.approval_status,
                    "totalImpressions": order.total_impressions,
                    "estimatedSheets": order.estimated_sheets,
                    "subtotal": float(order.subtotal),
                    "deliveryFee": float(order.delivery_fee),
                    "tax": float(order.tax),
                    "totalAmount": float(order.total_amount),
                    "currency": order.currency,
                    "createdAt": order.created_at.isoformat(),
                    "updatedAt": order.updated_at.isoformat(),
                    "totalPdfs": order.files.count(),
                    "files": files_data,
                }
            })

        job = self._get_job(lookup_id)
        serializer = PrintJobDetailsSerializer(job, context={'request': request})
        return Response({"success": True, "data": serializer.data})

    def _get_job(self, job_id) -> PrintJob:
        try:
            return PrintJob.objects.get(id=job_id)
        except Exception:
            return PrintJob.objects.filter(job_number=job_id).first() or self._raise_404()

    def _raise_404(self):
        from rest_framework.exceptions import NotFound
        raise NotFound("The requested print job was not found.")


class PrintJobStatusView(APIView):
    """
    GET /api/v1/print-jobs/{job_id}/status/
    Lightweight status tracking endpoint for client polling.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Check live status of print job")
    def get(self, request, job_id):
        try:
            job = PrintJob.objects.get(id=job_id)
        except (PrintJob.DoesNotExist, ValueError):
            job = PrintJob.objects.filter(job_number=job_id).first()
            if not job:
                from rest_framework.exceptions import NotFound
                raise NotFound("Print job not found.")

        serializer = PrintJobStatusSerializer(job)
        return Response({"success": True, "data": serializer.data})


class PrintJobCancelView(APIView):
    """
    POST /api/v1/print-jobs/{job_id}/cancel/
    Cancels job if still in cancellable stage.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Cancel a pending print job")
    def post(self, request, job_id):
        try:
            job = PrintJob.objects.get(id=job_id)
        except (PrintJob.DoesNotExist, ValueError):
            from rest_framework.exceptions import NotFound
            raise NotFound("Print job not found.")

        if not job.can_be_cancelled():
            return Response(
                {
                    "success": False,
                    "message": f"Job cannot be cancelled in state '{job.status}'. Printing has already commenced or completed."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', 'Cancelled by customer')
        transition_job_status(job, 'cancelled', error_code='CANCELLED_BY_CUSTOMER', error_message=reason, actor='customer')

        record_audit_event(
            event_type='job_cancelled',
            actor_type='customer',
            job_id=str(job.id),
            metadata={'reason': reason}
        )

        return Response({
            "success": True,
            "message": f"Print job {job.job_number} has been cancelled successfully."
        })


# ============================================================================
# COMPATIBILITY VIEWS FOR USER FRONTEND (userApis.ts)
# ============================================================================

class DocumentUploadView(APIView):
    """
    POST /api/v1/documents/upload/
    Accepts multipart/form-data upload from user_frontend.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({"success": False, "message": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.common.validators import validate_pdf_file
        from apps.common.storage import private_storage

        page_count, file_bytes = validate_pdf_file(uploaded_file)
        storage_key = private_storage.save_file(file_bytes, file_extension='.pdf')

        import uuid
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"

        return Response({
            "documentId": doc_id,
            "originalFileName": uploaded_file.name,
            "fileSizeBytes": len(file_bytes),
            "fileUrl": f"/media/documents/{storage_key}",
            "storageKey": storage_key,
            "pageCount": page_count,
            "fileType": "pdf",
            "mimeType": "application/pdf",
            "uploadedAt": request.data.get('uploadedAt', '')
        }, status=status.HTTP_201_CREATED)


class PricingCalculateView(APIView):
    """
    POST /api/v1/pricing/calculate/
    Live server-side price calculation for frontend draft.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        items = request.data.get('items', [])
        delivery_method = request.data.get('delivery_method', 'pickup')

        total_subtotal = 0.0
        breakdown_items = []

        for item in items:
            page_count = int(item.get('pageCount', 1))
            copies = int(item.get('copies', 1))
            sides = item.get('sides', 'single')
            colour_mode = item.get('colourMode', 'bw')
            paper_size = item.get('paperSize', 'A4')

            total_impressions = page_count * copies
            estimated_sheets = -(-page_count // 2) * copies if sides == 'double' else page_count * copies

            price = calculate_server_price(
                total_impressions=total_impressions,
                estimated_sheets=estimated_sheets,
                colour_mode=colour_mode,
                paper_size=paper_size,
                delivery_method='pickup'  # per-item without delivery
            )

            total_subtotal += float(price['subtotal'])
            breakdown_items.append({
                "fileName": item.get('fileName', 'Document'),
                "pageImpressions": total_impressions,
                "estimatedSheets": estimated_sheets,
                "unitPricePerImpression": float(price['unit_rate']),
                "paperPrice": 0.0,
                "itemSubtotal": float(price['subtotal']),
            })

        delivery_fee = float(PRICING_RATES['delivery'].get(delivery_method, 0.0))
        total_amount = total_subtotal + delivery_fee

        return Response({
            "currency": "PKR",
            "subtotal": total_subtotal,
            "deliveryFee": delivery_fee,
            "tax": 0.0,
            "totalAmount": total_amount,
            "items": breakdown_items,
        })


class OrderCreateView(APIView):
    """
    POST /api/v1/orders/
    POST /api/v1/orders/create/
    Direct order creation supporting multiple PDF files under a single Order ID.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        import json
        from django.db import transaction
        from decimal import Decimal

        data = request.data
        customer = data.get('customer', {}) if isinstance(data.get('customer'), dict) else {}
        customer_name = (
            customer.get('fullName')
            or data.get('customer_name')
            or data.get('customerName')
            or 'Customer'
        )
        customer_phone = (
            customer.get('phone')
            or data.get('customer_phone')
            or data.get('customerPhone')
            or '0300-0000000'
        )
        customer_email = (
            customer.get('email')
            or data.get('customer_email')
            or data.get('customerEmail')
            or ''
        )
        delivery_method = (
            data.get('delivery_method')
            or data.get('deliveryMethod')
            or 'pickup'
        )
        delivery_address = (
            customer.get('shippingAddress')
            or data.get('delivery_address')
            or ''
        )
        notes = (
            customer.get('notes')
            or data.get('notes')
            or ''
        )
        payment_method = data.get('payment_method', 'cash_on_delivery')

        customer_data = {
            'full_name': customer_name,
            'email': customer_email,
            'phone': customer_phone,
            'delivery_method': delivery_method,
            'shipping_address': delivery_address,
            'notes': notes,
            'payment_method': payment_method,
            'shop_id': data.get('shop_id') or data.get('shop') or (customer.get('shop_id') if isinstance(customer, dict) else None),
        }

        # Case 1: Uploaded files via multipart/form-data
        uploaded_files = request.FILES.getlist('files') or request.FILES.getlist('file')
        if uploaded_files:
            file_settings_raw = data.get('file_settings') or data.get('settings')
            settings_list = []
            if file_settings_raw:
                if isinstance(file_settings_raw, str):
                    try:
                        settings_list = json.loads(file_settings_raw)
                    except Exception:
                        settings_list = []
                elif isinstance(file_settings_raw, list):
                    settings_list = file_settings_raw

            order = create_order_with_files(
                files_list=uploaded_files,
                settings_list=settings_list,
                customer_data=customer_data,
                client_ip=request.META.get('REMOTE_ADDR')
            )

            # Auto print dispatch if enabled and cash/unblocked
            auto_print = data.get('auto_print')
            is_cash = payment_method in ['cash_on_delivery', 'cash', 'cod']
            if auto_print not in ['false', False, '0', 0] and (is_cash or auto_print in ['true', True, '1', 1]):
                for child_job in order.files.all():
                    execute_immediate_print_for_job(child_job)

            child_files_data = [
                {
                    "id": str(f.id),
                    "fileName": f.original_filename,
                    "pageCount": f.page_count,
                    "copies": f.copies,
                    "colourMode": f.colour_mode,
                    "paperSize": f.paper_size,
                    "sides": f.sides,
                    "totalImpressions": f.total_impressions,
                    "estimatedSheets": f.estimated_sheets,
                    "amount": float(f.total_amount),
                }
                for f in order.files.all()
            ]

            return Response({
                "orderId": str(order.id),
                "orderNumber": order.order_number,
                "status": order.status,
                "createdAt": order.created_at.isoformat(),
                "updatedAt": order.updated_at.isoformat(),
                "customer": {
                    "fullName": order.customer_name,
                    "phone": order.customer_phone,
                    "email": order.customer_email,
                    "deliveryMethod": order.delivery_method,
                },
                "totalPdfs": order.files.count(),
                "files": child_files_data,
                "totalImpressions": order.total_impressions,
                "totalSheets": order.estimated_sheets,
                "pricing": {
                    "currency": order.currency,
                    "subtotal": float(order.subtotal),
                    "deliveryFee": float(order.delivery_fee),
                    "tax": float(order.tax),
                    "totalAmount": float(order.total_amount),
                },
                "paymentStatus": order.payment_status,
                "trackingNumber": order.order_number,
            }, status=status.HTTP_201_CREATED)

        # Case 2: JSON items fallback
        items = data.get('items') or data.get('files') or []
        payment_status = 'cash_pending' if payment_method in ['cash_on_delivery', 'cash', 'cod', None] else 'unpaid'

        from apps.shops.models import Shop
        from apps.shops.services import get_or_create_default_shop
        shop_identifier = customer_data.get('shop_id')
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
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                delivery_method=delivery_method,
                delivery_address=delivery_address,
                notes=notes,
                status='queued',
                approval_status='awaiting_review',
                payment_status=payment_status,
            )

            total_impressions_sum = 0
            total_sheets_sum = 0
            subtotal_sum = Decimal('0.00')

            for idx, itm in enumerate(items):
                item_settings = itm.get('settings', {}) if isinstance(itm.get('settings'), dict) else itm
                copies = int(item_settings.get('copies', 1))
                page_count = int(itm.get('pageCount', 1))
                sides = item_settings.get('sides', 'single')
                colour_mode = item_settings.get('colourMode') or item_settings.get('colour_mode') or 'bw'
                paper_size = item_settings.get('paperSize') or item_settings.get('paper_size') or 'A4'
                page_range = item_settings.get('pageRange') or item_settings.get('page_range') or 'all'
                orientation = item_settings.get('orientation', 'portrait')

                total_impressions = page_count * copies
                estimated_sheets = -(-page_count // 2) * copies if sides == 'double' else page_count * copies

                pricing = calculate_server_price(
                    total_impressions=total_impressions,
                    estimated_sheets=estimated_sheets,
                    colour_mode=colour_mode,
                    paper_size=paper_size,
                    delivery_method='pickup'
                )

                orig_filename = itm.get('fileName') or itm.get('original_filename') or f'document_{idx+1}.pdf'
                storage_key = itm.get('documentId') or itm.get('storage_key') or f'docs/file_{idx+1}.pdf'
                file_size_bytes = int(itm.get('fileSizeBytes') or itm.get('file_size_bytes') or 1024)

                PrintJob.objects.create(
                    order=order,
                    shop=order.shop,
                    job_number=order.order_number,
                    access_token=order.access_token,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    delivery_method=delivery_method,
                    delivery_address=delivery_address,
                    notes=notes,
                    original_filename=orig_filename,
                    storage_key=storage_key,
                    file_size_bytes=file_size_bytes,
                    page_count=page_count,
                    selected_pages_count=page_count,
                    paper_size=paper_size,
                    colour_mode=colour_mode,
                    orientation=orientation,
                    sides=sides,
                    copies=copies,
                    page_range=page_range,
                    total_impressions=total_impressions,
                    estimated_sheets=estimated_sheets,
                    subtotal=pricing['subtotal'],
                    delivery_fee=Decimal('0.00'),
                    tax=pricing['tax'],
                    total_amount=pricing['total_amount'],
                    currency='PKR',
                    status='queued',
                    payment_status=payment_status,
                )

                total_impressions_sum += total_impressions
                total_sheets_sum += estimated_sheets
                subtotal_sum += pricing['subtotal']

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

        # If auto_print or cash
        if payment_method in ['cash_on_delivery', 'cash', None] or data.get('auto_print'):
            for child_job in order.files.all():
                execute_immediate_print_for_job(child_job)

        child_files_data = [
            {
                "id": str(f.id),
                "fileName": f.original_filename,
                "pageCount": f.page_count,
                "copies": f.copies,
                "colourMode": f.colour_mode,
                "paperSize": f.paper_size,
                "sides": f.sides,
            }
            for f in order.files.all()
        ]

        return Response({
            "orderId": str(order.id),
            "orderNumber": order.order_number,
            "status": "pending_payment",
            "createdAt": order.created_at.isoformat(),
            "updatedAt": order.updated_at.isoformat(),
            "customer": customer,
            "totalPdfs": order.files.count(),
            "files": child_files_data,
            "totalImpressions": order.total_impressions,
            "totalSheets": order.estimated_sheets,
            "pricing": {
                "currency": "PKR",
                "subtotal": float(order.subtotal),
                "deliveryFee": float(order.delivery_fee),
                "tax": float(order.tax),
                "totalAmount": float(order.total_amount),
            },
            "paymentStatus": order.payment_status,
            "trackingNumber": order.order_number,
        }, status=status.HTTP_201_CREATED)
