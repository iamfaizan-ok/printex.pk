import logging
import requests
import json
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.middleware.csrf import get_token
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils.text import slugify
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema

from apps.shops.models import Shop, ShopStaff
from apps.shops.services import (
    get_or_create_default_shop,
    link_user_to_shop,
    get_user_shop,
)
from apps.audit.services import record_audit_event
from .serializers import (
    AdminUserSerializer,
    LoginSerializer,
    RegisterShopSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    GoogleAuthSerializer,
)

logger = logging.getLogger("PrintX.Accounts")
User = get_user_model()


class LoginView(APIView):
    """
    POST /api/v1/accounts/login/ or /api/v1/admin/auth/login/
    Authenticates staff/admin user and creates a secure Django session.
    Protected with IP-based rate throttling against brute-force attacks.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

    @extend_schema(summary="Admin login", request=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
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


class LogoutView(APIView):
    """
    POST /api/v1/accounts/logout/ or /api/v1/admin/auth/logout/
    Terminates admin session.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.user.username if request.user.is_authenticated else 'anonymous'
        logout(request)
        if hasattr(request, 'session'):
            request.session.flush()

        record_audit_event(
            event_type='security_warning',
            actor_type='admin',
            actor_identifier=user_id,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'action': 'admin_logout'}
        )

        return Response({
            "success": True,
            "message": "Signed out successfully."
        }, status=status.HTTP_200_OK)


