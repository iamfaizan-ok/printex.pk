import io
from pypdf import PdfWriter
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.printing.models import PrintJob


def generate_sample_pdf(pages: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class CustomerPrintAPITests(APITestCase):

    def setUp(self):
        self.valid_pdf_bytes = generate_sample_pdf(pages=3)

    def test_health_check(self):
        url = reverse('health-check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'online')

    def test_print_options(self):
        url = reverse('print-options')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('A4', response.data.get('paper_sizes', []))
        self.assertIn('bw', response.data.get('colour_modes', []))

    def test_create_print_job_valid(self):
        url = reverse('print-jobs-list-create')
        pdf_file = SimpleUploadedFile(
            "assignment.pdf",
            self.valid_pdf_bytes,
            content_type="application/pdf"
        )
        data = {
            'file': pdf_file,
            'customer_name': 'Faizan Ali',
            'customer_phone': '03001234567',
            'copies': 2,
            'paper_size': 'A4',
            'colour_mode': 'bw',
            'sides': 'double',
            'page_range': 'all',
            'auto_print': 'false',
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data.get('success'))
        job_data = response.data.get('data')
        self.assertEqual(job_data.get('status'), 'queued')
        self.assertEqual(job_data.get('page_count'), 3)
        self.assertEqual(job_data.get('copies'), 2)
        self.assertEqual(job_data.get('total_impressions'), 6)  # 3 pages * 2 copies

        # Verify persisted in database
        job = PrintJob.objects.get(id=job_data['id'])
        self.assertEqual(job.customer_name, 'Faizan Ali')
        self.assertEqual(job.status, 'queued')

    def test_cash_payment_auto_prints(self):
        url = reverse('print-jobs-list-create')
        pdf_file = SimpleUploadedFile(
            "cash_doc.pdf",
            self.valid_pdf_bytes,
            content_type="application/pdf"
        )
        data = {
            'file': pdf_file,
            'customer_name': 'Cash Customer',
            'customer_phone': '03009999999',
            'payment_method': 'cash_on_delivery',
            'auto_print': 'true',
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data.get('success'))
        job_data = response.data.get('data')
        self.assertEqual(job_data.get('status'), 'submitted_to_printer')
        self.assertTrue(job_data.get('printer_dispatched'))
        self.assertTrue(bool(job_data.get('target_printer')))

    def test_reject_non_pdf_file(self):
        url = reverse('print-jobs-list-create')
        fake_file = SimpleUploadedFile(
            "malicious.exe",
            b"MZ\x90\x00\x03\x00\x00\x00",
            content_type="application/octet-stream"
        )
        data = {
            'file': fake_file,
            'customer_name': 'Hacker',
            'customer_phone': '03000000000',
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success', False))

    def test_reject_invalid_paper_size(self):
        url = reverse('print-jobs-list-create')
        pdf_file = SimpleUploadedFile(
            "doc.pdf",
            self.valid_pdf_bytes,
            content_type="application/pdf"
        )
        data = {
            'file': pdf_file,
            'paper_size': 'INVALID_POSTER_SIZE',
        }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_print_job(self):
        pdf_file = SimpleUploadedFile(
            "doc.pdf",
            self.valid_pdf_bytes,
            content_type="application/pdf"
        )
        url = reverse('print-jobs-list-create')
        create_resp = self.client.post(url, {'file': pdf_file, 'auto_print': 'false'}, format='multipart')
        job_id = create_resp.data['data']['id']

        cancel_url = reverse('print-jobs-cancel', kwargs={'job_id': job_id})
        cancel_resp = self.client.post(cancel_url, {'reason': 'Ordered by mistake'})
        self.assertEqual(cancel_resp.status_code, status.HTTP_200_OK)

        job = PrintJob.objects.get(id=job_id)
        self.assertEqual(job.status, 'cancelled')
