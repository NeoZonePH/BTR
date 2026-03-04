"""Notification service for TARGET system."""

from users.models import User, Notification
from .sms import send_sms


NOTIFY_ROLES = [
    User.Role.RESCOM,
    User.Role.RCDG,
    User.Role.CDC,
    User.Role.PDRRMO,
    User.Role.MDRRMO,
]


def notify_on_incident(incident):
    """
    Notify relevant users when an incident is created.
    Matches by region, province, and municipality.
    """
    # Find users with matching location and relevant roles
    filters = {'role__in': NOTIFY_ROLES}

    # Build location filter — match at the broadest available level
    if incident.region:
        filters['region'] = incident.region
    if incident.province:
        filters['province'] = incident.province
    if incident.municipality:
        filters['municipality'] = incident.municipality

    users_to_notify = User.objects.filter(**filters)

    # If no exact matches, notify all users with relevant roles
    if not users_to_notify.exists():
        users_to_notify = User.objects.filter(role__in=NOTIFY_ROLES)

    message = (
        f"🚨 NEW INCIDENT: {incident.title}\n"
        f"Type: {incident.get_incident_type_display()}\n"
        f"Location: {incident.municipality}, {incident.province}, {incident.region}\n"
        f"Reported by: {incident.reservist.full_name}\n"
        f"Date: {incident.created_at.strftime('%b %d, %Y %I:%M %p') if incident.created_at else 'Just now'}"
    )

    notifications = []
    for user in users_to_notify:
        notifications.append(
            Notification(
                user=user,
                incident=incident,
                message=message,
            )
        )
        # Send SMS
        if user.mobile_number:
            send_sms(user.mobile_number, message)

    Notification.objects.bulk_create(notifications)
    return len(notifications)
