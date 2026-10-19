from rest_framework import serializers
from .models import PrintJob, PrintJobAttempt


class PrintJobCreateSerializer(serializers.Serializer):
    """
    Serializer for POST /api/v1/print-jobs/ (multipart/form-data)
    """
    file = serializers.FileField(required=True)
    customer_name = serializers.CharField(max_length=120, default="Customer")
    customer_email = serializers.EmailField(required=False, default="")
    customer_phone = serializers.CharField(max_length=40, default="0300-0000000")
    delivery_method = serializers.ChoiceField(
        choices=['pickup', 'standard_delivery', 'express_delivery'],
        default='pickup'
    )
    delivery_address = serializers.CharField(required=False, default="")
    notes = serializers.CharField(required=False, default="")

    # Settings
    copies = serializers.IntegerField(default=1, min_value=1, max_value=100)
    paper_size = serializers.ChoiceField(choices=['A4', 'A3', 'Letter', 'Legal'], default='A4')
    colour_mode = serializers.ChoiceField(choices=['colour', 'bw'], default='bw')
    orientation = serializers.ChoiceField(choices=['portrait', 'landscape'], default='portrait')
    sides = serializers.ChoiceField(choices=['single', 'double'], default='single')
    page_range = serializers.CharField(default='all')
    payment_method = serializers.CharField(required=False, default='cash_on_delivery')


class PrintJobDetailsSerializer(serializers.ModelSerializer):
    """
    Full public details returned to authorized customer.
    """
    status_url = serializers.SerializerMethodField()

    class Meta:
        model = PrintJob
        fields = [
            'id',
            'job_number',
            'access_token',
            'status',
            'customer_name',
            'customer_phone',
            'delivery_method',
            'original_filename',
            'file_size_bytes',
            'page_count',
            'selected_pages_count',
            'copies',
            'paper_size',
            'colour_mode',
            'orientation',
            'sides',
            'page_range',
            'total_impressions',
            'estimated_sheets',
            'subtotal',
            'delivery_fee',
            'tax',
            'total_amount',
            'currency',
            'payment_status',
            'created_at',
            'updated_at',
            'status_url',
        ]
        read_only_fields = fields

    def get_status_url(self, obj):
        request = self.context.get('request')
        relative_url = f"/api/v1/print-jobs/{obj.id}/status/"
        return request.build_absolute_uri(relative_url) if request else relative_url


class PrintJobStatusSerializer(serializers.ModelSerializer):
    """
    Lightweight status tracking for polling.
    """
    class Meta:
        model = PrintJob
        fields = [
            'id',
            'job_number',
            'status',
            'created_at',
            'claimed_at',
            'submitted_at',
            'completed_at',
            'error_code',
            'error_message',
        ]
        read_only_fields = fields


class AgentJobClaimSerializer(serializers.ModelSerializer):
    """
    Payload returned to the PC Print Agent when a job is claimed.
    Includes short-lived download URL and required print options.
    """
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = PrintJob
        fields = [
            'id',
            'job_number',
            'status',
            'original_filename',
            'file_size_bytes',
            'file_sha256',
            'page_count',
            'selected_pages_count',
            'paper_size',
            'colour_mode',
            'orientation',
            'sides',
            'copies',
            'page_range',
            'download_url',
        ]
        read_only_fields = fields

    def get_download_url(self, obj):
        request = self.context.get('request')
        url = f"/api/v1/agent/jobs/{obj.id}/download/"
        return request.build_absolute_uri(url) if request else url
