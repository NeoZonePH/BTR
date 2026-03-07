"""
Middleware to ensure the application always uses Asia/Manila (Philippines) local time.
"""
from django.utils import timezone as dj_timezone
from django.utils.timezone import get_default_timezone


class ManilaTimezoneMiddleware:
    """
    Activate the default app timezone (Asia/Manila) on every request so that:
    - timezone.localtime() and timezone.localdate() use Philippines time
    - Template |date and |time filters render in Philippines time
    - API and views see consistent local time (Philippines)
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._tz = get_default_timezone()

    def __call__(self, request):
        dj_timezone.activate(self._tz)
        return self.get_response(request)
