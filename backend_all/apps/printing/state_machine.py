import logging
from typing import Set
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import PrintJob

logger = logging.getLogger(__name__)

# Allowed state transitions graph
VALID_TRANSITIONS = {
    'queued': {'claimed', 'cancelled', 'failed', 'submitting_to_printer', 'submitted_to_printer'},
    'claimed': {'downloading', 'ready_to_print', 'queued', 'failed', 'cancelled'},
    'downloading': {'ready_to_print', 'claimed', 'queued', 'failed'},
    'ready_to_print': {'submitting_to_printer', 'failed', 'cancelled'},
    'submitting_to_printer': {'submitted_to_printer', 'completed', 'outcome_unknown', 'failed'},
    'submitted_to_printer': {'completed', 'outcome_unknown', 'failed'},
    'outcome_unknown': {'completed', 'failed'},  # Manual operator / verification reconciliation
    'failed': {'queued'},  # Explicit retry if permitted
    'completed': set(),    # Terminal state
    'cancelled': set(),    # Terminal state
}


def transition_job_status(
    job: PrintJob,
    new_status: str,
    error_code: str = '',
    error_message: str = '',
    actor: str = 'system'
) -> PrintJob:
    """
    Validates and executes an atomic state transition for a PrintJob.
    Raises ValidationError if transition is invalid.
    """
    current_status = job.status
    allowed_targets: Set[str] = VALID_TRANSITIONS.get(current_status, set())

    if new_status not in allowed_targets:
        err_msg = (
            f"Illegal state transition: Job '{job.job_number}' cannot transition from "
            f"'{current_status}' to '{new_status}'."
        )
        logger.warning(err_msg)
        raise ValidationError({"status": err_msg})

    job.status = new_status

    now = timezone.now()
    if new_status == 'claimed' and not job.claimed_at:
        job.claimed_at = now
    elif new_status == 'submitted_to_printer':
        job.submitted_at = now
    elif new_status == 'completed':
        job.completed_at = now
    elif new_status in ['failed', 'outcome_unknown']:
        job.error_code = error_code
        job.error_message = error_message

    job.save(update_fields=[
        'status', 'assigned_station', 'claimed_at', 'submitted_at', 'completed_at',
        'error_code', 'error_message', 'updated_at'
    ])

    # Keep parent Order status aligned with child files
    if job.order:
        try:
            sibling_statuses = set(job.order.files.values_list('status', flat=True))
            if sibling_statuses == {'completed'}:
                job.order.status = 'completed'
                job.order.save(update_fields=['status', 'updated_at'])
            elif 'submitted_to_printer' in sibling_statuses:
                job.order.status = 'submitted_to_printer'
                job.order.save(update_fields=['status', 'updated_at'])
            elif 'submitting_to_printer' in sibling_statuses:
                job.order.status = 'submitting_to_printer'
                job.order.save(update_fields=['status', 'updated_at'])
        except Exception as e:
            logger.debug(f"Failed to synchronize parent order status: {e}")

    logger.info(f"Job '{job.job_number}' transitioned from '{current_status}' to '{new_status}' by {actor}.")
    return job
