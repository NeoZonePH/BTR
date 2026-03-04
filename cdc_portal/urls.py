from django.urls import path
from reservist_portal.portal_views import get_portal_dashboard
from reservist_portal.views import incident_list, incident_detail, update_incident_status, analytics_dashboard, chart_data, generate_summary
from . import views

app_name = 'cdc'

dashboard = get_portal_dashboard('CDC', 'cdc_portal/command_dashboard.html')

urlpatterns = [
    path('dashboard/', dashboard, name='cdc_dashboard'),
    path('incidents/', incident_list, name='cdc_incident_list'),
    path('incidents/<int:pk>/', incident_detail, name='cdc_incident_detail'),
    path('incidents/<int:pk>/status/', update_incident_status, name='cdc_update_status'),
    path('analytics/', analytics_dashboard, name='cdc_analytics'),
    path('analytics/chart-data/', chart_data, name='cdc_chart_data'),
    path('analytics/generate-summary/', generate_summary, name='cdc_generate_summary'),

    # Account management — DRRMO (CDC-scoped)
    path('accounts/manage/drrmo/', views.manage_drrmo_accounts, name='manage_drrmo_accounts'),
    path('accounts/manage/drrmo/create/', views.create_drrmo_account, name='create_drrmo_account'),
    path('accounts/manage/drrmo/<int:pk>/edit/', views.edit_drrmo_account, name='edit_drrmo_account'),
    path('accounts/manage/drrmo/<int:pk>/delete/', views.delete_drrmo_account, name='delete_drrmo_account'),

    # Reservist approval (CDC-scoped)
    path('accounts/manage/pending/', views.pending_reservists, name='pending_reservists'),
    path('accounts/manage/pending/<int:pk>/approve/', views.approve_reservist, name='approve_reservist'),
    path('accounts/manage/pending/<int:pk>/reject/', views.reject_reservist, name='reject_reservist'),
]
