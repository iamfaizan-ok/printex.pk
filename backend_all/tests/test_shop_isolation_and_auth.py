import io
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core import mail
from rest_framework import status
from rest_framework.test import APIClient
from pypdf import PdfWriter

from apps.shops.models import Shop, ShopStaff
from apps.shops.services import get_or_create_default_shop, link_user_to_shop
from apps.printing.models import Order, PrintJob
from apps.devices.models import PrintStation

User = get_user_model()


def generate_sample_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class ShopIsolationAndAuthTestSuite(TestCase):
    """
    Comprehensive test suite validating:
    1. Shop Isolation: Multiple shops, strict tenant boundaries, IDOR prevention.
    2. Admin Authentication: Signup, Login, Logout, Forgot Password, Reset Password, Google OAuth.
    3. QR Code generation and linking.
    """

    def setUp(self):
        self.client = APIClient()

        # 1. Create two separate shops
        self.shop_alpha = Shop.objects.create(
            shop_id='shop-alpha-01',
            name='Alpha Campus Print Shop',
            address='Main Campus, Academic Block 1',
            phone='0300-1111111',
            email='alpha@printx.pk',
            is_active=True
        )

        self.shop_beta = Shop.objects.create(
            shop_id='shop-beta-02',
            name='Beta City Center Print Shop',
            address='City Center Plaza, Floor 2',
            phone='0300-2222222',
            email='beta@printx.pk',
            is_active=True
        )

        # 2. Create staff users for each shop
        self.user_alpha = User.objects.create_user(
            username='admin_alpha',
            email='alpha_admin@printx.pk',
            password='AlphaPassword123!',
            is_staff=True,
            is_superuser=False
        )
        link_user_to_shop(self.user_alpha, self.shop_alpha, role='manager', is_approved=True)

        self.user_beta = User.objects.create_user(
            username='admin_beta',
            email='beta_admin@printx.pk',
            password='BetaPassword123!',
            is_staff=True,
            is_superuser=False
        )
        link_user_to_shop(self.user_beta, self.shop_beta, role='manager', is_approved=True)

        # 3. Create global superuser
        self.user_super = User.objects.create_superuser(
            username='global_superadmin',
            email='super@printx.pk',
            password='SuperPassword123!'
        )

        # 4. Create an order and job for Shop Alpha
        self.order_alpha = Order.objects.create(
            order_number='ORD id 101',
            shop=self.shop_alpha,
            customer_name='John Doe',
            customer_phone='0300-9999999',
            customer_email='john@example.com',
            status='queued',
            approval_status='awaiting_review',
            payment_status='cash_pending',
            total_amount=50.00
        )
        self.job_alpha = PrintJob.objects.create(
            order=self.order_alpha,
            shop=self.shop_alpha,
            job_number='ORD id 101',
            original_filename='alpha_document.pdf',
            storage_key='docs/alpha_doc.pdf',
            file_size_bytes=1024,
            status='queued',
            approval_status='awaiting_review',
            payment_status='cash_pending',
            total_amount=50.00
        )

        # 5. Create an order and job for Shop Beta
        self.order_beta = Order.objects.create(
            order_number='ORD id 102',
            shop=self.shop_beta,
            customer_name='Sarah Connor',
            customer_phone='0300-8888888',
            customer_email='sarah@example.com',
            status='queued',
            approval_status='awaiting_review',
            payment_status='cash_pending',
            total_amount=80.00
        )
        self.job_beta = PrintJob.objects.create(
            order=self.order_beta,
            shop=self.shop_beta,
            job_number='ORD id 102',
            original_filename='beta_document.pdf',
            storage_key='docs/beta_doc.pdf',
            file_size_bytes=2048,
            status='queued',
            approval_status='awaiting_review',
            payment_status='cash_pending',
            total_amount=80.00
        )

    # =========================================================================
    # PART 1: SHOP ISOLATION TESTS
    # =========================================================================

    def test_shop_has_unique_id_and_qr_code(self):
        """Verify shop has unique shop_id, customer portal URL, and QR code image bytes."""
        self.assertEqual(self.shop_alpha.shop_id, 'shop-alpha-01')
        self.assertTrue('shop=shop-alpha-01' in self.shop_alpha.get_customer_portal_url())

        # Test dynamic QR endpoint returns HTTP 200 with PNG
        response = self.client.get(f"/api/v1/shops/{self.shop_alpha.shop_id}/qr/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(len(response.content) > 100)

    def test_admin_alpha_only_sees_alpha_orders(self):
        """Shop Alpha admin should only receive Alpha orders, not Beta orders."""
        self.client.force_authenticate(user=self.user_alpha)
        response = self.client.get('/api/v1/admin/print-jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orders = response.data['data']

        order_numbers = [o['order_number'] for o in orders]
        self.assertIn('ORD id 101', order_numbers)
        self.assertNotIn('ORD id 102', order_numbers)
        self.assertEqual(response.data['stats']['total'], 1)

    def test_admin_beta_only_sees_beta_orders(self):
        """Shop Beta admin should only receive Beta orders, not Alpha orders."""
        self.client.force_authenticate(user=self.user_beta)
        response = self.client.get('/api/v1/admin/print-jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orders = response.data['data']

        order_numbers = [o['order_number'] for o in orders]
        self.assertIn('ORD id 102', order_numbers)
        self.assertNotIn('ORD id 101', order_numbers)
        self.assertEqual(response.data['stats']['total'], 1)

    def test_cross_shop_access_forbidden_on_order_actions(self):
        """Admin Alpha trying to block, unblock, or Pay OK Shop Beta's order gets HTTP 403."""
        self.client.force_authenticate(user=self.user_alpha)

        # Block Shop Beta's order
        res_block = self.client.post(f"/api/v1/admin/print-jobs/{self.order_beta.id}/block/")
        self.assertEqual(res_block.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Access denied", res_block.data['message'])

        # Pay OK on Shop Beta's order
        res_pay = self.client.post(f"/api/v1/admin/print-jobs/{self.order_beta.id}/pay-ok/")
        self.assertEqual(res_pay.status_code, status.HTTP_403_FORBIDDEN)

        # Download Shop Beta's PDF
        res_down = self.client.get(f"/api/v1/admin/print-jobs/{self.job_beta.id}/download/")
        self.assertEqual(res_down.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_has_global_access(self):
        """Superuser can access and list orders across all shops."""
        self.client.force_authenticate(user=self.user_super)
        response = self.client.get('/api/v1/admin/print-jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_numbers = [o['order_number'] for o in response.data['data']]
        self.assertIn('ORD id 101', order_numbers)
        self.assertIn('ORD id 102', order_numbers)

    def test_order_creation_links_to_specified_shop(self):
        """Customer placing an order with ?shop_id=shop-beta-02 binds order to Shop Beta."""
        pdf_bytes = generate_sample_pdf()
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_file.name = "customer_doc.pdf"

        response = self.client.post(
            '/api/v1/orders/create/',
            {
                'files': [pdf_file],
                'customer_name': 'Ali Khan',
                'customer_phone': '0300-5555555',
                'shop_id': 'shop-beta-02',
                'file_settings': json.dumps([{
                    'copies': 1,
                    'paper_size': 'A4',
                    'colour_mode': 'bw',
                    'sides': 'single',
                }]),
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_num = response.data['orderNumber']

        created_order = Order.objects.get(order_number=order_num)
        self.assertEqual(created_order.shop, self.shop_beta)
        for f in created_order.files.all():
            self.assertEqual(f.shop, self.shop_beta)

    # =========================================================================
    # PART 2: ADMIN AUTHENTICATION TESTS
    # =========================================================================

    def test_admin_signup_creates_staff_and_assigns_shop(self):
        """Test secure admin signup prevents superuser escalation and assigns shop."""
        payload = {
            'username': 'new_operator',
            'email': 'new_operator@printx.pk',
            'password': 'SecureOperatorPassword123!',
            'full_name': 'Operator Khan',
            'shop_id': 'shop-alpha-01',
        }
        response = self.client.post('/api/v1/admin/auth/signup/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        user = User.objects.get(username='new_operator')
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)  # Strict non-escalation
        self.assertEqual(user.shop_profile.shop, self.shop_alpha)

    def test_admin_signup_with_weak_password_rejected(self):
        """Signup with password under 8 characters or trivial is rejected."""
        payload = {
            'username': 'weak_user',
            'email': 'weak@printx.pk',
            'password': '123',
            'shop_id': 'shop-alpha-01',
        }
        response = self.client.post('/api/v1/admin/auth/signup/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_admin_login_and_logout(self):
        """Staff user can log in, receive session cookie, view profile, and log out."""
        login_res = self.client.post('/api/v1/admin/auth/login/', {
            'username': 'admin_alpha',
            'password': 'AlphaPassword123!'
        })
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertTrue(login_res.data['success'])
        self.assertEqual(login_res.data['data']['shop']['shop_id'], 'shop-alpha-01')

        # Test GET /admin/auth/me/
        me_res = self.client.get('/api/v1/admin/auth/me/')
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data['data']['username'], 'admin_alpha')

        # Test GET /admin/my-shop/
        shop_res = self.client.get('/api/v1/admin/my-shop/')
        self.assertEqual(shop_res.status_code, status.HTTP_200_OK)
        self.assertEqual(shop_res.data['data']['shop_id'], 'shop-alpha-01')

        # Test Logout
        logout_res = self.client.post('/api/v1/admin/auth/logout/')
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

    def test_password_reset_flow(self):
        """Full email-based forgot password & password reset token confirm flow."""
        # 1. Request password reset
        mail.outbox = []
        req_res = self.client.post('/api/v1/admin/auth/password-reset/', {
            'email': 'alpha_admin@printx.pk'
        })
        self.assertEqual(req_res.status_code, status.HTTP_200_OK)
        self.assertTrue(req_res.data['success'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("password reset", mail.outbox[0].subject.lower())

        # 2. Extract token & uid
        token = default_token_generator.make_token(self.user_alpha)
        uid = urlsafe_base64_encode(force_bytes(self.user_alpha.pk))

        # 3. Confirm password reset
        confirm_res = self.client.post('/api/v1/admin/auth/password-reset-confirm/', {
            'uid': uid,
            'token': token,
            'new_password': 'BrandNewPassword999!',
        })
        self.assertEqual(confirm_res.status_code, status.HTTP_200_OK)
        self.assertTrue(confirm_res.data['success'])

        # 4. Verify login works with new password
        login_res = self.client.post('/api/v1/admin/auth/login/', {
            'username': 'admin_alpha',
            'password': 'BrandNewPassword999!'
        })
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)

    @patch('requests.get')
    def test_google_oauth_signin(self, mock_get):
        """Google OAuth verifies credential, links to staff account, never stores Google password."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'iss': 'https://accounts.google.com',
            'sub': 'google-uid-123456789',
            'email': 'alpha_admin@printx.pk',
            'email_verified': 'true',
            'name': 'Alpha Admin User',
        }
        mock_get.return_value = mock_resp

        response = self.client.post('/api/v1/admin/auth/google/', {
            'credential': 'mock_google_id_token_xyz'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['username'], 'admin_alpha')

        # Verify Google sub was linked
        self.user_alpha.refresh_from_db()
        self.assertEqual(self.user_alpha.shop_profile.google_sub, 'google-uid-123456789')
        # Verify user password remains unchanged/secure
        self.assertTrue(self.user_alpha.check_password('AlphaPassword123!'))
