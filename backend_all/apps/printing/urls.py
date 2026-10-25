from django.urls import path
from .views import (
    HealthCheckView,
    PrintOptionsView,
    PrintJobListCreateView,
    PrintJobDetailView,
    PrintJobStatusView,
    PrintJobCancelView,
    PrintJobDirectPrintView,
    DocumentUploadView,
    PricingCalculateView,
    OrderCreateView,
)
from .admin_views import (
    AdminLoginView,
    AdminSignupView,
    AdminPasswordResetRequestView,
    AdminPasswordResetConfirmView,
    AdminGoogleAuthView,
    AdminMyShopView,
    AdminLogoutView,
    AdminMeView,
    AdminPrintJobListView,
    AdminPrintJobDetailView,
    AdminPrintJobBlockView,
    AdminPrintJobUnblockView,
    AdminPrintJobPayOkView,
    AdminPrintJobAuthorizePrintView,
    AdminPrintJobClearAllView,
    AdminFileDownloadView,
)


urlpatterns = [
    # Core Spec Endpoints (Section 5)
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('print-options/', PrintOptionsView.as_view(), name='print-options'),
    path('print-jobs/', PrintJobListCreateView.as_view(), name='print-jobs-list-create'),
    path('print-jobs/<str:job_id>/', PrintJobDetailView.as_view(), name='print-jobs-detail'),
    path('print-jobs/<str:job_id>/print/', PrintJobDirectPrintView.as_view(), name='print-jobs-direct-print'),
    path('print-jobs/<str:job_id>/status/', PrintJobStatusView.as_view(), name='print-jobs-status'),
    path('print-jobs/<str:job_id>/cancel/', PrintJobCancelView.as_view(), name='print-jobs-cancel'),

    # Frontend Compatibility Endpoints (BACKEND_API_SPEC.md & userApis.ts)
    path('documents/upload/', DocumentUploadView.as_view(), name='api-documents-upload'),
    path('pricing/calculate/', PricingCalculateView.as_view(), name='api-pricing-calculate'),
    path('orders/', OrderCreateView.as_view(), name='api-orders'),
    path('orders/create/', OrderCreateView.as_view(), name='api-orders-create'),
    path('orders/track/', PrintJobDetailView.as_view(), name='api-orders-track'),
    path('orders/<str:job_id>/', PrintJobDetailView.as_view(), name='api-orders-detail'),

    # Admin Portal Authentication & Shop APIs
    path('admin/auth/login/', AdminLoginView.as_view(), name='admin-auth-login'),
    path('admin/auth/signup/', AdminSignupView.as_view(), name='admin-auth-signup'),
    path('admin/auth/logout/', AdminLogoutView.as_view(), name='admin-auth-logout'),
    path('admin/auth/me/', AdminMeView.as_view(), name='admin-auth-me'),
    path('admin/auth/password-reset/', AdminPasswordResetRequestView.as_view(), name='admin-auth-password-reset'),
    path('admin/auth/password-reset-confirm/', AdminPasswordResetConfirmView.as_view(), name='admin-auth-password-reset-confirm'),
    path('admin/auth/google/', AdminGoogleAuthView.as_view(), name='admin-auth-google'),
    path('admin/my-shop/', AdminMyShopView.as_view(), name='admin-my-shop'),

    # Admin Portal Order & Print Management
    path('admin/print-jobs/', AdminPrintJobListView.as_view(), name='admin-print-jobs-list'),
    path('admin/print-jobs/clear-all/', AdminPrintJobClearAllView.as_view(), name='admin-print-jobs-clear-all'),
    path('admin/print-jobs/<str:job_id>/', AdminPrintJobDetailView.as_view(), name='admin-print-jobs-detail'),
    path('admin/print-jobs/<str:job_id>/download/', AdminFileDownloadView.as_view(), name='admin-print-jobs-download'),
    path('admin/print-jobs/<str:job_id>/block/', AdminPrintJobBlockView.as_view(), name='admin-print-jobs-block'),
    path('admin/print-jobs/<str:job_id>/unblock/', AdminPrintJobUnblockView.as_view(), name='admin-print-jobs-unblock'),
    path('admin/print-jobs/<str:job_id>/pay-ok/', AdminPrintJobPayOkView.as_view(), name='admin-print-jobs-pay-ok'),
    path('admin/print-jobs/<str:job_id>/authorize-print/', AdminPrintJobAuthorizePrintView.as_view(), name='admin-print-jobs-authorize-print'),
]

