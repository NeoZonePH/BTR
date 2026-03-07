from django.urls import path
from apps.reservist_portal.portal_views import get_portal_dashboard
from apps.reservist_portal.views import incident_list, incident_detail, update_incident_status, analytics_dashboard, chart_data, generate_summary

app_name = 'mdrrmo'

dashboard = get_portal_dashboard('MDRRMO', 'mdrrmo_portal/command_dashboard.html')

urlpatterns = [
    path('dashboard/', dashboard, name='mdrrmo_dashboard'),
    path('incidents/', incident_list, name='mdrrmo_incident_list'),
    path('incidents/<int:pk>/', incident_detail, name='mdrrmo_incident_detail'),
    path('incidents/<int:pk>/status/', update_incident_status, name='mdrrmo_update_status'),
    path('analytics/', analytics_dashboard, name='mdrrmo_analytics'),
    path('analytics/chart-data/', chart_data, name='mdrrmo_chart_data'),
    path('analytics/generate-summary/', generate_summary, name='mdrrmo_generate_summary'),
]
