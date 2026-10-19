import uuid
from django.db import models


class PaymentTransaction(models.Model):
    PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
        ('jazzcash', 'JazzCash'),
        ('easypaisa', 'EasyPaisa'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash On Delivery'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('requires_action', 'Requires Customer Action'),
        ('succeeded', 'Payment Succeeded'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        'printing.PrintJob',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    provider = models.CharField(max_length=40, choices=PROVIDER_CHOICES)
    provider_transaction_id = models.CharField(max_length=120, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='PKR')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', db_index=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.provider} ({self.amount} {self.currency}) - {self.status}"
