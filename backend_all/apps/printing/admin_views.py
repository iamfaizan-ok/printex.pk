import logging
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from apps.common.permissions import IsAdminOrStaff
from apps.audit.services import record_audit_event
from .models import PrintJob
from .state_machine import transition_job_status
from .printer_service import execute_immediate_print_for_job
from .admin_serializers import (
    AdminLoginSerializer,
    AdminUserSerializer,
    AdminBlockSerializer,
    AdminPrintJobSummarySerializer,
    AdminPrintJobDetailSerializer,
)

logger = logging.getLogger("PrintX.AdminApi")
User = get_user_model()


# ============================================================================
# 1. ADMIN AUTHENTICATION
# ============================================================================

class AdminLoginView(APIView):
    """
    POST /api/v1/admin/auth/login/
    Authenticates staff/admin user and establishes a secure Django session.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Admin login", request=AdminLoginSerializer)
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        # Support username or email login
        user = authenticate(request, username=username, password=password)
        if not user and '@' in username:
            try:
                user_obj = User.objects.get(email__iexact=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                user = None

        if not user:
            return Response(
                {"success": False, "message": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not (user.is_staff or user.is_superuser):
            logger.warning(f"Unauthorized login attempt by non-staff user '{username}'.")
            return Response(
                {"success": False, "message": "Access denied. Admin/staff credentials required."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Establish server-side session
        login(request, user)

        # Ensure CSRF token is generated and returned
        csrf_token = get_token(request)

        record_audit_event(
            event_type='security_warning',
            actor_type='admin',
            actor_identifier=user.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'action': 'admin_login_success'}
        )

        return Response({
            "success": True,
            "message": "Signed in successfully.",
            "data": AdminUserSerializer(user).data,
            "csrfToken": csrf_token,
        }, status=status.HTTP_200_OK)


class AdminLogoutView(APIView):
    """
    POST /api/v1/admin/auth/logout/
    Terminates the server-side admin session.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Admin logout")
    def post(self, request):
        user_name = request.user.username
        logout(request)

        record_audit_event(
            event_type='security_warning',
            actor_type='admin',
            actor_identifier=user_name,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'action': 'admin_logout'}
        )

        return Response({
            "success": True,
            "message": "Logged out successfully."
        }, status=status.HTTP_200_OK)


class AdminMeView(APIView):
    """
    GET /api/v1/admin/auth/me/
    Returns authenticated admin profile or 401 if unauthenticated.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Get current admin profile")
    def get(self, request):
        csrf_token = get_token(request)
        return Response({
            "success": True,
            "data": AdminUserSerializer(request.user).data,
            "csrfToken": csrf_token,
        })


# ============================================================================
# 2. ALL ORDER PRINTS DASHBOARD (LIST, SEARCH, FILTER, PAGINATION)
# ============================================================================

class AdminPrintJobListView(APIView):
    """
    GET /api/v1/admin/print-jobs/
    Compact order listing with real-time stats, search, tab filters, and pagination.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="List print jobs with filters and stats")
    def get(self, request):
        base_qs = PrintJob.objects.select_related('assigned_station').all()

        # 1. Summary Statistics for Top Counter Badges
        stats = {
            'total': base_qs.count(),
            'cash_pending': base_qs.filter(payment_status='cash_pending').count(),
            'blocked': base_qs.filter(approval_status='blocked').count(),
            'queued': base_qs.filter(status='queued').count(),
            'printing': base_qs.filter(status__in=['submitting_to_printer', 'submitted_to_printer', 'downloading', 'ready_to_print']).count(),
            'completed': base_qs.filter(status='completed').count(),
            'failed': base_qs.filter(status='failed').count(),
        }

        qs = base_qs

        # 2. Tab Filter
        tab = request.query_params.get('tab', 'all').lower()
        if tab == 'cash_pending':
            qs = qs.filter(payment_status='cash_pending')
        elif tab == 'blocked':
            qs = qs.filter(approval_status='blocked')
        elif tab == 'queued':
            qs = qs.filter(status='queued')
        elif tab == 'printing':
            qs = qs.filter(status__in=['submitting_to_printer', 'submitted_to_printer', 'downloading', 'ready_to_print'])
        elif tab == 'completed':
            qs = qs.filter(status='completed')
        elif tab == 'failed':
            qs = qs.filter(status='failed')

        # 3. Specific Field Filters
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        approval_filter = request.query_params.get('approval_status')
        if approval_filter:
            qs = qs.filter(approval_status=approval_filter)

        payment_filter = request.query_params.get('payment_status')
        if payment_filter:
            qs = qs.filter(payment_status=payment_filter)

        # 4. Search Filter (by Order ID, Filename, Customer details)
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(job_number__icontains=search) |
                Q(original_filename__icontains=search) |
                Q(customer_name__icontains=search) |
                Q(customer_phone__icontains=search)
            )

        # 5. Ordering
        ordering = request.query_params.get('ordering', '-created_at')
        allowed_orderings = ['-created_at', 'created_at', 'total_amount', '-total_amount', 'status']
        if ordering in allowed_orderings:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-created_at')

        # 6. Pagination
        total_filtered = qs.count()
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1

        try:
            page_size = min(max(5, int(request.query_params.get('page_size', 15))), 100)
        except ValueError:
            page_size = 15

        start = (page - 1) * page_size
        end = start + page_size
        orders_page = qs[start:end]

        total_pages = max(1, (total_filtered + page_size - 1) // page_size)

        serializer = AdminPrintJobSummarySerializer(orders_page, many=True)

        return Response({
            "success": True,
            "data": serializer.data,
            "stats": stats,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalPages": total_pages,
                "totalCount": total_filtered,
                "hasNext": page < total_pages,
                "hasPrev": page > 1,
            }
        })


