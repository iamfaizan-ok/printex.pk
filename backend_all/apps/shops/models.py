import io
import uuid
import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.utils.text import slugify


class Shop(models.Model):
    """
    Multi-tenant Shop Model.
    Each shop has a unique shop_id, customer-facing QR code, and isolated orders and prints.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop_id = models.CharField(
        max_length=60,
        unique=True,
        db_index=True,
        help_text="Unique human-readable shop identifier, e.g., 'shop-main-01' or 'STN-MAIN-01'"
    )
    name = models.CharField(max_length=150, help_text="Public store name")
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    address = models.TextField(blank=True, help_text="Physical shop address")
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    qr_code_image = models.ImageField(upload_to='shop_qrs/', blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['shop_id']
        verbose_name = 'Print Shop'
        verbose_name_plural = 'Print Shops'

    def __str__(self):
        return f"{self.name} ({self.shop_id})"

    def get_customer_portal_url(self, base_url: str = None) -> str:
        """
        Builds the target URL encoded in the physical QR code.
        Directs customer phone cameras straight to PrintX ordering with this shop preselected.
        """
        if not base_url:
            base_url = getattr(settings, 'FRONTEND_PORTAL_URL', 'http://localhost:3000')
        base_url = base_url.rstrip('/')
        return f"{base_url}/?shop={self.shop_id}"

    def generate_qr_bytes(self, base_url: str = None) -> bytes:
        """
        Generates PNG bytes for the shop's QR code.
        """
        target_url = self.get_customer_portal_url(base_url)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(target_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def ensure_qr_code_image(self, base_url: str = None):
        """
        Ensures the QR code image is generated and saved to media storage.
        """
        if not self.qr_code_image:
            png_bytes = self.generate_qr_bytes(base_url)
            filename = f"{self.shop_id}_qr.png"
            self.qr_code_image.save(filename, ContentFile(png_bytes), save=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.shop_id or self.name or str(uuid.uuid4())[:8])
        if not self.qr_code_image:
            try:
                self.ensure_qr_code_image()
            except Exception:
                pass
        super().save(*args, **kwargs)


class ShopStaff(models.Model):
    """
    Links Django Admin/Staff users to their authorized Print Shop.
    Enforces strict least-privilege shop isolation.
    """
    ROLE_CHOICES = [
        ('manager', 'Shop Manager'),
        ('operator', 'Print Operator'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shop_profile'
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='staff_members'
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='manager')
    is_approved = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Requires approval for non-invite admin signups"
    )
    google_sub = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
        help_text="Google OAuth 2.0 subject identifier for linked accounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Shop Staff Profile'
        verbose_name_plural = 'Shop Staff Profiles'

    def __str__(self):
        return f"{self.user.username} -> {self.shop.name} ({self.role})"
