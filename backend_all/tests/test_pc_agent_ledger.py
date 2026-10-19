import tempfile
from pathlib import Path
from unittest import TestCase
from pc_agent.ledger import AgentLedger


class AgentLedgerTests(TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_ledger.sqlite3"
        self.ledger = AgentLedger(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_retrieve_claim(self):
        job_data = {
            'id': 'job_uuid_123',
            'job_number': 'PRX-2026-999',
            'target_printer': 'HP LaserJet Pro',
            'copies': 2,
            'paper_size': 'A4',
            'colour_mode': 'colour',
        }
        self.ledger.record_claim(job_data, local_pdf_path='/tmp/PRX-2026-999.pdf')

        retrieved = self.ledger.get_job('job_uuid_123')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['job_number'], 'PRX-2026-999')
        self.assertEqual(retrieved['local_status'], 'claimed')
        self.assertEqual(retrieved['copies'], 2)

    def test_update_status_and_recovery(self):
        job_data = {
            'id': 'job_uuid_456',
            'job_number': 'PRX-2026-456',
            'target_printer': 'Canon iR-ADV',
            'copies': 1,
            'paper_size': 'A4',
            'colour_mode': 'bw',
        }
        self.ledger.record_claim(job_data)
        self.ledger.update_status('job_uuid_456', 'submitting_to_printer')

        # Simulate agent crash & restart
        new_ledger_instance = AgentLedger(self.db_path)
        unresolved = new_ledger_instance.get_unresolved_jobs()

        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]['job_id'], 'job_uuid_456')
        self.assertEqual(unresolved[0]['local_status'], 'submitting_to_printer')