class AdminPrintJobDetailView(APIView):
    """
    GET /api/v1/admin/print-jobs/{id}/
    Detailed view for single order including attempt history and audit log.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Get full print job details with audit log")
    def get(self, request, job_id):
        job = self._get_job(job_id)
        serializer = AdminPrintJobDetailSerializer(job)
        return Response({"success": True, "data": serializer.data})

    def _get_job(self, job_id) -> PrintJob:
        try:
            return PrintJob.objects.get(id=job_id)
        except (PrintJob.DoesNotExist, ValueError):
            job = PrintJob.objects.filter(job_number=job_id).first()
            if not job:
                from rest_framework.exceptions import NotFound
                raise NotFound("Print job not found.")
            return job


# ============================================================================
# 3. ORDER ACTION WORKFLOWS (BLOCK, UNBLOCK, PAY OK, PRINT)
# ============================================================================

class AdminPrintJobBlockView(APIView):
    """
    POST /api/v1/admin/print-jobs/{id}/block/
    Blocks an order from being queued, claimed, or printed.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Block print job", request=AdminBlockSerializer)
    def post(self, request, job_id):
        serializer = AdminBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', 'Blocked by administrator')

        with transaction.atomic():
            try:
                job = PrintJob.objects.select_for_update().get(id=job_id)
            except (PrintJob.DoesNotExist, ValueError):
                job = PrintJob.objects.select_for_update().filter(job_number=job_id).first()
                if not job:
                    return Response({"success": False, "message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            if not job.can_be_blocked():
                return Response(
                    {
                        "success": False,
                        "message": f"Order {job.job_number} cannot be blocked in status '{job.status}'. Printing has already completed or cancelled."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Record block metadata
            job.approval_status = 'blocked'
            job.blocked_by = request.user
            job.blocked_at = timezone.now()
            job.blocked_reason = reason
            job.save(update_fields=['approval_status', 'blocked_by', 'blocked_at', 'blocked_reason', 'updated_at'])

            record_audit_event(
                event_type='job_blocked',
                actor_type='admin',
                actor_identifier=request.user.username,
                job_id=str(job.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'reason': reason, 'job_number': job.job_number}
            )

            logger.info(f"Admin {request.user.username} blocked job {job.job_number}.")

        return Response({
            "success": True,
            "message": f"Order {job.job_number} has been blocked successfully.",
            "data": AdminPrintJobSummarySerializer(job).data,
        }, status=status.HTTP_200_OK)


class AdminPrintJobUnblockView(APIView):
    """
    POST /api/v1/admin/print-jobs/{id}/unblock/
    Unblocks a previously blocked job. Does NOT automatically mark cash received.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Unblock print job")
    def post(self, request, job_id):
        with transaction.atomic():
            try:
                job = PrintJob.objects.select_for_update().get(id=job_id)
            except (PrintJob.DoesNotExist, ValueError):
                job = PrintJob.objects.select_for_update().filter(job_number=job_id).first()
                if not job:
                    return Response({"success": False, "message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            if not job.can_be_unblocked():
                return Response(
                    {"success": False, "message": f"Order {job.job_number} is not currently blocked."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Unblock into awaiting review (or approved if already paid)
            job.approval_status = 'approved' if job.payment_status in ['cash_received', 'paid'] else 'awaiting_review'
            job.blocked_by = None
            job.blocked_at = None
            job.blocked_reason = ""
            job.save(update_fields=['approval_status', 'blocked_by', 'blocked_at', 'blocked_reason', 'updated_at'])

            record_audit_event(
                event_type='job_unblocked',
                actor_type='admin',
                actor_identifier=request.user.username,
                job_id=str(job.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'job_number': job.job_number}
            )

            logger.info(f"Admin {request.user.username} unblocked job {job.job_number}.")

        return Response({
            "success": True,
            "message": f"Order {job.job_number} has been unblocked.",
            "data": AdminPrintJobSummarySerializer(job).data,
        }, status=status.HTTP_200_OK)


class AdminPrintJobPayOkView(APIView):
    """
    POST /api/v1/admin/print-jobs/{id}/pay-ok/
    Manual cash receipt confirmation by shop administrator.
    Confirms cash has been received physically at the counter.
    If the order is not blocked, authorizes printing and enqueues to spooler.
    If the order is blocked, Pay OK confirms payment but does NOT override the block.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Approve cash payment (Pay OK)")
    def post(self, request, job_id):
        with transaction.atomic():
            try:
                job = PrintJob.objects.select_for_update().get(id=job_id)
            except (PrintJob.DoesNotExist, ValueError):
                job = PrintJob.objects.select_for_update().filter(job_number=job_id).first()
                if not job:
                    return Response({"success": False, "message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            if job.payment_status == 'cash_received':
                return Response(
                    {"success": False, "message": f"Cash payment for order {job.job_number} was already approved."},
                    status=status.HTTP_409_CONFLICT
                )

            # 1. Update Payment Status to cash_received
            job.payment_status = 'cash_received'
            job.payment_approved_by = request.user
            job.payment_approved_at = timezone.now()

            # 2. Separation of Payment and Printing:
            # If order is unblocked, approve printing and enqueue
            dispatched = False
            dispatch_msg = ""
            if job.approval_status != 'blocked':
                job.approval_status = 'approved'
                job.approved_by = request.user
                job.approved_at = timezone.now()

                # Dispatch directly to physical printer
                dispatched, dispatch_msg = execute_immediate_print_for_job(job)
            else:
                logger.warning(f"Pay OK received for blocked job {job.job_number}. Block preserved.")

            job.save()

            record_audit_event(
                event_type='pay_ok_approved',
                actor_type='admin',
                actor_identifier=request.user.username,
                job_id=str(job.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={
                    'job_number': job.job_number,
                    'amount': str(job.total_amount),
                    'currency': job.currency,
                    'is_blocked': job.approval_status == 'blocked',
                    'dispatched': dispatched
                }
            )

            logger.info(f"Admin {request.user.username} approved cash payment for {job.job_number}.")

        msg = f"Cash payment confirmed for Order {job.job_number}."
        if job.approval_status == 'blocked':
            msg += " Note: Order is currently BLOCKED and will not print until explicitly unblocked."
        elif dispatched:
            msg += f" Sent to printer spooler ({job.target_printer_name})."
        else:
            msg += " Added to print queue."

        return Response({
            "success": True,
            "message": msg,
            "data": AdminPrintJobSummarySerializer(job).data,
        }, status=status.HTTP_200_OK)


class AdminPrintJobAuthorizePrintView(APIView):
    """
    POST /api/v1/admin/print-jobs/{id}/authorize-print/
    Admin manually authorizes printing for an unblocked, paid order.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Authorize print job")
    def post(self, request, job_id):
        with transaction.atomic():
            try:
                job = PrintJob.objects.select_for_update().get(id=job_id)
            except (PrintJob.DoesNotExist, ValueError):
                job = PrintJob.objects.select_for_update().filter(job_number=job_id).first()
                if not job:
                    return Response({"success": False, "message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            # Verification 1: Block check
            if job.approval_status == 'blocked':
                return Response(
                    {
                        "success": False,
                        "message": f"Order {job.job_number} is BLOCKED. You must unblock it before authorizing printing."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verification 2: Payment check
            if job.payment_status == 'cash_pending':
                # Cash payment is automatically confirmed upon admin print authorization
                job.payment_status = 'cash_received'
                job.payment_approved_by = request.user
                job.payment_approved_at = timezone.now()
            elif job.payment_status not in ['cash_received', 'paid']:
                return Response(
                    {
                        "success": False,
                        "message": f"Order {job.job_number} has not been paid yet (status: '{job.payment_status}'). Confirm cash with 'Pay OK' before printing."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verification 3: Terminal status check
            if job.status in ['submitted_to_printer', 'completed']:
                return Response(
                    {
                        "success": False,
                        "message": f"Order {job.job_number} has already been submitted to printer or completed."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Authorize print
            job.approval_status = 'approved'
            job.approved_by = request.user
            job.approved_at = timezone.now()

            # Dispatch directly to printer spooler
            dispatched, dispatch_msg = execute_immediate_print_for_job(job)
            job.save()

            record_audit_event(
                event_type='job_approved',
                actor_type='admin',
                actor_identifier=request.user.username,
                job_id=str(job.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'job_number': job.job_number, 'dispatched': dispatched}
            )

        return Response({
            "success": True,
            "message": f"Print job {job.job_number} authorized and dispatched to printer.",
            "data": AdminPrintJobSummarySerializer(job).data,
        }, status=status.HTTP_202_ACCEPTED)
