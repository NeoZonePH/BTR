from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.dashboard_redirect, name='home'),
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/register/', views.register_view, name='register'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/settings/', views.account_settings, name='account_settings'),

    # Notifications
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='notification_read_all'),

    # AJAX — cascading dropdowns
    path('api/rcdg-list/', views.get_rcdg_list, name='api_rcdg_list'),
    path('api/cdc-for-rcdg/', views.get_cdc_for_rcdg, name='api_cdc_for_rcdg'),
]
