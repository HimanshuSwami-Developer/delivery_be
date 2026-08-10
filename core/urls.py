"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    # Standard simplejwt refresh — separate from accounts.urls since it's
    # framework-provided, not one of our OTP views.
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Domain APIs — same endpoints serve both the customer app and the
    # admin console; per-resource read/write is split by role via
    # `core/permissions.py` (IsAdminRoleOrReadOnly etc.), not by separate
    # URL prefixes.
    path('api/', include('zones.urls')),
    path('api/', include('catalog.urls')),
    path('api/', include('delivery.urls')),
    path('api/', include('cart.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('promotions.urls')),
    path('api/', include('support.urls')),
    path('api/admin/reports/', include('reports.urls')),

     # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

]
