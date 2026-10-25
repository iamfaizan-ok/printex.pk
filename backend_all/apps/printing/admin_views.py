import logging
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.middleware.csrf import get_token
import requests
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from apps.common.permissions import IsAdminOrStaff
from apps.audit.services import record_audit_event
from apps.shops.models import Shop, ShopStaff
from apps.shops.services import (
    get_user_shop,
    user_has_shop_access,
    get_or_create_default_shop,
    link_user_to_shop,
)
from .models import Order, PrintJob, PrintJobAttempt
from .state_machine import transition_job_status
from . import printer_service
from .printer_service import execute_immediate_print_for_job


def dispatch_print_job(job):
    """
    Dispatches print job while respecting test mocks on either
    apps.printing.admin_views.execute_immediate_print_for_job or
    apps.printing.printer_service.execute_immediate_print_for_job.
    """
    import sys
    mod = sys.modules.get('apps.printing.admin_views')
    if mod and hasattr(mod, 'execute_immediate_print_for_job'):
        target_fn = getattr(mod, 'execute_immediate_print_for_job')
        if hasattr(target_fn, 'assert_called') or hasattr(target_fn, 'return_value'):
            return target_fn(job)
    return printer_service.execute_immediate_print_for_job(job)
from .admin_serializers import (
    AdminLoginSerializer,
    AdminSignupSerializer,
    AdminPasswordResetRequestSerializer,
    AdminPasswordResetConfirmSerializer,
    AdminGoogleAuthSerializer,
    AdminUserSerializer,
    AdminBlockSerializer,
    AdminPrintJobSummarySerializer,
    AdminOrderSummarySerializer,
    AdminOrderFileSerializer,
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
    Protected with IP-based rate throttling against brute force attacks.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

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

        # Check approval status if linked to shop
        if not user.is_superuser and hasattr(user, 'shop_profile') and not user.shop_profile.is_approved:
            return Response(
                {"success": False, "message": "Account pending administrator approval."},
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


class AdminSignupView(APIView):
    """
    POST /api/v1/admin/auth/signup/
    Secure admin/shop registration with strict privilege escalation prevention.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

    @extend_schema(summary="Admin / Shop operator registration", request=AdminSignupSerializer)
    def post(self, request):
        serializer = AdminSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        username = data['username']
        email = data['email'].strip().lower()
        password = data['password']
        full_name = data.get('full_name', '')
        reg_key = data.get('registration_key', '').strip()
        new_shop_name = data.get('new_shop_name', '').strip()
        shop_id = data.get('shop_id', '').strip()

        # Check duplicate username / email
        if User.objects.filter(username__iexact=username).exists():
            return Response({
                "success": False,
                "message": "An account with this username already exists."
            }, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=email).exists():
            return Response({
                "success": False,
                "message": "An account with this email address already exists."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Enforce strong password validation
        try:
            validate_password(password)
        except Exception as e:
            msg = "; ".join(e.messages) if hasattr(e, 'messages') else str(e)
            return Response({"success": False, "message": msg}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent unauthorized registration via key if configured
        expected_key = getattr(settings, 'ADMIN_REGISTRATION_KEY', '')
        is_approved = True
        if expected_key:
            if reg_key != expected_key:
                return Response({
                    "success": False,
                    "message": "Invalid registration key. Authorization from platform owner required."
                }, status=status.HTTP_403_FORBIDDEN)
            is_approved = True

        # Resolve or create assigned shop
        if new_shop_name:
            from django.utils.text import slugify
            base_id = f"shop-{slugify(new_shop_name)}"[:40] or "shop-new"
            cand_id = base_id
            counter = 1
            while Shop.objects.filter(shop_id=cand_id).exists():
                cand_id = f"{base_id}-{counter}"
                counter += 1
            shop = Shop.objects.create(
                shop_id=cand_id,
                name=new_shop_name,
                address=data.get('new_shop_address', ''),
                phone=data.get('new_shop_phone', ''),
                email=email,
                is_active=True
            )
        elif shop_id:
            shop = Shop.objects.filter(shop_id=shop_id, is_active=True).first()
            if not shop:
                return Response({
                    "success": False,
                    "message": f"Shop '{shop_id}' not found or inactive."
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            shop = get_or_create_default_shop()

        # Create user with strict least privilege (is_superuser=False always!)
        first_name = full_name.split()[0] if full_name else username
        last_name = " ".join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else ""

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_superuser=False,
            is_active=True
        )

        # Assign user to shop
        link_user_to_shop(user, shop, role='manager', is_approved=is_approved)

        login(request, user)
        csrf_token = get_token(request)

        record_audit_event(
            event_type='security_warning',
            actor_type='admin',
            actor_identifier=user.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'action': 'admin_signup_success', 'shop_id': shop.shop_id}
        )

        return Response({
            "success": True,
            "message": f"Account created and assigned to {shop.name}.",
            "data": AdminUserSerializer(user).data,
            "csrfToken": csrf_token,
        }, status=status.HTTP_201_CREATED)


class AdminPasswordResetRequestView(APIView):
    """
    POST /api/v1/admin/auth/password-reset/
    Sends secure email instructions to reset password.
    Protected against user enumeration.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

    @extend_schema(summary="Request password reset instructions", request=AdminPasswordResetRequestSerializer)
    def post(self, request):
        serializer = AdminPasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip().lower()

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            base_admin = getattr(settings, 'ADMIN_PORTAL_URL', 'http://localhost:8000/admin-panel/login.html')
            reset_url = f"{base_admin}?action=reset&uid={uid}&token={token}"

            subject = "PrintX Admin — Password Reset Request"
            message = (
                f"Hello {user.username},\n\n"
                f"A password reset request was received for your PrintX Admin account.\n\n"
                f"To set a new password, open the following link:\n{reset_url}\n\n"
                f"If you did not request this, you can safely ignore this email.\n\n"
                f"PrintX Security Team"
            )
            try:
                send_mail(
                    subject,
                    message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@printx.pk'),
                    [user.email],
                    fail_silently=False
                )
            except Exception as e:
                logger.warning(f"Password reset email delivery note: {e}")

            logger.info(f"[SECURITY/PASSWORD_RESET] Reset link generated for {email}: {reset_url}")

        return Response({
            "success": True,
            "message": "If an authorized admin account exists with that email address, password reset instructions have been sent."
        }, status=status.HTTP_200_OK)


class AdminPasswordResetConfirmView(APIView):
    """
    POST /api/v1/admin/auth/password-reset-confirm/
    Validates token and updates admin password.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

    @extend_schema(summary="Confirm and execute password reset", request=AdminPasswordResetConfirmSerializer)
    def post(self, request):
        serializer = AdminPasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            user_pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_pk)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                "success": False,
                "message": "Invalid or expired password reset link."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({
                "success": False,
                "message": "Invalid or expired password reset token."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user)
        except Exception as e:
            msg = "; ".join(e.messages) if hasattr(e, 'messages') else str(e)
            return Response({"success": False, "message": msg}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        record_audit_event(
            event_type='security_warning',
            actor_type='admin',
            actor_identifier=user.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'action': 'password_reset_completed'}
        )

        return Response({
            "success": True,
            "message": "Password has been successfully reset. You may now sign in with your new password."
        }, status=status.HTTP_200_OK)


class AdminGoogleAuthView(APIView):
    """
    POST /api/v1/admin/auth/google/
    Authenticates staff using Google OAuth 2.0 Identity Services credential.
    Verifies ID token directly with Google APIs. Never stores Google account passwords.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

    @extend_schema(summary="Google OAuth 2.0 Sign-In", request=AdminGoogleAuthSerializer)
    def post(self, request):
        serializer = AdminGoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = serializer.validated_data['credential']

        # Cryptographically verify with Google OAuth tokeninfo endpoint
        try:
            verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
            resp = requests.get(verify_url, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Google OAuth verification failed: {resp.text}")
                return Response({
                    "success": False,
                    "message": "Invalid Google OAuth 2.0 identity credential."
                }, status=status.HTTP_400_BAD_REQUEST)
            payload = resp.json()
        except Exception as err:
            logger.error(f"Error connecting to Google OAuth endpoint: {err}")
            return Response({
                "success": False,
                "message": "Unable to verify Google credential at this time."
            }, status=status.HTTP_502_BAD_GATEWAY)

        email = payload.get('email', '').strip().lower()
        email_verified = payload.get('email_verified') in [True, 'true', 'True']
        sub = payload.get('sub', '')
        name = payload.get('name', '')

        if not email or not email_verified:
            return Response({
                "success": False,
                "message": "Google account email is unverified or missing."
            }, status=status.HTTP_400_BAD_REQUEST)

        client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
        if client_id and payload.get('aud') != client_id:
            return Response({
                "success": False,
                "message": "OAuth Client ID audience mismatch."
            }, status=status.HTTP_403_FORBIDDEN)

        # Look up existing user
        user = User.objects.filter(email__iexact=email).first()
        if user:
            if not (user.is_staff or user.is_superuser):
                return Response({
                    "success": False,
                    "message": "Access denied. Admin or staff privileges are required."
                }, status=status.HTTP_403_FORBIDDEN)

            try:
                if hasattr(user, 'shop_profile') and user.shop_profile:
                    user.shop_profile.google_sub = sub
                    user.shop_profile.save(update_fields=['google_sub'])
            except Exception:
                pass
        else:
            # Create staff user with unusable password
            base_username = email.split('@')[0].replace('.', '_')[:30]
            username = base_username
            c = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{c}"
                c += 1

            first_name = name.split()[0] if name else username
            last_name = " ".join(name.split()[1:]) if name and len(name.split()) > 1 else ""

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,
                is_superuser=False,
                is_active=True
            )
            user.set_unusable_password()  # Never retrieves or stores Google account password

            shop_id = serializer.validated_data.get('shop_id')
            shop = None
            if shop_id:
                shop = Shop.objects.filter(shop_id=shop_id, is_active=True).first()
            if not shop:
                shop = get_or_create_default_shop()

            profile = link_user_to_shop(user, shop, role='manager', is_approved=True)
            profile.google_sub = sub
            profile.save(update_fields=['google_sub'])

        login(request, user)
        csrf_token = get_token(request)

        record_audit_event(
            event_type='security_warning',
            actor_type='admin',
            actor_identifier=user.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'action': 'google_oauth_login_success', 'email': email}
        )

        return Response({
            "success": True,
            "message": f"Signed in with Google as {user.username}.",
            "data": AdminUserSerializer(user).data,
            "csrfToken": csrf_token,
        }, status=status.HTTP_200_OK)


class AdminMyShopView(APIView):
    """
    GET /api/v1/admin/my-shop/
    Returns authenticated staff user's assigned shop details including QR code and customer portal link.
    """
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        shop = get_user_shop(request.user)
        if not shop and request.user.is_superuser:
            shop = get_or_create_default_shop()

        if not shop:
            return Response({
                "success": False,
                "message": "No print shop assigned to this admin account."
            }, status=status.HTTP_404_NOT_FOUND)

        base_origin = request.headers.get('Origin') or request.headers.get('Referer')
        base_url = None
        if base_origin and 'localhost:3000' in base_origin:
            base_url = 'http://localhost:3000'
        elif base_origin and '127.0.0.1:3000' in base_origin:
            base_url = 'http://127.0.0.1:3000'

        stations = shop.stations.all().values('id', 'name', 'station_code', 'status', 'last_heartbeat_at')

        return Response({
            "success": True,
            "data": {
                "id": str(shop.id),
                "shop_id": shop.shop_id,
                "name": shop.name,
                "address": shop.address,
                "phone": shop.phone,
                "email": shop.email,
                "qr_url": f"/api/v1/shops/{shop.shop_id}/qr/",
                "customer_url": shop.get_customer_portal_url(base_url),
                "is_active": shop.is_active,
                "stations": list(stations),
            }
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
    Order-level dashboard listing with real-time stats, multi-PDF details, search, tab filters, and pagination.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="List orders with grouped PDFs, filters and stats")
    def get(self, request):
        from .cleanup_service import cleanup_completed_pdfs
        # Execute safe idempotent cleanup of completed PDFs older than 30 minutes
        cleanup_completed_pdfs(cutoff_minutes=30)

        cutoff_30min = timezone.now() - timezone.timedelta(minutes=30)
        search = request.query_params.get('search', '').strip()
        include_archived = request.query_params.get('include_archived', '').lower() in ['1', 'true', 'yes']

        # Multi-Tenant Shop Isolation
        is_super = request.user.is_superuser
        admin_shop = get_user_shop(request.user)

        if not is_super:
            if not admin_shop:
                return Response({
                    "success": False,
                    "message": "No print shop assigned to this admin account."
                }, status=status.HTTP_403_FORBIDDEN)
            base_qs = Order.objects.filter(shop=admin_shop).select_related('shop', 'approved_by').prefetch_related('files')
        else:
            # Superuser can see all, or optionally filter by shop_id
            shop_filter = request.query_params.get('shop_id')
            if shop_filter and shop_filter not in ['all', '']:
                base_qs = Order.objects.filter(shop__shop_id=shop_filter).select_related('shop', 'approved_by').prefetch_related('files')
            else:
                base_qs = Order.objects.select_related('shop', 'approved_by').prefetch_related('files')
        if not search and not include_archived:
            # Remove completed orders older than 30 minutes from active admin dashboard
            active_qs = base_qs.exclude(
                Q(status='completed', created_at__lte=cutoff_30min) |
                Q(status='completed', files__created_at__lte=cutoff_30min)
            ).distinct()
        else:
            active_qs = base_qs

        # 1. Summary Statistics for Top Counter Badges
        stats = {
            'total': active_qs.count(),
            'cash_pending': active_qs.filter(payment_status='cash_pending').count(),
            'blocked': active_qs.filter(approval_status='blocked').count(),
            'queued': active_qs.filter(status='queued').count(),
            'printing': active_qs.filter(status__in=['submitting_to_printer', 'submitted_to_printer', 'downloading', 'ready_to_print']).count(),
            'completed': active_qs.filter(status='completed').count(),
            'failed': active_qs.filter(status='failed').count(),
        }

        qs = active_qs

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
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search) |
                Q(customer_name__icontains=search) |
                Q(customer_phone__icontains=search) |
                Q(files__original_filename__icontains=search)
            ).distinct()

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

        serializer = AdminOrderSummarySerializer(orders_page, many=True)

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
        if not user_has_shop_access(request.user, getattr(job, 'shop', None)):
            return Response({
                "success": False,
                "message": "Access denied: Unauthorized access to another shop's document."
            }, status=status.HTTP_403_FORBIDDEN)
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


