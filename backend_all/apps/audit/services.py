import logging
from typing import Optional, Dict, Any
from .models import AuditEvent

logger = logging.getLogger(__name__)


def record_audit_event(
    event_type: str,
    actor_type: str = 'system',
    actor_identifier: str = '',
    job_id: Optional[str] = None,
    station_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """
    Safely creates an immutable audit event without throwing exceptions that block business logic.
    """
    clean_meta = metadata or {}
    # Filter out sensitive fields
    for secret_key in ['password', 'secret', 'token', 'auth_token', 'credit_card', 'cvv']:
        if secret_key in clean_meta:
            clean_meta[secret_key] = '[REDACTED]'

    try:
        event = AuditEvent.objects.create(
            event_type=event_type,
            actor_type=actor_type,
            actor_identifier=actor_identifier,
            job_id=job_id,
            station_id=station_id,
            ip_address=ip_address,
            metadata=clean_meta,
        )
        return event
    except Exception as e:
        logger.error(f"Failed to record audit event '{event_type}': {e}")
        return None
