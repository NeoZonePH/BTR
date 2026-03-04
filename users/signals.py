from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import ActivityLog

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    if user.role == 'RESERVIST':
        ActivityLog.objects.create(
            user=user,
            action=ActivityLog.Action.LOGIN,
            details='User logged in.'
        )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user and user.role == 'RESERVIST':
        ActivityLog.objects.create(
            user=user,
            action=ActivityLog.Action.LOGOUT,
            details='User logged out.'
        )
