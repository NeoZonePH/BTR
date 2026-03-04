from django.urls import path
from reservist_portal.portal_views import get_portal_dashboard
from reservist_portal.views import incident_list, incident_detail, update_incident_status, analytics_dashboard, chart_data, generate_summary

app_name = 'pdrrmo'

dashboard = get_portal_dashboard('PDRRMO', 'pdrrmo_portal/command_dashboard.html')

urlpatterns = [
    path('dashboard/', dashboard, name='pdrrmo_dashboard'),
    path('incidents/', incident_list, name='pdrrmo_incident_list'),
    path('incidents/<int:pk>/', incident_detail, name='pdrrmo_incident_detail'),
    path('incidents/<int:pk>/status/', update_incident_status, name='pdrrmo_update_status'),
    path('analytics/', analytics_dashboard, name='pdrrmo_analytics'),
    path('analytics/chart-data/', chart_data, name='pdrrmo_chart_data'),
    path('analytics/generate-summary/', generate_summary, name='pdrrmo_generate_summary'),
]
