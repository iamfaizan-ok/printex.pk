from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PrintJob, PrintJobAttempt
from apps.audit.models import AuditEvent

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff', 'is_superuser']


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})


class AdminBlockSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, default="Blocked by shop administrator", max_length=500)


class AdminPrintJobSummarySerializer(serializers.ModelSerializer):
    """
    Compact single-row summary serializer for the All Order Prints dashboard.
    """
    can_block = serializers.SerializerMethodField()
    can_unblock = serializers.SerializerMethodField()
    can_print = serializers.SerializerMethodField()
    can_pay_ok = serializers.SerializerMethodField()
    is_cash_pending = serializers.SerializerMethodField()
    assigned_station_name = serializers.CharField(source='assigned_station.name', read_only=True)

    class Meta:
        model = PrintJob
        fields = [
            'id',
            'job_number',
            'original_filename',
            'customer_name',
            'customer_phone',
            'page_count',
            'copies',
            'paper_size',
            'colour_mode',
            'sides',
            'total_impressions',
            'estimated_sheets',
            'total_amount',
            'currency',
            'payment_status',
            'approval_status',
            'status',
            'target_printer_name',
            'assigned_station_name',
            'created_at',
            'updated_at',
            'approved_at',
            'blocked_at',
            'blocked_reason',
            'payment_approved_at',
            # Action capability flags for UI rendering
            'can_block',
            'can_unblock',
            'can_print',
            'can_pay_ok',
            'is_cash_pending',
        ]

    def get_can_block(self, obj: PrintJob) -> bool:
        return obj.can_be_blocked() and obj.approval_status != 'blocked'

    def get_can_unblock(self, obj: PrintJob) -> bool:
        return obj.can_be_unblocked()

    def get_can_print(self, obj: PrintJob) -> bool:
        return obj.can_be_printed()

    def get_can_pay_ok(self, obj: PrintJob) -> bool:
        return obj.can_approve_cash()

    def get_is_cash_pending(self, obj: PrintJob) -> bool:
        return obj.payment_status == 'cash_pending'


class PrintJobAttemptSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)

    class Meta:
        model = PrintJobAttempt
        fields = ['id', 'attempt_number', 'status', 'started_at', 'finished_at', 'diagnostic_details', 'station_name']


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ['id', 'event_type', 'actor_type', 'actor_identifier', 'created_at', 'metadata']


class AdminPrintJobDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer including attempts, approval history and audit trail.
    """
    attempts = PrintJobAttemptSerializer(many=True, read_only=True)
    audit_events = serializers.SerializerMethodField()
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)
    blocked_by_username = serializers.CharField(source='blocked_by.username', read_only=True)
    payment_approved_by_username = serializers.CharField(source='payment_approved_by.username', read_only=True)

    class Meta:
        model = PrintJob
        fields = '__all__'

    def get_audit_events(self, obj: PrintJob):
        events = AuditEvent.objects.filter(job_id=obj.id).order_by('-created_at')[:20]
        return AuditEventSerializer(events, many=True).data
