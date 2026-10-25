from django.urls import path
from .views import ShopListView, ShopDetailView, ShopQRCodeView

urlpatterns = [
    path('', ShopListView.as_view(), name='shops-list'),
    path('<str:shop_id>/', ShopDetailView.as_view(), name='shops-detail'),
    path('<str:shop_id>/qr/', ShopQRCodeView.as_view(), name='shops-qr'),
]
