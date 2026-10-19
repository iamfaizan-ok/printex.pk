import time
import logging
from pathlib import Path
from typing import Optional

from .config import (
    STATION_CODE,
    AGENT_SECRET,
    BACKEND_BASE_URL,
    AGENT_VERSION,
    POLL_INTERVAL_SECONDS,
    HEARTBEAT_INTERVAL_SECONDS,
    SPOOL_DIR,
    LEDGER_DB_PATH,
    ALLOWED_PRINTERS,
    DEFAULT_PRINTER_NAME,
    PRINT_EXECUTION_MODE,
)
from .ledger import AgentLedger
from .printer_adapter import WindowsPrinterAdapter
from .client import AgentApiClient

logger = logging.getLogger("PrintXAgent")


class PrintXAgent:
    """
    Windows PC Print Agent Service:
    - Maintains local ledger for crash recovery
    - Authenticates via outbound HTTPS
    - Safely submits approved PDFs to local physical printer spooler
    """

    def __init__(self):
        self.ledger = AgentLedger(LEDGER_DB_PATH)
        self.printer_adapter = WindowsPrinterAdapter(
            allowed_printers=ALLOWED_PRINTERS,
            default_printer=DEFAULT_PRINTER_NAME,
            mode=PRINT_EXECUTION_MODE
        )
        self.client = AgentApiClient(
            base_url=BACKEND_BASE_URL,
            station_code=STATION_CODE,
            agent_secret=AGENT_SECRET,
            agent_version=AGENT_VERSION
        )
        self.spool_dir = SPOOL_DIR
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        self.running = False
        self.last_heartbeat = 0

    def recover_unresolved_jobs(self):
        """
        On startup, recover jobs that were interrupted by a system crash or power outage.
        """
        unresolved = self.ledger.get_unresolved_jobs()
        if not unresolved:
            return

        logger.warning(f"Found {len(unresolved)} unresolved job(s) in local ledger from previous run.")
        for row in unresolved:
            job_id = row['job_id']
            status = row['local_status']
            logger.info(f"Checking recovery for Job {row['job_number']} (local status: {status})...")

            if status in ['submitting_to_printer', 'submitted_to_printer']:
                # The job was already sent or partially sent to spooler!
                # Do NOT duplicate print blindly. Report outcome_unknown for safe operator reconciliation.
                self.client.update_job_status(
                    job_id=job_id,
                    status='outcome_unknown',
                    error_code='AGENT_REBOOT_RECOVERY',
                    diagnostic_details='PC restarted during print submission. Outcome uncertain to prevent duplicate physical paper waste.'
                )
                self.ledger.update_status(job_id, 'outcome_unknown')
            elif status in ['claimed', 'downloading', 'ready_to_print']:
                # Safe to retry processing
                logger.info(f"Retrying incomplete pre-print processing for Job {row['job_number']}...")

    def process_job(self, job_data: dict):
        job_id = job_data['id']
        job_number = job_data['job_number']
        logger.info(f"Processing claimed Job {job_number}...")

        # Record in local crash ledger
        self.ledger.record_claim(job_data)

        # Step 1: Downloading
        self.client.update_job_status(job_id, 'downloading')
        self.ledger.update_status(job_id, 'downloading')

        local_pdf_path = self.spool_dir / f"{job_number}.pdf"
        download_success = self.client.download_pdf(job_data['download_url'], local_pdf_path)

        if not download_success:
            err = "Failed to download authorized PDF from backend."
            logger.error(err)
            self.client.update_job_status(job_id, 'failed', error_code='DOWNLOAD_FAILED', error_message=err)
            self.ledger.update_status(job_id, 'failed', error=err)
            return

        # Step 2: Ready to Print
        self.client.update_job_status(job_id, 'ready_to_print')
        self.ledger.update_status(job_id, 'ready_to_print', local_pdf_path=str(local_pdf_path))

        # Step 3: Submitting to local printer
        self.client.update_job_status(job_id, 'submitting_to_printer')
        self.ledger.update_status(job_id, 'submitting_to_printer')

        target_printer = job_data.get('target_printer') or DEFAULT_PRINTER_NAME
        copies = int(job_data.get('copies', 1))

        print_success, diagnostic = self.printer_adapter.print_pdf(
            pdf_path=local_pdf_path,
            printer_name=target_printer,
            copies=copies
        )

        if print_success:
            logger.info(f"Job {job_number} successfully spooled to {target_printer}!")
            self.client.update_job_status(
                job_id,
                'completed',
                diagnostic_details=diagnostic
            )
            self.ledger.update_status(job_id, 'completed')

            # Clean up local temporary spool PDF safely
            try:
                if local_pdf_path.exists():
                    local_pdf_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete temp spool file {local_pdf_path}: {e}")
        else:
            logger.error(f"Job {job_number} printing failed: {diagnostic}")
            self.client.update_job_status(
                job_id,
                'failed',
                error_code='SPOOLER_SUBMISSION_FAILED',
                error_message=diagnostic,
                diagnostic_details=diagnostic
            )
            self.ledger.update_status(job_id, 'failed', error=diagnostic)

    def run_cycle(self):
        now = time.time()
        # 1. Heartbeat check
        if now - self.last_heartbeat > HEARTBEAT_INTERVAL_SECONDS:
            printers = self.printer_adapter.get_installed_printers()
            self.client.send_heartbeat(printers)
            self.last_heartbeat = now

        # 2. Claim available job
        job_data = self.client.claim_job()
        if job_data:
            self.process_job(job_data)

    def start(self):
        logger.info(f"Starting PrintX PC Agent v{AGENT_VERSION} for Station '{STATION_CODE}'...")
        printers = self.printer_adapter.get_installed_printers()
        logger.info(f"Detected Windows Printers: {printers}")
        logger.info(f"Printer Allowlist: {ALLOWED_PRINTERS}")
        logger.info(f"Execution Mode: {PRINT_EXECUTION_MODE}")

        self.running = True
        self.recover_unresolved_jobs()

        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Unexpected error in agent polling cycle: {e}")
            time.sleep(POLL_INTERVAL_SECONDS)

    def stop(self):
        logger.info("Stopping PrintX PC Agent gracefully...")
        self.running = False
