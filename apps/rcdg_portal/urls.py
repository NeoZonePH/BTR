from django.urls import path
from apps.reservist_portal.portal_views import get_portal_dashboard
from apps.reservist_portal.views import incident_list, incident_detail, update_incident_status, analytics_dashboard, chart_data, generate_summary
from . import views

app_name = 'rcdg'

dashboard = get_portal_dashboard('RCDG', 'rcdg_portal/command_dashboard.html')

urlpatterns = [
    path('dashboard/', dashboard, name='rcdg_dashboard'),
    path('incidents/', incident_list, name='rcdg_incident_list'),
    path('incidents/<int:pk>/', incident_detail, name='rcdg_incident_detail'),
    path('incidents/<int:pk>/status/', update_incident_status, name='rcdg_update_status'),
    path('responders/', views.responder_records, name='rcdg_responder_records'),
    path('analytics/', analytics_dashboard, name='rcdg_analytics'),
    path('analytics/chart-data/', chart_data, name='rcdg_chart_data'),
    path('analytics/generate-summary/', generate_summary, name='rcdg_generate_summary'),

    # Account management — CDC (RCDG-scoped)
    path('accounts/manage/cdc/', views.manage_cdc_accounts, name='manage_cdc_accounts'),
    path('accounts/manage/cdc/create/', views.create_cdc_account, name='create_cdc_account'),
    path('accounts/manage/cdc/<int:pk>/edit/', views.edit_cdc_account, name='edit_cdc_account'),
    path('accounts/manage/cdc/<int:pk>/delete/', views.delete_cdc_account, name='delete_cdc_account'),
]
