from .models import Notification


def notifications_processor(request):
    """Add unread notification count and recent notifications to template context."""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        recent_notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        return {
            'unread_notification_count': unread_count,
            'recent_notifications': recent_notifications,
        }
    return {}
