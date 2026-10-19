import uuid
from django.db import models


class AuditEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('job_created', 'Print Job Created'),
        ('job_queued', 'Job Queued'),
        ('job_claimed', 'Job Claimed by Station'),
        ('job_status_updated', 'Job Status Updated'),
        ('job_cancelled', 'Job Cancelled'),
        ('job_blocked', 'Job Blocked by Admin'),
        ('job_unblocked', 'Job Unblocked by Admin'),
        ('job_approved', 'Job Printing Approved'),
        ('pay_ok_approved', 'Cash Payment Approved (Pay OK)'),
        ('job_downloaded', 'Job PDF Downloaded by Agent'),
        ('agent_heartbeat', 'Agent Heartbeat'),
        ('agent_registered', 'Agent Registered'),
        ('payment_intent', 'Payment Intent Created'),
        ('payment_verified', 'Payment Verified'),
        ('security_warning', 'Security Alert / Warning'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, db_index=True)
    actor_type = models.CharField(max_length=30, default='system')  # customer, agent, system, admin
    actor_identifier = models.CharField(max_length=120, blank=True)
    job_id = models.UUIDField(null=True, blank=True, db_index=True)
    station_id = models.UUIDField(null=True, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['job_id', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {self.event_type} ({self.actor_type})"
