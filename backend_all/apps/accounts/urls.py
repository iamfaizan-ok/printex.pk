from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    RegisterShopView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    GoogleAuthView,
    AdminMeView,
    AdminMyShopView,
)

urlpatterns = [
    # Login & Logout
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Shop Registration (Admin & Shop creation)
    path('register-shop/', RegisterShopView.as_view(), name='register-shop'),
    path('signup/', RegisterShopView.as_view(), name='signup'),  # Alias

    # Password Reset
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # Google OAuth 2.0 Sign In
    path('google/', GoogleAuthView.as_view(), name='google-auth'),

    # Profile & Assigned Shop
    path('me/', AdminMeView.as_view(), name='me'),
    path('my-shop/', AdminMyShopView.as_view(), name='my-shop'),
]
