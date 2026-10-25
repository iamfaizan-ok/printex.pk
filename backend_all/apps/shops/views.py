from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from drf_spectacular.utils import extend_schema

from .models import Shop
from .serializers import ShopPublicSerializer
from .services import get_or_create_default_shop


class ShopListView(APIView):
    """
    GET /api/v1/shops/
    Returns all active print shops with their identifiers, addresses, and customer URLs.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="List all active print shops")
    def get(self, request):
        # Guarantee at least default shop exists
        get_or_create_default_shop()
        shops = Shop.objects.filter(is_active=True).order_by('name')
        serializer = ShopPublicSerializer(shops, many=True, context={'request': request})
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class ShopDetailView(APIView):
    """
    GET /api/v1/shops/{shop_id}/
    Returns details for a specific shop identified by shop_id or UUID.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Get print shop details")
    def get(self, request, shop_id):
        shop = Shop.objects.filter(shop_id=shop_id, is_active=True).first()
        if not shop:
            try:
                shop = Shop.objects.filter(id=shop_id, is_active=True).first()
            except Exception:
                shop = None

        if not shop:
            return Response(
                {"success": False, "message": f"Shop '{shop_id}' not found or inactive."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ShopPublicSerializer(shop, context={'request': request})
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class ShopQRCodeView(APIView):
    """
    GET /api/v1/shops/{shop_id}/qr/
    Renders high-resolution PNG QR code directly into phone scanners and browser displays.
    Optimized with fast HTTP caching.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Get physical QR code PNG for shop")
    def get(self, request, shop_id):
        shop = Shop.objects.filter(shop_id=shop_id, is_active=True).first()
        if not shop:
            try:
                shop = Shop.objects.filter(id=shop_id, is_active=True).first()
            except Exception:
                shop = None

        if not shop:
            raise Http404("Shop not found.")

        # Determine frontend portal URL base
        origin = request.headers.get('Origin') or request.headers.get('Referer')
        base_url = None
        if origin and 'localhost:3000' in origin:
            base_url = 'http://localhost:3000'
        elif origin and '127.0.0.1:3000' in origin:
            base_url = 'http://127.0.0.1:3000'

        png_bytes = shop.generate_qr_bytes(base_url=base_url)

        response = HttpResponse(png_bytes, content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="{shop.shop_id}_qr.png"'
        response['Cache-Control'] = 'public, max-age=86400'
        return response
