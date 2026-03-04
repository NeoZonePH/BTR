from django.urls import path
from reservist_portal.portal_views import get_portal_dashboard
from reservist_portal.views import incident_list, incident_detail, update_incident_status, analytics_dashboard, chart_data, generate_summary
from . import views

app_name = 'rescom'

dashboard = get_portal_dashboard('RESCOM', 'rescom_portal/command_dashboard.html')

urlpatterns = [
    path('dashboard/', dashboard, name='rescom_dashboard'),
    path('incidents/', incident_list, name='rescom_incident_list'),
    path('incidents/<int:pk>/', incident_detail, name='rescom_incident_detail'),
    path('incidents/<int:pk>/status/', update_incident_status, name='rescom_update_status'),
    path('incidents/<int:pk>/hard-delete/', views.hard_delete_incident, name='hard_delete_incident'),
    path('analytics/', analytics_dashboard, name='rescom_analytics'),
    path('analytics/chart-data/', chart_data, name='rescom_chart_data'),
    path('analytics/generate-summary/', generate_summary, name='rescom_generate_summary'),

    # Reservist Activity Logs
    path('logs/', views.reservist_activity_logs, name='reservist_activity_logs'),

    # Database Backup/Restore
    path('database/', views.database_management, name='database_management'),
    
    # Server Storage
    path('storage/', views.server_storage_status, name='server_storage'),

    # Account management — RCDG
    path('accounts/manage/rcdg/', views.manage_rcdg_accounts, name='manage_rcdg_accounts'),
    path('accounts/manage/rcdg/create/', views.create_rcdg_account, name='create_rcdg_account'),
    path('accounts/manage/rcdg/<int:pk>/edit/', views.edit_rcdg_account, name='edit_rcdg_account'),
    path('accounts/manage/rcdg/<int:pk>/delete/', views.delete_rcdg_account, name='delete_rcdg_account'),

    # Account management — CDC (RESCOM scope)
    path('accounts/manage/cdc/', views.manage_cdc_accounts, name='manage_cdc_accounts'),
    path('accounts/manage/cdc/create/', views.create_cdc_account, name='create_cdc_account'),
    path('accounts/manage/cdc/<int:pk>/delete/', views.delete_cdc_account, name='delete_cdc_account'),

    # Account management — DRRMO (RESCOM scope)
    path('accounts/manage/drrmo/', views.manage_drrmo_accounts, name='manage_drrmo_accounts'),
    path('accounts/manage/drrmo/create/', views.create_drrmo_account, name='create_drrmo_account'),
    path('accounts/manage/drrmo/<int:pk>/delete/', views.delete_drrmo_account, name='delete_drrmo_account'),

    # Reservist approval (RESCOM scope)
    path('accounts/manage/pending/', views.pending_reservists, name='pending_reservists'),
    path('accounts/manage/pending/<int:pk>/approve/', views.approve_reservist, name='approve_reservist'),
    path('accounts/manage/pending/<int:pk>/reject/', views.reject_reservist, name='reject_reservist'),

    # Organization reference CRUD — RCDG / CDC
    path('org/rcdg/', views.rcdg_list, name='ref_rcdg_list'),
    path('org/rcdg/create/', views.rcdg_create, name='ref_rcdg_create'),
    path('org/rcdg/<int:pk>/edit/', views.rcdg_edit, name='ref_rcdg_edit'),
    path('org/rcdg/<int:pk>/delete/', views.rcdg_delete, name='ref_rcdg_delete'),
    path('org/cdc/', views.cdc_list, name='ref_cdc_list'),
    path('org/cdc/create/', views.cdc_create, name='ref_cdc_create'),
    path('org/cdc/<int:pk>/edit/', views.cdc_edit, name='ref_cdc_edit'),
    path('org/cdc/<int:pk>/delete/', views.cdc_delete, name='ref_cdc_delete'),
]
