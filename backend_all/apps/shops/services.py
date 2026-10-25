import logging
from typing import Optional
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Shop, ShopStaff

logger = logging.getLogger("PrintX.Shops")
User = get_user_model()


def get_or_create_default_shop() -> Shop:
    """
    Returns the primary default shop or provisions one automatically.
    Guarantees seamless fallback for legacy orders and fresh deployments.
    """
    shop = Shop.objects.filter(is_active=True).first()
    if not shop:
        shop = Shop.objects.create(
            shop_id='shop-main-01',
            name='PrintX Main Facility',
            address='Commercial Center, Blue Area, Islamabad',
            phone='+92-300-1234567',
            email='support@printx.pk',
            is_active=True
        )
        logger.info(f"Initialized default print shop: {shop}")
    return shop


def get_user_shop(user) -> Optional[Shop]:
    """
    Retrieves the shop assigned to the given user, if any.
    Returns None if user is unauthenticated or has no assigned shop profile.
    """
    if not user or not user.is_authenticated:
        return None
    try:
        if hasattr(user, 'shop_profile') and user.shop_profile and user.shop_profile.is_approved:
            return user.shop_profile.shop
    except Exception:
        pass
    return None


def user_has_shop_access(user, target_shop: Optional[Shop]) -> bool:
    """
    Verifies if user is authorized to view or manage data belonging to target_shop.
    - Superusers have global oversight access across all shops.
    - Shop managers/operators can ONLY access their assigned shop.
    - If target_shop is None: superusers can access; regular staff cannot access unassigned data.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False

    assigned_shop = get_user_shop(user)
    if not assigned_shop or not target_shop:
        return False

    return str(assigned_shop.id) == str(target_shop.id) or assigned_shop.shop_id == target_shop.shop_id


def link_user_to_shop(user, shop: Shop, role: str = 'manager', is_approved: bool = True) -> ShopStaff:
    """
    Safely links or updates a staff user's shop assignment.
    """
    profile, created = ShopStaff.objects.update_or_create(
        user=user,
        defaults={
            'shop': shop,
            'role': role,
            'is_approved': is_approved,
        }
    )
    return profile
