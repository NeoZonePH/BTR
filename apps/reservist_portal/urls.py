from django.urls import path
from . import views

app_name = 'reservist'

urlpatterns = [
    path('dashboard/', views.reservist_dashboard, name='reservist_dashboard'),
    path('incidents/create/', views.create_incident, name='create_incident'),
    path('incidents/', views.incident_list, name='incident_list'),
    path('incidents/<int:pk>/', views.incident_detail, name='incident_detail'),
    path('incidents/<int:pk>/edit/', views.edit_incident, name='edit_incident'),
    path('incidents/<int:pk>/status/', views.update_incident_status, name='update_incident_status'),
    path('incidents/<int:pk>/delete/', views.soft_delete_incident, name='soft_delete_incident'),
    path('incidents/<int:pk>/restore/', views.restore_incident, name='restore_incident'),
    path('recycle-bin/', views.recycle_bin, name='recycle_bin'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/generate-summary/', views.generate_summary, name='generate_summary'),
    path('analytics/chart-data/', views.chart_data, name='chart_data'),
]
