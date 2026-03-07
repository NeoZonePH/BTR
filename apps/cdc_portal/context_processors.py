"""
Context processors for the CDC portal.
Exposes reservist approval notification data for CDC users in templates.
"""
from users.models import User


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
