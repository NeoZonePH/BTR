from django.db.utils import OperationalError, ProgrammingError

# Default branding when table doesn't exist or no record (TARGET)
DEFAULT_NAME_CODE = 'TARGET'
DEFAULT_NAME_DESC = 'TARGET — Emergency Tracker'


def app_branding(request):
    """Provide app_name_code and app_name_desc to all templates. TARGET is default; RESCOM can override in settings."""
    try:
        from .models import AppBranding
        branding = AppBranding.get()
        return {
            'app_name_code': branding.name_code or DEFAULT_NAME_CODE,
            'app_name_desc': branding.name_desc or DEFAULT_NAME_DESC,
        }
    except (OperationalError, ProgrammingError):
        return {
            'app_name_code': DEFAULT_NAME_CODE,
            'app_name_desc': DEFAULT_NAME_DESC,
        }