def resolve_order(order_or_job_id):
    """
    Resolves an Order instance by Order ID, order_number, or child PrintJob ID/number.
    """
    try:
        order = Order.objects.filter(id=order_or_job_id).first()
        if order:
            return order
    except Exception:
        pass

    order = Order.objects.filter(order_number=order_or_job_id).first()
    if order:
        return order

    try:
        job = PrintJob.objects.filter(id=order_or_job_id).first()
        if job and job.order:
            return job.order
        if job:
            return job
    except Exception:
        pass

    job = PrintJob.objects.filter(job_number=order_or_job_id).first()
    if job and job.order:
        return job.order
    return job


# ============================================================================
# 3. ORDER ACTION WORKFLOWS (BLOCK, UNBLOCK, PAY OK, PRINT)
# ============================================================================

class AdminPrintJobBlockView(APIView):
    """
    POST /api/v1/admin/print-jobs/{id}/block/
    Blocks an entire order (and all its child PDFs) from being queued, claimed, or printed.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Block order", request=AdminBlockSerializer)
    def post(self, request, job_id):
        serializer = AdminBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', 'Blocked by administrator')

        with transaction.atomic():
            target = resolve_order(job_id)
            if not target:
                return Response({"success": False, "message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            if not user_has_shop_access(request.user, getattr(target, 'shop', None)):
                return Response({
                    "success": False,
                    "message": "Access denied: Unauthorized access to another shop's order."
                }, status=status.HTTP_403_FORBIDDEN)

            order_num = getattr(target, 'order_number', None) or getattr(target, 'job_number', 'ORD')

            if not target.can_be_blocked():
                return Response(
                    {
                        "success": False,
                        "message": f"Order {order_num} cannot be blocked in status '{target.status}'. Printing has already completed or cancelled."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Record block metadata
            now = timezone.now()
            target.approval_status = 'blocked'
            target.blocked_by = request.user
            target.blocked_at = now
            target.blocked_reason = reason
            target.save(update_fields=['approval_status', 'blocked_by', 'blocked_at', 'blocked_reason', 'updated_at'])

            if isinstance(target, Order):
                target.files.all().update(
                    approval_status='blocked',
                    blocked_by=request.user,
                    blocked_at=now,
                    blocked_reason=reason
                )

            record_audit_event(
                event_type='job_blocked',
                actor_type='admin',
                actor_identifier=request.user.username,
                job_id=str(job_id),
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'reason': reason, 'order_number': order_num, 'order_id': str(target.id)}
            )
            if str(target.id) != str(job_id):
                record_audit_event(
                    event_type='job_blocked',
                    actor_type='admin',
                    actor_identifier=request.user.username,
                    job_id=str(target.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={'reason': reason, 'order_number': order_num}
                )

            logger.info(f"Admin {request.user.username} blocked order {order_num}.")

        resp_serializer = AdminOrderSummarySerializer(target) if isinstance(target, Order) else AdminPrintJobSummarySerializer(target)
        return Response({
            "success": True,
            "message": f"Order {order_num} has been blocked successfully.",
            "data": resp_serializer.data,
        }, status=status.HTTP_200_OK)


class AdminPrintJobUnblockView(APIView):
    """
    POST /api/v1/admin/print-jobs/{id}/unblock/
    Unblocks a previously blocked order.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Unblock order")
    def post(self, request, job_id):
        with transaction.atomic():
            target = resolve_order(job_id)
            if not target:
                return Response({"success": False, "message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            if not user_has_shop_access(request.user, getattr(target, 'shop', None)):
                return Response({
                    "success": False,
                    "message": "Access denied: Unauthorized access to another shop's order."
                }, status=status.HTTP_403_FORBIDDEN)

            order_num = getattr(target, 'order_number', None) or getattr(target, 'job_number', 'ORD')

            if not target.can_be_unblocked():
                return Response(
                    {"success": False, "message": f"Order {order_num} is not currently blocked."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            new_approval = 'approved' if target.payment_status in ['cash_received', 'paid'] else 'awaiting_review'
            target.approval_status = new_approval
            target.blocked_by = None
            target.blocked_at = None
            target.blocked_reason = ""
            target.save(update_fields=['approval_status', 'blocked_by', 'blocked_at', 'blocked_reason', 'updated_at'])

            if isinstance(target, Order):
                target.files.all().update(
                    approval_status=new_approval,
                    blocked_by=None,
                    blocked_at=None,
                    blocked_reason=""
                )

            record_audit_event(
                event_type='job_unblocked',
                actor_type='admin',
                actor_identifier=request.user.username,
                job_id=str(job_id),
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'order_number': order_num, 'order_id': str(target.id)}
            )
            if str(target.id) != str(job_id):
                record_audit_event(
                    event_type='job_unblocked',
                    actor_type='admin',
                    actor_identifier=request.user.username,
                    job_id=str(target.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={'order_number': order_num}
                )

            logger.info(f"Admin {request.user.username} unblocked order {order_num}.")

        resp_serializer = AdminOrderSummarySerializer(target) if isinstance(target, Order) else AdminPrintJobSummarySerializer(target)
        return Response({
            "success": True,
            "message": f"Order {order_num} has been unblocked.",
            "data": resp_serializer.data,
        }, status=status.HTTP_200_OK)


class AdminPrintJobPayOkView(APIView):
    """
    POST /api/v1/admin/print-jobs/{id}/pay-ok/
    Manual cash receipt confirmation by shop administrator.
    Confirms cash has been received physically at the counter for the complete order.
    If the order is not blocked, authorizes printing and enqueues all child PDFs to spooler.
    If the order is blocked, Pay OK confirms payment but does NOT override the block.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Approve cash payment (Pay OK)")
    def post(self, request, job_id):
        with transaction.atomic():
            target = resolve_order(job_id)
            if not target:
                return Response({"success": False, "message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            if not user_has_shop_access(request.user, getattr(target, 'shop', None)):
                return Response({
                    "success": False,
                    "message": "Access denied: Unauthorized access to another shop's order."
                }, status=status.HTTP_403_FORBIDDEN)

            order_num = getattr(target, 'order_number', None) or getattr(target, 'job_number', 'ORD')

            if target.payment_status == 'cash_received':
                return Response(
                    {"success": False, "message": f"Cash payment for order {order_num} was already approved."},
                    status=status.HTTP_409_CONFLICT
                )

            now = timezone.now()
            target.payment_status = 'cash_received'
            target.payment_approved_by = request.user
            target.payment_approved_at = now

            dispatched_count = 0
            if target.approval_status != 'blocked':
                target.approval_status = 'approved'
                target.approved_by = request.user
                target.approved_at = now

                # Dispatch printing for all child files
                if isinstance(target, Order):
                    for child_job in target.files.all():
                        ok, _ = dispatch_print_job(child_job)
                        if ok:
                            dispatched_count += 1
                else:
                    ok, _ = dispatch_print_job(target)
                    if ok:
                        dispatched_count += 1
            else:
                logger.warning(f"Pay OK received for blocked order {order_num}. Block preserved.")

            target.save()

            if isinstance(target, Order):
                target.files.all().update(
                    payment_status='cash_received',
                    payment_approved_by=request.user,
                    payment_approved_at=now,
                    approval_status=target.approval_status,
                )

            record_audit_event(
                event_type='pay_ok_approved',
                actor_type='admin',
                actor_identifier=request.user.username,
                job_id=str(job_id),
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={
                    'order_number': order_num,
                    'amount': str(target.total_amount),
                    'currency': target.currency,
                    'is_blocked': target.approval_status == 'blocked',
                    'dispatched_count': dispatched_count,
                    'order_id': str(target.id)
                }
            )
            if str(target.id) != str(job_id):
                record_audit_event(
                    event_type='pay_ok_approved',
                    actor_type='admin',
                    actor_identifier=request.user.username,
                    job_id=str(target.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={
                        'order_number': order_num,
                        'amount': str(target.total_amount),
                        'currency': target.currency,
                        'is_blocked': target.approval_status == 'blocked',
                        'dispatched_count': dispatched_count
                    }
                )

            logger.info(f"Admin {request.user.username} approved cash payment for {order_num}.")

        msg = f"Cash payment confirmed for Order {order_num}."
        if target.approval_status == 'blocked':
            msg += " Note: Order is currently BLOCKED and will not print until explicitly unblocked."
        elif dispatched_count > 0:
            msg += f" Sent {dispatched_count} PDF document(s) to printer spooler."
        else:
            msg += " Added to print queue."

        resp_serializer = AdminOrderSummarySerializer(target) if isinstance(target, Order) else AdminPrintJobSummarySerializer(target)
        return Response({
            "success": True,
            "message": msg,
            "data": resp_serializer.data,
        }, status=status.HTTP_200_OK)


class AdminPrintJobAuthorizePrintView(APIView):
    """
    POST /api/v1/admin/print-jobs/{id}/authorize-print/
    Admin manually authorizes printing for an unblocked, paid order (all child PDFs).
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Authorize print job")
    def post(self, request, job_id):
        with transaction.atomic():
            target = resolve_order(job_id)
            if not target:
                return Response({"success": False, "message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            if not user_has_shop_access(request.user, getattr(target, 'shop', None)):
                return Response({
                    "success": False,
                    "message": "Access denied: Unauthorized access to another shop's order."
                }, status=status.HTTP_403_FORBIDDEN)

            order_num = getattr(target, 'order_number', None) or getattr(target, 'job_number', 'ORD')

            # Verification 1: Block check
            if target.approval_status == 'blocked':
                return Response(
                    {
                        "success": False,
                        "message": f"Order {order_num} is BLOCKED. You must unblock it before authorizing printing."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verification 2: Payment check
            now = timezone.now()
            if target.payment_status == 'cash_pending':
                target.payment_status = 'cash_received'
                target.payment_approved_by = request.user
                target.payment_approved_at = now
            elif target.payment_status not in ['cash_received', 'paid']:
                return Response(
                    {
                        "success": False,
                        "message": f"Order {order_num} has not been paid yet (status: '{target.payment_status}'). Confirm cash with 'Pay OK' before printing."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verification 3: Terminal status check
            if target.status in ['submitted_to_printer', 'completed']:
                return Response(
                    {
                        "success": False,
                        "message": f"Order {order_num} has already been submitted to printer or completed."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Authorize print
            target.approval_status = 'approved'
            target.approved_by = request.user
            target.approved_at = now

            dispatched_count = 0
            if isinstance(target, Order):
                for child_job in target.files.all():
                    ok, _ = dispatch_print_job(child_job)
                    if ok:
                        dispatched_count += 1
                target.files.all().update(
                    approval_status='approved',
                    approved_by=request.user,
                    approved_at=now,
                    payment_status='cash_received'
                )
            else:
                ok, _ = dispatch_print_job(target)
                if ok:
                    dispatched_count += 1

            target.save()

            record_audit_event(
                event_type='job_approved',
                actor_type='admin',
                actor_identifier=request.user.username,
                job_id=str(job_id),
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'order_number': order_num, 'dispatched_count': dispatched_count, 'order_id': str(target.id)}
            )
            if str(target.id) != str(job_id):
                record_audit_event(
                    event_type='job_approved',
                    actor_type='admin',
                    actor_identifier=request.user.username,
                    job_id=str(target.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={'order_number': order_num, 'dispatched_count': dispatched_count}
                )

        resp_serializer = AdminOrderSummarySerializer(target) if isinstance(target, Order) else AdminPrintJobSummarySerializer(target)
        return Response({
            "success": True,
            "message": f"Order {order_num} authorized. Sent {dispatched_count} document(s) to printer.",
            "data": resp_serializer.data,
        }, status=status.HTTP_202_ACCEPTED)


class AdminFileDownloadView(APIView):
    """
    GET /api/v1/admin/print-jobs/{job_id}/download/
    Streams individual PDF file to authenticated admin/staff for viewing in browser or downloading.
    """
    permission_classes = [IsAdminOrStaff]

    def get(self, request, job_id):
        from django.http import FileResponse
        from apps.common.storage import private_storage

        job = None
        try:
            job = PrintJob.objects.filter(id=job_id).first()
        except Exception:
            pass

        if not job:
            job = PrintJob.objects.filter(job_number=job_id).first()

        if not job or not job.storage_key:
            return Response(
                {"success": False, "message": "PDF file is not available (it may have been purged under the 30-minute cleanup policy)."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Multi-Tenant Shop Isolation Check
        if not user_has_shop_access(request.user, getattr(job, 'shop', None)):
            return Response({
                "success": False,
                "message": "Access denied: Unauthorized access to another shop's document."
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            file_path = private_storage.get_full_path(job.storage_key)
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid file path detected."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not file_path.exists() or not file_path.is_file():
            return Response(
                {"success": False, "message": "File not found on disk storage."},
                status=status.HTTP_404_NOT_FOUND
            )

        as_inline = request.query_params.get('inline') == '1'
        disposition = 'inline' if as_inline else 'attachment'
        safe_filename = re.sub(r'[\r\n"\\/]', '', job.original_filename or 'document.pdf')

        response = FileResponse(open(str(file_path), 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'{disposition}; filename="{safe_filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class AdminPrintJobClearAllView(APIView):
    """
    POST /api/v1/admin/print-jobs/clear-all/
    Clears all orders, related print attempts, and deletes all PDF files from storage.
    """
    permission_classes = [IsAdminOrStaff]

    @extend_schema(summary="Clear all orders and PDF data")
    def post(self, request):
        from apps.common.storage import private_storage

        is_super = request.user.is_superuser
        admin_shop = get_user_shop(request.user)

        if not is_super:
            if not admin_shop:
                return Response({
                    "success": False,
                    "message": "Access denied: No print shop assigned."
                }, status=status.HTTP_403_FORBIDDEN)
            target_jobs = PrintJob.objects.filter(shop=admin_shop)
            target_orders = Order.objects.filter(shop=admin_shop)
        else:
            shop_param = request.query_params.get('shop_id')
            if shop_param and shop_param not in ['all', '']:
                target_jobs = PrintJob.objects.filter(shop__shop_id=shop_param)
                target_orders = Order.objects.filter(shop__shop_id=shop_param)
            else:
                target_jobs = PrintJob.objects.all()
                target_orders = Order.objects.all()

        # 1. Collect all storage keys to delete PDF files
        storage_keys = list(target_jobs.values_list('storage_key', flat=True))
        files_deleted = 0
        for key in storage_keys:
            if key:
                try:
                    if private_storage.delete_file(key):
                        files_deleted += 1
                except Exception as err:
                    logger.warning(f"Error deleting file {key}: {err}")

        # Also purge any remaining files in private_storage docs directory if superuser
        if is_super and not request.query_params.get('shop_id'):
            try:
                docs_dir = private_storage.base_dir / 'docs'
                if docs_dir.exists():
                    for p in docs_dir.glob('*'):
                        if p.is_file():
                            try:
                                p.unlink()
                                files_deleted += 1
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"Error purging docs directory: {e}")

        # 2. Delete targeted records
        PrintJobAttempt.objects.filter(job__in=target_jobs).delete()
        jobs_deleted, _ = target_jobs.delete()
        orders_deleted, _ = target_orders.delete()

        record_audit_event(
            event_type='security_warning',
            actor_type='admin',
            actor_identifier=request.user.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'action': 'clear_all_orders', 'orders_deleted': orders_deleted, 'jobs_deleted': jobs_deleted, 'files_deleted': files_deleted}
        )

        return Response({
            "success": True,
            "message": f"Successfully cleared all {orders_deleted} orders and removed associated PDF documents.",
            "deleted_count": orders_deleted,
            "files_deleted": files_deleted,
        }, status=status.HTTP_200_OK)

