from rest_framework import serializers
from .models import Shop, ShopStaff


class ShopPublicSerializer(serializers.ModelSerializer):
    """
    Public shop metadata for customer selection & QR code scanning.
    """
    qr_url = serializers.SerializerMethodField()
    customer_url = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = [
            'id',
            'shop_id',
            'name',
            'slug',
            'address',
            'phone',
            'email',
            'qr_url',
            'customer_url',
            'is_active',
        ]

    def get_qr_url(self, obj):
        request = self.context.get('request')
        if obj.qr_code_image and hasattr(obj.qr_code_image, 'url'):
            url = obj.qr_code_image.url
            if request:
                return request.build_absolute_uri(url)
            return url
        # Fallback to dynamic QR endpoint
        if request:
            return request.build_absolute_uri(f"/api/v1/shops/{obj.shop_id}/qr/")
        return f"/api/v1/shops/{obj.shop_id}/qr/"

    def get_customer_url(self, obj):
        request = self.context.get('request')
        base = None
        if request:
            base = f"{request.scheme}://{request.get_host()}"
        return obj.get_customer_portal_url(base)


class ShopStaffSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    shop_id = serializers.CharField(source='shop.shop_id', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)

    class Meta:
        model = ShopStaff
        fields = [
            'id',
            'username',
            'email',
            'shop_id',
            'shop_name',
            'role',
            'is_approved',
            'created_at',
        ]
