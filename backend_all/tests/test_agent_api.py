from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.devices.models import PrintStation
from apps.printing.models import PrintJob
from apps.common.storage import private_storage
from .test_customer_api import generate_sample_pdf


class AgentAPITests(APITestCase):

    def setUp(self):
        self.station_code = "STN-TEST-99"
        self.agent_secret = "secret_agent_key_2026"
        self.station = PrintStation.objects.create(
            name="Test Print Station",
            station_code=self.station_code,
            allowed_printers=["HP LaserJet Pro", "Microsoft Print to PDF"],
            capabilities={"paper_sizes": ["A4"], "colour": True, "duplex": True},
            is_enabled=True,
            status="offline"
        )
        self.station.set_token(self.agent_secret)
        self.station.save()

        # Seed sample queued print job
        pdf_bytes = generate_sample_pdf(pages=1)
        storage_key = private_storage.save_file(pdf_bytes)

        self.job = PrintJob.objects.create(
            job_number=PrintJob.generate_job_number(),
            access_token=PrintJob.generate_access_token(),
            customer_name="Test Customer",
            customer_phone="03001112233",
            original_filename="sample.pdf",
            storage_key=storage_key,
            file_size_bytes=len(pdf_bytes),
            page_count=1,
            copies=1,
            paper_size="A4",
            colour_mode="bw",
            status="queued",
            approval_status="approved",
            payment_status="paid"
        )

    def test_agent_heartbeat_authorized(self):
        url = reverse('agent-heartbeat')
        headers = {
            'HTTP_X_STATION_CODE': self.station_code,
            'HTTP_X_AGENT_SECRET': self.agent_secret,
        }
        response = self.client.post(url, {'agent_version': '1.0.0'}, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.station.refresh_from_db()
        self.assertEqual(self.station.status, 'online')

    def test_agent_heartbeat_invalid_credentials_rejected(self):
        url = reverse('agent-heartbeat')
        headers = {
            'HTTP_X_STATION_CODE': self.station_code,
            'HTTP_X_AGENT_SECRET': 'WRONG_SECRET',
        }
        response = self.client.post(url, {}, **headers)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_agent_claim_job(self):
        url = reverse('agent-claim-job')
        headers = {
            'HTTP_X_STATION_CODE': self.station_code,
            'HTTP_X_AGENT_SECRET': self.agent_secret,
        }
        response = self.client.post(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        claimed_job = response.data['job']
        self.assertEqual(claimed_job['id'], str(self.job.id))

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'claimed')
        self.assertEqual(self.job.assigned_station, self.station)

    def test_agent_download_authorized_pdf(self):
        # Claim first
        self.job.assigned_station = self.station
        self.job.status = 'claimed'
        self.job.save()

        url = reverse('agent-job-download', kwargs={'job_id': self.job.id})
        headers = {
            'HTTP_X_STATION_CODE': self.station_code,
            'HTTP_X_AGENT_SECRET': self.agent_secret,
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_agent_update_status_flow(self):
        self.job.assigned_station = self.station
        self.job.status = 'claimed'
        self.job.save()

        url = reverse('agent-job-status', kwargs={'job_id': self.job.id})
        headers = {
            'HTTP_X_STATION_CODE': self.station_code,
            'HTTP_X_AGENT_SECRET': self.agent_secret,
        }

        # claimed -> downloading
        resp1 = self.client.post(url, {'status': 'downloading'}, **headers)
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)

        # downloading -> ready_to_print
        resp2 = self.client.post(url, {'status': 'ready_to_print'}, **headers)
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)

        # ready_to_print -> submitting_to_printer
        resp3 = self.client.post(url, {'status': 'submitting_to_printer'}, **headers)
        self.assertEqual(resp3.status_code, status.HTTP_200_OK)

        # submitting_to_printer -> completed
        resp4 = self.client.post(url, {'status': 'completed', 'diagnostic_details': 'Printed successfully'}, **headers)
        self.assertEqual(resp4.status_code, status.HTTP_200_OK)

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'completed')
        self.assertIsNotNone(self.job.completed_at)
