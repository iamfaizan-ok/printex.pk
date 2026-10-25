from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    shop = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'shop']

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


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})


class RegisterShopSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, min_length=3, max_length=150, trim_whitespace=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, min_length=8, write_only=True, style={'input_type': 'password'})
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    
    # Shop fields (supports either 'shop_name' or 'new_shop_name' for full compatibility)
    shop_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    new_shop_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    shop_address = serializers.CharField(required=False, allow_blank=True)
    new_shop_address = serializers.CharField(required=False, allow_blank=True)
    shop_phone = serializers.CharField(required=False, allow_blank=True, max_length=50)
    new_shop_phone = serializers.CharField(required=False, allow_blank=True, max_length=50)
    shop_id = serializers.CharField(required=False, allow_blank=True, max_length=60)
    registration_key = serializers.CharField(required=False, allow_blank=True, max_length=128)

    def validate_password(self, value):
        validate_password(value)
        return value

    def get_resolved_shop_name(self):
        return (self.validated_data.get('shop_name') or self.validated_data.get('new_shop_name') or '').strip()

    def get_resolved_shop_address(self):
        return (self.validated_data.get('shop_address') or self.validated_data.get('new_shop_address') or '').strip()

    def get_resolved_shop_phone(self):
        return (self.validated_data.get('shop_phone') or self.validated_data.get('new_shop_phone') or '').strip()


# Backward compatibility aliases
AdminLoginSerializer = LoginSerializer
AdminSignupSerializer = RegisterShopSerializer


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8, write_only=True, style={'input_type': 'password'})

    def validate_new_password(self, value):
        validate_password(value)
        return value


class GoogleAuthSerializer(serializers.Serializer):
    credential = serializers.CharField(required=True, help_text="Google OAuth 2.0 ID Token / JWT credential")
    shop_id = serializers.CharField(required=False, allow_blank=True)
