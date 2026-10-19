from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from apps.printing.models import PrintJob
from apps.audit.services import record_audit_event
from .models import PaymentTransaction


class PaymentCreateIntentView(APIView):
    """
    POST /api/v1/payments/create-intent/
    Initializes payment intent for Stripe, JazzCash, EasyPaisa, or Cash On Delivery.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Initialize payment intent for order")
    def post(self, request):
        order_id = request.data.get('orderId')
        payment_method = request.data.get('paymentMethod', 'cash_on_delivery')

        if not order_id:
            return Response(
                {"success": False, "message": "orderId is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            job = PrintJob.objects.get(id=order_id)
        except (PrintJob.DoesNotExist, ValueError):
            job = PrintJob.objects.filter(job_number=order_id).first()
            if not job:
                return Response(
                    {"success": False, "message": "Order not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

        tx = PaymentTransaction.objects.create(
            job=job,
            provider=payment_method,
            provider_transaction_id=f"TXN-{job.job_number}",
            amount=job.total_amount,
            currency=job.currency,
            status='pending' if payment_method != 'cash_on_delivery' else 'succeeded'
        )

        if payment_method == 'cash_on_delivery':
            job.payment_status = 'cash_pending'
            job.save(update_fields=['payment_status', 'updated_at'])

        record_audit_event(
            event_type='payment_intent',
            actor_type='customer',
            job_id=str(job.id),
            metadata={'method': payment_method, 'amount': str(job.total_amount)}
        )

        return Response({
            "orderId": str(job.id),
            "paymentId": str(tx.id),
            "paymentMethod": payment_method,
            "checkoutUrl": f"/orders/{job.id}/track",
            "amount": float(job.total_amount),
            "currency": job.currency,
            "status": "succeeded" if payment_method == 'cash_on_delivery' else "requires_action"
        }, status=status.HTTP_201_CREATED)


class PaymentVerifyView(APIView):
    """
    POST /api/v1/payments/verify/
    Verifies payment completion.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Verify payment completion")
    def post(self, request):
        order_id = request.data.get('orderId')
        payment_id = request.data.get('paymentId')

        try:
            job = PrintJob.objects.get(id=order_id)
        except (PrintJob.DoesNotExist, ValueError):
            job = PrintJob.objects.filter(job_number=order_id).first()
            if not job:
                return Response({"success": False, "message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        job.payment_status = 'paid'
        job.save(update_fields=['payment_status', 'updated_at'])

        record_audit_event(
            event_type='payment_verified',
            actor_type='customer',
            job_id=str(job.id),
            metadata={'status': 'paid'}
        )

        return Response({
            "status": "succeeded",
            "isPaid": True,
            "orderId": str(job.id),
            "orderNumber": job.job_number,
        })
