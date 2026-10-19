import io
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from pypdf import PdfWriter

from apps.devices.models import PrintStation
from apps.printing.models import PrintJob
from apps.audit.models import AuditEvent
from apps.printing.services import claim_next_job_for_station


User = get_user_model()


def generate_sample_pdf(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class AdminPortalTestSuite(TestCase):
    """
    Automated test suite verifying the PrintX Admin Portal APIs,
    session authentication, role-based access control, Block/Unblock logic,
    Pay OK cash workflow, print authorization, and audit trail.
    """

    def setUp(self):
        self.client = APIClient()

        # 1. Authorized Admin User
        self.admin_user = User.objects.create_superuser(
            username='admin_tester',
            email='admin@printx.pk',
            password='TestPassword123!'
        )

        # 2. Non-staff Customer User
        self.customer_user = User.objects.create_user(
            username='customer_jane',
            email='jane@example.com',
            password='TestPassword123!'
        )

        # 3. Create Sample Print Jobs
        self.cash_job = PrintJob.objects.create(
            job_number='PRX-20261019-111111',
            original_filename='final_report.pdf',
            storage_key='documents/test1.pdf',
            file_size_bytes=1024,
            page_count=5,
            copies=1,
            paper_size='A4',
            colour_mode='bw',
            sides='single',
            total_amount=25.00,
            currency='PKR',
            status='queued',
            approval_status='awaiting_review',
            payment_status='cash_pending',
        )

        self.paid_job = PrintJob.objects.create(
            job_number='PRX-20261019-222222',
            original_filename='thesis_draft.pdf',
            storage_key='documents/test2.pdf',
            file_size_bytes=2048,
            page_count=10,
            copies=2,
            paper_size='A4',
            colour_mode='colour',
            sides='double',
            total_amount=100.00,
            currency='PKR',
            status='queued',
            approval_status='approved',
            payment_status='paid',
        )

    # -------------------------------------------------------------------------
    # 1. Admin Authentication & Role-Based Access Control
    # -------------------------------------------------------------------------
    def test_admin_login_success(self):
        """Staff/admin can successfully authenticate and establish session."""
        url = reverse('admin-auth-login')
        response = self.client.post(url, {
            'username': 'admin_tester',
            'password': 'TestPassword123!'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.assertIn('csrfToken', response.data)
        self.assertEqual(response.data['data']['username'], 'admin_tester')

    def test_customer_login_denied_admin_access(self):
        """Non-staff customer credentials are rejected with HTTP 403."""
        url = reverse('admin-auth-login')
        response = self.client.post(url, {
            'username': 'customer_jane',
            'password': 'TestPassword123!'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data.get('success'))

    def test_unauthenticated_access_to_admin_endpoints_blocked(self):
        """Unauthenticated requests to admin endpoints return HTTP 401 or 403."""
        url = reverse('admin-print-jobs-list')
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


    def test_admin_me_and_logout(self):
        """Authenticated admin can check profile and log out."""
        self.client.force_authenticate(user=self.admin_user)

        # GET /admin/auth/me/
        me_url = reverse('admin-auth-me')
        me_res = self.client.get(me_url)
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data['data']['username'], 'admin_tester')

        # POST /admin/auth/logout/
        logout_url = reverse('admin-auth-logout')
        logout_res = self.client.post(logout_url)
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # 2. Order Listing, Filtering, Search, and Pagination
    # -------------------------------------------------------------------------
    def test_order_listing_and_stats(self):
        """Admin dashboard returns order list with summary stats."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-list')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))

        stats = response.data.get('stats', {})
        self.assertGreaterEqual(stats.get('total', 0), 2)
        self.assertGreaterEqual(stats.get('cash_pending', 0), 1)

    def test_tab_filter_cash_pending(self):
        """Filtering by tab 'cash_pending' only returns orders awaiting cash."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-list') + '?tab=cash_pending'

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orders = response.data.get('data', [])
        for order in orders:
            self.assertEqual(order['payment_status'], 'cash_pending')

    def test_search_by_order_id_and_filename(self):
        """Search filters correctly by Order ID and document filename."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-list') + '?search=thesis_draft'

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orders = response.data.get('data', [])
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['job_number'], self.paid_job.job_number)

    # -------------------------------------------------------------------------
    # 3. Block & Unblock Workflows
    # -------------------------------------------------------------------------
    def test_block_order_workflow(self):
        """Admin can block an order with audit metadata."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-block', kwargs={'job_id': self.cash_job.id})

        response = self.client.post(url, {'reason': 'Suspicious file content'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.cash_job.refresh_from_db()
        self.assertEqual(self.cash_job.approval_status, 'blocked')
        self.assertEqual(self.cash_job.blocked_by, self.admin_user)
        self.assertEqual(self.cash_job.blocked_reason, 'Suspicious file content')

        # Audit event verification
        audit = AuditEvent.objects.filter(job_id=str(self.cash_job.id), event_type='job_blocked').first()
        self.assertIsNotNone(audit)

        self.assertEqual(audit.actor_identifier, 'admin_tester')

    def test_unblock_order_workflow(self):
        """Admin can unblock a previously blocked order."""
        self.cash_job.approval_status = 'blocked'
        self.cash_job.blocked_by = self.admin_user
        self.cash_job.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-unblock', kwargs={'job_id': self.cash_job.id})

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.cash_job.refresh_from_db()
        self.assertEqual(self.cash_job.approval_status, 'awaiting_review')
        self.assertIsNone(self.cash_job.blocked_by)

    # -------------------------------------------------------------------------
    # 4. Pay OK Workflow & Separation of Payment and Printing
    # -------------------------------------------------------------------------
    @patch('apps.printing.admin_views.execute_immediate_print_for_job')
    def test_pay_ok_approves_cash_and_dispatches_unblocked(self, mock_print):
        """Pay OK marks cash as received and dispatches printing if unblocked."""
        mock_print.return_value = (True, "Dispatched successfully")

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-pay-ok', kwargs={'job_id': self.cash_job.id})

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.cash_job.refresh_from_db()
        self.assertEqual(self.cash_job.payment_status, 'cash_received')
        self.assertEqual(self.cash_job.approval_status, 'approved')
        self.assertEqual(self.cash_job.payment_approved_by, self.admin_user)

    @patch('apps.printing.printer_service.execute_immediate_print_for_job')
    def test_pay_ok_on_blocked_job_does_not_override_block(self, mock_print):
        """CRITICAL: Pay OK on a blocked job NEVER bypasses the block."""
        self.cash_job.approval_status = 'blocked'
        self.cash_job.blocked_by = self.admin_user
        self.cash_job.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-pay-ok', kwargs={'job_id': self.cash_job.id})

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.cash_job.refresh_from_db()
        # Payment is confirmed, but approval status remains BLOCKED
        self.assertEqual(self.cash_job.payment_status, 'cash_received')
        self.assertEqual(self.cash_job.approval_status, 'blocked')
        # Physical printer dispatch must NOT have occurred
        mock_print.assert_not_called()

    def test_duplicate_pay_ok_conflict(self):
        """Clicking Pay OK when already paid returns HTTP 409 Conflict."""
        self.cash_job.payment_status = 'cash_received'
        self.cash_job.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-pay-ok', kwargs={'job_id': self.cash_job.id})

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    # -------------------------------------------------------------------------
    # 5. Authorize Print Endpoint Validations
    # -------------------------------------------------------------------------
    def test_authorize_print_rejects_unpaid_order(self):
        """Authorizing print for an unpaid order is rejected with HTTP 400."""
        self.cash_job.payment_status = 'unpaid'
        self.cash_job.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-authorize-print', kwargs={'job_id': self.cash_job.id})

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("has not been paid yet", response.data.get('message', ''))

    def test_authorize_print_rejects_blocked_order(self):
        """Authorizing print for a blocked order is rejected with HTTP 400."""
        self.paid_job.approval_status = 'blocked'
        self.paid_job.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-authorize-print', kwargs={'job_id': self.paid_job.id})

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("BLOCKED", response.data.get('message', ''))

    @patch('apps.printing.admin_views.execute_immediate_print_for_job')
    def test_authorize_print_success_for_eligible_order(self, mock_print):
        """Authorizing print for eligible (paid, unblocked) order returns 202."""
        mock_print.return_value = (True, "Dispatched")

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-authorize-print', kwargs={'job_id': self.paid_job.id})

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.paid_job.refresh_from_db()
        self.assertEqual(self.paid_job.approval_status, 'approved')

    @patch('apps.printing.admin_views.execute_immediate_print_for_job')
    def test_authorize_print_on_cash_pending_confirms_cash_and_prints(self, mock_print):
        """Authorizing print on cash_pending order automatically marks cash received and dispatches."""
        mock_print.return_value = (True, "Dispatched")

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('admin-print-jobs-authorize-print', kwargs={'job_id': self.cash_job.id})

        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.cash_job.refresh_from_db()
        self.assertEqual(self.cash_job.approval_status, 'approved')
        self.assertEqual(self.cash_job.payment_status, 'cash_received')
        mock_print.assert_called_once()

    # -------------------------------------------------------------------------
    # 6. PC Agent Queue Enforcement
    # -------------------------------------------------------------------------
    def test_pc_agent_cannot_claim_blocked_or_unpaid_job(self):
        """PC agent claim routine strictly ignores blocked and unpaid jobs."""
        station = PrintStation.objects.create(
            name='Test Station 1',
            station_code='STATION_TEST_1',
            allowed_printers=['HP LaserJet Pro'],
            capabilities={'colour': True},
            is_enabled=True,
            status='online'
        )


        # 1. Unpaid job is never claimed
        claimed_job = claim_next_job_for_station(station)
        # Should claim paid_job, not cash_job
        self.assertIsNotNone(claimed_job)
        self.assertEqual(claimed_job.id, self.paid_job.id)

        # Reset paid_job back to queued and block it
        self.paid_job.status = 'queued'
        self.paid_job.approval_status = 'blocked'
        self.paid_job.save()

        # 2. Blocked job must never be claimed
        no_job = claim_next_job_for_station(station)
        self.assertIsNone(no_job)
