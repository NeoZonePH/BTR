from django.urls import path
from . import views

urlpatterns = [
    path('regions/', views.get_regions, name='ref_regions'),
    path('provinces/', views.get_provinces, name='ref_provinces'),
    path('cities/', views.get_cities, name='ref_cities'),
    path('barangays/', views.get_barangays, name='ref_barangays'),
    path('rcdgs/', views.get_rcdgs, name='ref_rcdgs'),
    path('cdcs/', views.get_cdcs, name='ref_cdcs'),
]
