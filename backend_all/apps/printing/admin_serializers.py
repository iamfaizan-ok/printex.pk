from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Order, PrintJob, PrintJobAttempt
from apps.audit.models import AuditEvent

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    shop = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff', 'is_superuser', 'shop']

    def get_shop(self, obj):
        try:
            if hasattr(obj, 'shop_profile') and obj.shop_profile and obj.shop_profile.is_approved:
                s = obj.shop_profile.shop
                return {
                    'shop_id': s.shop_id,
                    'name': s.name,
                    'address': s.address,
                    'phone': s.phone,
                    'role': obj.shop_profile.role,
                    'qr_url': f"/api/v1/shops/{s.shop_id}/qr/",
                    'customer_url': s.get_customer_portal_url(),
                }
        except Exception:
            pass
        if obj.is_superuser:
            return {
                'shop_id': 'all',
                'name': 'All Print Shops (Superadmin Mode)',
                'address': 'Global Administrative Console',
                'phone': '',
                'role': 'superuser',
                'qr_url': None,
                'customer_url': None,
            }
        return None


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})


class AdminSignupSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, min_length=3, max_length=150, trim_whitespace=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, min_length=8, write_only=True, style={'input_type': 'password'})
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    shop_id = serializers.CharField(required=False, allow_blank=True, max_length=60)
    new_shop_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    new_shop_address = serializers.CharField(required=False, allow_blank=True)
    new_shop_phone = serializers.CharField(required=False, allow_blank=True, max_length=50)
    registration_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class AdminPasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class AdminPasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8, write_only=True, style={'input_type': 'password'})


class AdminGoogleAuthSerializer(serializers.Serializer):
    credential = serializers.CharField(required=True, help_text="Google OAuth 2.0 ID Token")
    shop_id = serializers.CharField(required=False, allow_blank=True, max_length=60)
    new_shop_name = serializers.CharField(required=False, allow_blank=True, max_length=150)


class AdminBlockSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, default="Blocked by shop administrator", max_length=500)


class AdminOrderFileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    view_url = serializers.SerializerMethodField()
    file_available = serializers.SerializerMethodField()

    class Meta:
        model = PrintJob
        fields = [
            'id',
            'job_number',
            'original_filename',
            'file_size_bytes',
            'page_count',
            'copies',
            'paper_size',
            'colour_mode',
            'orientation',
            'sides',
            'page_range',
            'total_impressions',
            'estimated_sheets',
            'total_amount',
            'status',
            'download_url',
            'view_url',
            'file_available',
            'created_at',
        ]

    def get_download_url(self, obj: PrintJob) -> str:
        return f"/api/v1/admin/print-jobs/{obj.id}/download/"

    def get_view_url(self, obj: PrintJob) -> str:
        return f"/api/v1/admin/print-jobs/{obj.id}/download/?inline=1"

    def get_file_available(self, obj: PrintJob) -> bool:
        return bool(obj.storage_key)


class AdminOrderSummarySerializer(serializers.ModelSerializer):
    """
    Serializer representing one complete Order entry, including all its associated PDF files.
    """
    job_number = serializers.CharField(source='order_number', read_only=True)
    shop_id = serializers.CharField(source='shop.shop_id', read_only=True, default='')
    shop_name = serializers.CharField(source='shop.name', read_only=True, default='')
    pdf_count = serializers.IntegerField(source='files.count', read_only=True)
    files = AdminOrderFileSerializer(many=True, read_only=True)
    can_block = serializers.SerializerMethodField()
    can_unblock = serializers.SerializerMethodField()
    can_print = serializers.SerializerMethodField()
    can_pay_ok = serializers.SerializerMethodField()
    is_cash_pending = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'job_number',
            'shop_id',
            'shop_name',
            'customer_name',
            'customer_phone',
            'customer_email',
            'delivery_method',
            'delivery_address',
            'notes',
            'status',
            'approval_status',
            'payment_status',
            'total_impressions',
            'estimated_sheets',
            'subtotal',
            'delivery_fee',
            'tax',
            'total_amount',
            'currency',
            'created_at',
            'updated_at',
            'approved_at',
            'blocked_at',
            'blocked_reason',
            'payment_approved_at',
            'pdf_count',
            'files',
            'can_block',
            'can_unblock',
            'can_print',
            'can_pay_ok',
            'is_cash_pending',
        ]

    def get_can_block(self, obj: Order) -> bool:
        return obj.can_be_blocked() and obj.approval_status != 'blocked'

    def get_can_unblock(self, obj: Order) -> bool:
        return obj.can_be_unblocked()

    def get_can_print(self, obj: Order) -> bool:
        return obj.can_be_printed()

    def get_can_pay_ok(self, obj: Order) -> bool:
        return obj.can_approve_cash()

    def get_is_cash_pending(self, obj: Order) -> bool:
        return obj.payment_status == 'cash_pending'


class AdminPrintJobSummarySerializer(serializers.ModelSerializer):
    """
    Compact single-row summary serializer for backward compatibility.
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
            'notes',
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
