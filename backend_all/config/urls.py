from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from django.http import HttpResponseRedirect
from django.views.static import serve

def admin_panel_view(request, path=''):
    if not path or path == '/':
        return HttpResponseRedirect('/admin-panel/login.html')
    return serve(request, path, document_root=str(settings.ADMIN_SIDE_DIR))

urlpatterns = [
    # Redirect root to admin panel login
    path('', lambda request: HttpResponseRedirect('/admin-panel/login.html'), name='root-redirect'),

    path('admin/', admin.site.urls),

    # Admin Panel Static Frontend (admin_side)
    path('admin-panel/', admin_panel_view, {'path': 'login.html'}, name='admin-panel-root'),
    path('admin-panel/<path:path>', admin_panel_view, name='admin-panel-static'),

    # Customer & Core Printing APIs
    path('api/v1/', include('apps.printing.urls')),

    # Payments API
    path('api/v1/payments/', include('apps.payments.urls')),

    # Windows PC Print Agent Authenticated APIs
    path('api/v1/agent/', include('apps.devices.urls')),

    # Interactive OpenAPI / Swagger Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

