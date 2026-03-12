from django.shortcuts import render, redirect


def landing_view(request):
    """Public landing page. Redirect authenticated users to their dashboard."""
    if request.user.is_authenticated:
        return redirect(request.user.dashboard_url)
    return render(request, 'landing/landing.html')