class RegisterShopView(APIView):
    """
    POST /api/v1/accounts/register-shop/ or /api/v1/admin/auth/signup/
    Registers a new print shop in the database, creates the shop manager admin account,
    links them in PostgreSQL, and establishes the user session.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

    @extend_schema(summary="Register shop and create admin account", request=RegisterShopSerializer)
    def post(self, request):
        serializer = RegisterShopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        username = data['username']
        email = data['email'].strip().lower()
        password = data['password']
        full_name = data.get('full_name', '')
        reg_key = data.get('registration_key', '').strip()

        shop_name = serializer.get_resolved_shop_name()
        shop_address = serializer.get_resolved_shop_address()
        shop_phone = serializer.get_resolved_shop_phone()
        existing_shop_id = data.get('shop_id', '').strip()

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

        # Registration key gatekeeping if configured
        expected_key = getattr(settings, 'ADMIN_REGISTRATION_KEY', '')
        if expected_key and reg_key != expected_key:
            return Response({
                "success": False,
                "message": "Invalid registration key. Authorization from platform owner required."
            }, status=status.HTTP_403_FORBIDDEN)

        # 1. Resolve or Create the Shop in Database
        if shop_name:
            base_id = f"shop-{slugify(shop_name)}"[:40] or "shop-new"
            cand_id = base_id
            counter = 1
            while Shop.objects.filter(shop_id=cand_id).exists():
                cand_id = f"{base_id}-{counter}"
                counter += 1
            shop = Shop.objects.create(
                shop_id=cand_id,
                name=shop_name,
                address=shop_address,
                phone=shop_phone,
                email=email,
                is_active=True
            )
        elif existing_shop_id:
            shop = Shop.objects.filter(shop_id=existing_shop_id, is_active=True).first()
            if not shop:
                return Response({
                    "success": False,
                    "message": f"Shop '{existing_shop_id}' not found or inactive."
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Default fallback shop if no name provided
            shop = get_or_create_default_shop()

        # 2. Create User with strict least-privilege (is_superuser=False always!)
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

        # 3. Link User to Shop as Manager in Database
        link_user_to_shop(user, shop, role='manager', is_approved=True)

        # 4. Automatically authenticate & establish session
        login(request, user)
        csrf_token = get_token(request)

        record_audit_event(
            event_type='security_warning',
            actor_type='admin',
            actor_identifier=user.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'action': 'shop_registered', 'shop_id': shop.shop_id, 'shop_name': shop.name}
        )

        return Response({
            "success": True,
            "message": f"Shop '{shop.name}' and manager account successfully registered.",
            "data": AdminUserSerializer(user).data,
            "csrfToken": csrf_token,
        }, status=status.HTTP_201_CREATED)


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/accounts/password-reset/
    Initiates email-based password reset for admin/staff accounts.
    Returns generic anti-enumeration success message regardless of existence.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

    @extend_schema(summary="Request admin password reset email", request=PasswordResetRequestSerializer)
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip().lower()

        generic_response = Response({
            "success": True,
            "message": "If an account exists with that email, a password reset link has been dispatched."
        }, status=status.HTTP_200_OK)

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user or not (user.is_staff or user.is_superuser):
            return generic_response

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        admin_base = getattr(settings, 'ADMIN_BASE_URL', 'http://127.0.0.1:8000/admin-panel')
        reset_link = f"{admin_base}/login.html?view=reset&uid={uid}&token={token}"

        subject = "PrintX Admin Operations - Password Reset Request"
        message = (
            f"Hello {user.username},\n\n"
            f"A password reset was requested for your PrintX Admin account.\n\n"
            f"Click or paste the following link to set a new password:\n{reset_link}\n\n"
            f"If you did not request this reset, you can safely disregard this email.\n\n"
            f"— PrintX Multi-Tenant Operations Team"
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@printx.pk')

        try:
            send_mail(subject, message, from_email, [email], fail_silently=False)
            logger.info(f"Password reset link emailed to {email} (UID: {uid})")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}")

        return generic_response


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/accounts/password-reset-confirm/
    Verifies reset token and updates user password in database.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

    @extend_schema(summary="Confirm password reset", request=PasswordResetConfirmSerializer)
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid_b64 = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            uid = force_str(urlsafe_base64_decode(uid_b64))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                "success": False,
                "message": "Invalid or expired password reset link."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({
                "success": False,
                "message": "Password reset token is invalid or has expired."
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        record_audit_event(
            event_type='security_warning',
            actor_type='admin',
            actor_identifier=user.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'action': 'password_reset_confirmed'}
        )

        return Response({
            "success": True,
            "message": "Password has been updated successfully. Please sign in with your new password."
        }, status=status.HTTP_200_OK)


class GoogleAuthView(APIView):
    """
    POST /api/v1/accounts/google/
    Secure Google OAuth 2.0 verification.
    Validates Google ID token via Google's tokeninfo API.
    Never retrieves or stores external passwords.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_auth'

    @extend_schema(summary="Google OAuth Sign-In", request=GoogleAuthSerializer)
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = serializer.validated_data['credential']

        # Verify Google ID Token via Google tokeninfo
        try:
            verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
            resp = requests.get(verify_url, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Google OAuth verification failed: {resp.text}")
                return Response({
                    "success": False,
                    "message": "Invalid Google credential."
                }, status=status.HTTP_400_BAD_REQUEST)
            token_data = resp.json()
        except Exception as e:
            logger.warning(f"Google token verification failed: {e}")
            return Response({
                "success": False,
                "message": "Google authentication failed. Token verification error."
            }, status=status.HTTP_400_BAD_REQUEST)

        if 'error_description' in token_data or 'email' not in token_data:
            return Response({
                "success": False,
                "message": "Invalid Google credential."
            }, status=status.HTTP_400_BAD_REQUEST)

        email = token_data['email'].lower().strip()
        email_verified = token_data.get('email_verified') in [True, 'true', 'True']
        google_sub = token_data.get('sub', '')
        name = token_data.get('name', '')

        if not email_verified:
            return Response({
                "success": False,
                "message": "Google email must be verified to sign in."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Enforce Client ID match if configured
        expected_client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
        if expected_client_id and token_data.get('aud') != expected_client_id:
            logger.warning("Google token audience mismatch.")
            return Response({
                "success": False,
                "message": "Invalid Google client audience."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find existing user or link
        user = User.objects.filter(email__iexact=email).first()
        if user:
            if not (user.is_staff or user.is_superuser):
                return Response({
                    "success": False,
                    "message": "Access denied. Admin/staff credentials required."
                }, status=status.HTTP_403_FORBIDDEN)

            if hasattr(user, 'shop_profile') and user.shop_profile:
                if not user.shop_profile.google_sub:
                    user.shop_profile.google_sub = google_sub
                    user.shop_profile.save(update_fields=['google_sub'])
        else:
            # Register staff user for Google account
            username_candidate = email.split('@')[0].replace('.', '_')[:30]
            base_u = username_candidate
            c = 1
            while User.objects.filter(username__iexact=username_candidate).exists():
                username_candidate = f"{base_u}{c}"
                c += 1

            first_name = name.split()[0] if name else username_candidate
            last_name = " ".join(name.split()[1:]) if name and len(name.split()) > 1 else ""

            user = User.objects.create_user(
                username=username_candidate,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,
                is_superuser=False,
                is_active=True
            )
            user.set_unusable_password()
            user.save()

            target_shop = get_or_create_default_shop()
            link_user_to_shop(user, target_shop, role='operator', google_sub=google_sub, is_approved=True)

        login(request, user)
        csrf_token = get_token(request)

        return Response({
            "success": True,
            "message": "Signed in with Google successfully.",
            "data": AdminUserSerializer(user).data,
            "csrfToken": csrf_token,
        }, status=status.HTTP_200_OK)


class AdminMeView(APIView):
    """
    GET /api/v1/accounts/me/ or /api/v1/admin/auth/me/
    Returns authenticated admin profile and assigned shop.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({"success": False, "message": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            "success": True,
            "data": AdminUserSerializer(request.user).data
        }, status=status.HTTP_200_OK)


class AdminMyShopView(APIView):
    """
    GET /api/v1/accounts/my-shop/ or /api/v1/admin/my-shop/
    Returns shop details, QR endpoint, and customer upload URL.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({"success": False, "message": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        shop = get_user_shop(request.user)
        if not shop:
            if request.user.is_superuser:
                return Response({
                    "success": True,
                    "data": {
                        "shop_id": "all",
                        "name": "Global Admin (All Shops)",
                        "address": "Platform Head Office",
                        "customer_portal_url": "http://localhost:3000",
                        "qr_url": None,
                    }
                })
            return Response({"success": False, "message": "No assigned shop found for your profile."}, status=status.HTTP_404_NOT_FOUND)

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
                "customer_portal_url": shop.get_customer_portal_url(base_url),
                "qr_url": f"/api/v1/shops/{shop.shop_id}/qr/",
                "created_at": shop.created_at.isoformat(),
                "stations": list(stations),
            }
        }, status=status.HTTP_200_OK)
