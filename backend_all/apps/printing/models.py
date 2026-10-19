import uuid
import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.devices.models import PrintStation


class PrintJob(models.Model):
    APPROVAL_CHOICES = [
        ('awaiting_review', 'Awaiting Review'),
        ('approved', 'Approved for Printing'),
        ('blocked', 'Blocked by Admin'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('cash_pending', 'Cash Payment Pending'),
        ('cash_received', 'Cash Payment Received'),
        ('online_payment_pending', 'Online Payment Pending'),
        ('paid', 'Paid Online'),
        ('payment_failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    ]

    STATUS_CHOICES = [
        ('queued', 'Queued for Printing'),
        ('claimed', 'Claimed by Station'),
        ('downloading', 'Downloading Document'),
        ('ready_to_print', 'Document Ready to Print'),
        ('submitting_to_printer', 'Submitting to Local OS Spooler'),
        ('submitted_to_printer', 'Submitted to Printer Spooler'),
        ('completed', 'Print Verified / Completed'),
        ('failed', 'Printing Failed'),
        ('outcome_unknown', 'Outcome Uncertain / Recheck Required'),
        ('cancelled', 'Job Cancelled'),
    ]

    PAPER_SIZE_CHOICES = [
        ('A4', 'A4'),
        ('A3', 'A3'),
        ('Letter', 'Letter'),
        ('Legal', 'Legal'),
    ]

    COLOUR_MODE_CHOICES = [
        ('bw', 'Black & White'),
        ('colour', 'Full Colour'),
    ]

    ORIENTATION_CHOICES = [
        ('portrait', 'Portrait'),
        ('landscape', 'Landscape'),
    ]

    SIDES_CHOICES = [
        ('single', 'Single Sided'),
        ('double', 'Double Sided / Duplex'),
    ]

    DELIVERY_METHOD_CHOICES = [
        ('pickup', 'Self Pickup'),
        ('standard_delivery', 'Standard Delivery'),
        ('express_delivery', 'Express Delivery'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_number = models.CharField(max_length=40, unique=True, db_index=True)
    access_token = models.CharField(max_length=64, db_index=True, help_text="Random unguessable access token")
    idempotency_key = models.CharField(max_length=128, blank=True, null=True, db_index=True)

    # Customer Information
    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=40)
    delivery_method = models.CharField(max_length=30, choices=DELIVERY_METHOD_CHOICES, default='pickup')
    delivery_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Document details & private storage
    original_filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=255, help_text="Relative path in private storage")
    file_size_bytes = models.BigIntegerField()
    file_sha256 = models.CharField(max_length=64, blank=True)
    page_count = models.IntegerField(default=1)
    selected_pages_count = models.IntegerField(default=1)

    # Print Configuration Settings
    paper_size = models.CharField(max_length=20, choices=PAPER_SIZE_CHOICES, default='A4')
    colour_mode = models.CharField(max_length=20, choices=COLOUR_MODE_CHOICES, default='bw')
    orientation = models.CharField(max_length=20, choices=ORIENTATION_CHOICES, default='portrait')
    sides = models.CharField(max_length=20, choices=SIDES_CHOICES, default='single')
    copies = models.PositiveIntegerField(default=1)
    page_range = models.CharField(max_length=100, default='all')

    # Calculated Totals
    total_impressions = models.PositiveIntegerField(default=1)
    estimated_sheets = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default='PKR')
    payment_status = models.CharField(
        max_length=30,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
        db_index=True
    )
    approval_status = models.CharField(
        max_length=30,
        choices=APPROVAL_CHOICES,
        default='awaiting_review',
        db_index=True
    )

    # Admin Approval & Block Audit Tracking
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_print_jobs'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='blocked_print_jobs'
    )
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_reason = models.TextField(blank=True)
    payment_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cash_approved_print_jobs'
    )
    payment_approved_at = models.DateTimeField(null=True, blank=True)

    # Queue & Station Assignment
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='queued', db_index=True)
    assigned_station = models.ForeignKey(
        PrintStation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='jobs'
    )
    target_printer_name = models.CharField(max_length=120, blank=True)

    # Life Cycle Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    claimed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Diagnostic & Errors
    error_code = models.CharField(max_length=60, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['assigned_station', 'status']),
            models.Index(fields=['approval_status', 'created_at']),
            models.Index(fields=['payment_status', 'created_at']),
            models.Index(fields=['approval_status', 'status']),
        ]

    def __str__(self):
        return f"{self.job_number} - {self.original_filename} ({self.status})"

    @staticmethod
    def generate_job_number() -> str:
        date_str = timezone.now().strftime('%Y%m%d')
        random_suffix = secrets.token_hex(3).upper()
        return f"PRX-{date_str}-{random_suffix}"

    @staticmethod
    def generate_access_token() -> str:
        return secrets.token_urlsafe(32)

    def can_be_cancelled(self) -> bool:
        """
        Cancellation is only permitted when job is queued or claimed.
        Once it is submitting_to_printer or completed, it cannot be safely cancelled.
        """
        return self.status in ['queued', 'claimed']

    def can_be_blocked(self) -> bool:
        return self.status not in ['completed', 'cancelled']

    def can_be_unblocked(self) -> bool:
        return self.approval_status == 'blocked'

    def can_be_printed(self) -> bool:
        is_unblocked = self.approval_status != 'blocked'
        # Eligible for print authorization if already paid, or cash is pending to be collected
        is_payable_or_paid = self.payment_status in ['cash_received', 'paid', 'cash_pending']
        is_not_already_printed = self.status not in ['submitting_to_printer', 'submitted_to_printer', 'completed']
        return is_unblocked and is_payable_or_paid and is_not_already_printed

    def can_approve_cash(self) -> bool:
        return self.payment_status == 'cash_pending'


class PrintJobAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(PrintJob, on_delete=models.CASCADE, related_name='attempts')
    station = models.ForeignKey(PrintStation, null=True, blank=True, on_delete=models.SET_NULL)
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    diagnostic_details = models.TextField(blank=True)

    class Meta:
        ordering = ['attempt_number']

    def __str__(self):
        return f"Job {self.job.job_number} - Attempt #{self.attempt_number} ({self.status})"
