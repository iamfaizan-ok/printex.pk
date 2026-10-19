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
from .models import PrintJob
from .serializers import (
    PrintJobCreateSerializer,
    PrintJobDetailsSerializer,
    PrintJobStatusSerializer,
)
from .services import (
    create_print_job_from_upload,
    calculate_server_price,
    PRICING_RATES,
)
from .printer_service import (
    execute_immediate_print_for_job,
    get_system_default_printer,
)
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
    Returns details of the job. Verified by access_token or public ID.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Get print job details")
    def get(self, request, job_id):
        job = self._get_job(job_id)
        serializer = PrintJobDetailsSerializer(job, context={'request': request})
        return Response({"success": True, "data": serializer.data})

    def _get_job(self, job_id) -> PrintJob:
        try:
            return PrintJob.objects.get(id=job_id)
        except (PrintJob.DoesNotExist, ValueError):
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
    POST /api/v1/orders/create/
    Direct order creation from frontend draft payload.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        customer = data.get('customer', {})
        items = data.get('items', [])
        delivery_method = data.get('deliveryMethod', 'pickup')

        first_item = items[0] if items else {}
        copies = int(first_item.get('copies', 1))
        page_count = int(first_item.get('pageCount', 1))
        sides = first_item.get('sides', 'single')
        colour_mode = first_item.get('colourMode', 'bw')
        paper_size = first_item.get('paperSize', 'A4')
        page_range = first_item.get('pageRange', 'all')

        total_impressions = page_count * copies
        estimated_sheets = -(-page_count // 2) * copies if sides == 'double' else page_count * copies

        pricing = calculate_server_price(
            total_impressions=total_impressions,
            estimated_sheets=estimated_sheets,
            colour_mode=colour_mode,
            paper_size=paper_size,
            delivery_method=delivery_method
        )

        job = PrintJob.objects.create(
            job_number=PrintJob.generate_job_number(),
            access_token=PrintJob.generate_access_token(),
            customer_name=customer.get('fullName', 'Customer'),
            customer_email=customer.get('email', ''),
            customer_phone=customer.get('phone', '0300-0000000'),
            delivery_method=delivery_method,
            delivery_address=customer.get('shippingAddress', ''),
            notes=customer.get('notes', ''),
            original_filename=first_item.get('fileName', 'document.pdf'),
            storage_key=first_item.get('documentId', 'docs/sample.pdf'),
            file_size_bytes=int(first_item.get('fileSizeBytes', 1024)),
            page_count=page_count,
            selected_pages_count=page_count,
            paper_size=paper_size,
            colour_mode=colour_mode,
            orientation=first_item.get('orientation', 'portrait'),
            sides=sides,
            copies=copies,
            page_range=page_range,
            total_impressions=total_impressions,
            estimated_sheets=estimated_sheets,
            subtotal=pricing['subtotal'],
            delivery_fee=pricing['delivery_fee'],
            tax=pricing['tax'],
            total_amount=pricing['total_amount'],
            status='queued'
        )

        # If document already in private storage and cash/auto_print, trigger immediate print
        if data.get('payment_method') in ['cash_on_delivery', 'cash', None] or data.get('auto_print'):
            execute_immediate_print_for_job(job)

        return Response({
            "orderId": str(job.id),
            "orderNumber": job.job_number,
            "status": "pending_payment",
            "createdAt": job.created_at.isoformat(),
            "updatedAt": job.updated_at.isoformat(),
            "customer": customer,
            "totalImpressions": total_impressions,
            "totalSheets": estimated_sheets,
            "pricing": {
                "currency": "PKR",
                "subtotal": float(pricing['subtotal']),
                "deliveryFee": float(pricing['delivery_fee']),
                "tax": float(pricing['tax']),
                "totalAmount": float(pricing['total_amount']),
                "items": []
            },
            "paymentStatus": "unpaid",
            "trackingNumber": job.job_number,
        }, status=status.HTTP_201_CREATED)
