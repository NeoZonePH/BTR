"""TARGET URL Configuration."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls')),
    path('', include('users.urls')),
    path('reservist/', include('apps.reservist_portal.urls')),
    path('rescom/', include('apps.rescom_portal.urls')),
    path('rcdg/', include('apps.rcdg_portal.urls')),
    path('cdc/', include('apps.cdc_portal.urls')),
    path('pdrrmo/', include('apps.pdrrmo_portal.urls')),
    path('mdrrmo/', include('apps.mdrrmo_portal.urls')),
    path('references/', include('references.urls')),
    path('api/', include('apps.reservist_portal.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
