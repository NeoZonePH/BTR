from .models import AppBranding


def app_branding(request):
    """Provide app_name_code and app_name_desc to all templates."""
    branding = AppBranding.get()
    return {
        'app_name_code': branding.name_code,
        'app_name_desc': branding.name_desc,
    }
