"""
Context processors for the CDC portal.
Exposes reservist approval notification data for CDC users,
and mustering notification count for reservists.
"""
from users.models import User

from .models import MusterNotification


def reservist_approval_notification(request):
    """
    Add pending reservist approval count and list for CDC users.
    Used in base template to show a badge on "Reservist Approvals" and optional dropdown.
    """
    if not request.user.is_authenticated:
        return {'pending_reservist_approval_count': 0, 'pending_reservist_approvals': []}
    if request.user.role != 'CDC':
        return {'pending_reservist_approval_count': 0, 'pending_reservist_approvals': []}

    # Only CDC users have assigned_cdc; scope pending reservists to this CDC
    assigned_cdc = getattr(request.user, 'assigned_cdc', None)
    if not assigned_cdc:
        return {
            'pending_reservist_approval_count': 0,
            'pending_reservist_approvals': [],
        }

    pending_qs = User.objects.filter(
        role='RESERVIST',
        is_approved=False,
        assigned_cdc=assigned_cdc,
    ).order_by('date_joined')

    return {
        'pending_reservist_approval_count': pending_qs.count(),
        'pending_reservist_approvals': list(pending_qs[:10]),
    }


def muster_notification_for_reservist(request):
    """
    For reservists: count of unread muster notifications (when CDC created a mustering).
    Used in base template for topbar notification icon and sidebar Mustering badge.
    """
    if not request.user.is_authenticated:
        return {'muster_notification_count': 0}
    if request.user.role != 'RESERVIST':
        return {'muster_notification_count': 0}
    count = MusterNotification.objects.filter(
        reservist=request.user,
        read_at__isnull=True,
    ).count()
    return {'muster_notification_count': count}
