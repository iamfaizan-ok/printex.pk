import uuid
import hashlib
import secrets
from django.db import models


class PrintStation(models.Model):
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('maintenance', 'Maintenance'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, help_text="e.g. Main Print Facility - Windows Station 1")
    station_code = models.CharField(max_length=60, unique=True, db_index=True)
    auth_token_hash = models.CharField(max_length=128, help_text="SHA-256 hashed agent secret token")
    
    # Authorized physical Windows printer identifiers (strict allowlist)
    allowed_printers = models.JSONField(
        default=list,
        help_text="Explicit allowlist of printer names registered on the Windows host"
    )
    
    # Media and print capabilities
    capabilities = models.JSONField(
        default=dict,
        help_text="Supported paper sizes, color modes, and duplex capabilities"
    )

    is_enabled = models.BooleanField(default=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline', db_index=True)
    agent_version = models.CharField(max_length=40, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['station_code']
        indexes = [
            models.Index(fields=['is_enabled', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.station_code}) - {self.status}"

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    def set_token(self, raw_token: str):
        self.auth_token_hash = self.hash_token(raw_token)

    def check_token(self, raw_token: str) -> bool:
        return secrets.compare_digest(self.auth_token_hash, self.hash_token(raw_token))

    def update_heartbeat(self, agent_version: str = '', ip: str = None):
        from django.utils import timezone
        self.last_heartbeat_at = timezone.now()
        self.status = 'online'
        if agent_version:
            self.agent_version = agent_version
        if ip:
            self.ip_address = ip
        self.save(update_fields=['last_heartbeat_at', 'status', 'agent_version', 'ip_address', 'updated_at'])
