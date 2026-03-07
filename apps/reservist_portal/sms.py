"""
Pluggable SMS service for TARGET system.
Configure SMS_PROVIDER in settings / .env.
Supports: 'console' (dev logging), extensible for production providers.
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(mobile_number, message):
    """
    Send an SMS message using the configured provider.

    Args:
        mobile_number: Recipient phone number
        message: SMS text content
    """
    provider = getattr(settings, 'SMS_PROVIDER', 'console')

    if provider == 'console':
        _send_console(mobile_number, message)
    else:
        logger.warning(f"Unknown SMS provider '{provider}'. Message not sent.")


def _send_console(mobile_number, message):
    """Development: log SMS messages to console."""
    logger.info(
        f"\n{'='*50}\n"
        f"📱 SMS TO: {mobile_number}\n"
        f"{'='*50}\n"
        f"{message}\n"
        f"{'='*50}"
    )


# ─── Add production providers below ───

def _send_semaphore(mobile_number, message):
    """
    Semaphore SMS (Philippines).
    Uncomment and configure when ready for production.

    import requests
    api_key = settings.SMS_API_KEY
    params = {
        'apikey': api_key,
        'number': mobile_number,
        'message': message,
        'sendername': 'TARGET',
    }
    response = requests.post('https://api.semaphore.co/api/v4/messages', params=params)
    return response.json()
    """
    pass


def _send_twilio(mobile_number, message):
    """
    Twilio SMS.
    Uncomment and configure when ready for production.

    from twilio.rest import Client
    client = Client(settings.SMS_API_KEY, settings.SMS_API_SECRET)
    message = client.messages.create(
        body=message,
        from_=settings.SMS_FROM_NUMBER,
        to=mobile_number,
    )
    return message.sid
    """
    pass
