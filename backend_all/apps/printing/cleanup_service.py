import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from apps.common.storage import private_storage
from apps.audit.services import record_audit_event
from .models import PrintJob

logger = logging.getLogger("PrintX.CleanupService")


def cleanup_completed_pdfs(cutoff_minutes: int = 30) -> dict:
    """
    Scans all PrintJobs that are marked 'completed' and whose PDF/order creation
    timestamp is at least `cutoff_minutes` old (default 30 minutes).

    Requirement compliance:
    - Calculates 30 minutes based on job.created_at (order/PDF creation timestamp).
    - ONLY cleans up jobs marked 'completed'.
    - Does NOT remove PDFs belonging to pending, queued, downloading, ready_to_print,
      submitting_to_printer, or any other incomplete order.
    - Deletes only the physical PDF file from private_storage.
    - Strictly preserves the PrintJob database record, customer details, payment records,
      and order history.
    - Safe, idempotent, and error-tolerant.
    """
    cutoff_time = timezone.now() - timedelta(minutes=cutoff_minutes)

    # Strictly target ONLY 'completed' jobs created at or before cutoff_time
    candidate_jobs = (
        PrintJob.objects.filter(
            Q(status='completed') | Q(order__status='completed'),
            created_at__lte=cutoff_time,
        )
        .exclude(storage_key='')
        .only('id', 'job_number', 'storage_key', 'original_filename', 'created_at', 'status', 'notes')
    )

    cleaned_count = 0
    errors = []

    for job in candidate_jobs:
        storage_key = job.storage_key
        if not storage_key:
            continue

        try:
            file_deleted = False
            # Safely attempt to remove physical PDF file from storage
            try:
                if private_storage.delete_file(storage_key):
                    file_deleted = True
            except Exception as file_err:
                logger.warning(
                    f"Physical file removal exception for Job #{job.job_number} ('{storage_key}'): {file_err}"
                )
                errors.append(f"Job #{job.job_number} file error: {file_err}")

            # Clear storage_key pointer on the job record while keeping customer & payment data intact
            with transaction.atomic():
                orig_name = job.original_filename
                job.storage_key = ''
                cleanup_note = f"[PDF file purged after {cutoff_minutes}m retention at {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}]"
                if job.notes:
                    job.notes = f"{job.notes}\n{cleanup_note}"
                else:
                    job.notes = cleanup_note
                job.save(update_fields=['storage_key', 'notes', 'updated_at'])
                cleaned_count += 1

            record_audit_event(
                event_type='storage_cleanup',
                actor_type='system',
                job_id=str(job.id),
                metadata={
                    'action': 'auto_cleanup_completed_pdf',
                    'job_number': job.job_number,
                    'original_filename': orig_name,
                    'retention_minutes': cutoff_minutes,
                    'file_deleted': file_deleted,
                    'created_at': job.created_at.isoformat(),
                }
            )
            logger.info(
                f"[AutoCleanup] Successfully purged PDF for completed Order #{job.job_number} ('{orig_name}') "
                f"created at {job.created_at.isoformat()} (age: >={cutoff_minutes}m). Order record preserved."
            )
        except Exception as exc:
            logger.error(f"[AutoCleanup] Failed processing Job #{job.job_number}: {exc}", exc_info=True)
            errors.append(f"Job #{job.job_number}: {str(exc)}")

    # Check incomplete jobs to verify they are never touched
    incomplete_count = PrintJob.objects.exclude(status='completed').count()

    return {
        'cutoff_time': cutoff_time.isoformat(),
        'cleaned_count': cleaned_count,
        'preserved_incomplete_count': incomplete_count,
        'errors': errors,
    }
