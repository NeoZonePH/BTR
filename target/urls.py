"""TARGET URL Configuration."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls')),
    path('', include('users.urls')),
    path('reservist/', include('reservist_portal.urls')),
    path('rescom/', include('rescom_portal.urls')),
    path('rcdg/', include('rcdg_portal.urls')),
    path('cdc/', include('cdc_portal.urls')),
    path('pdrrmo/', include('pdrrmo_portal.urls')),
    path('mdrrmo/', include('mdrrmo_portal.urls')),
    path('references/', include('references.urls')),
    path('api/', include('reservist_portal.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
