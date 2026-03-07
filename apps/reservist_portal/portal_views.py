"""
Portal view factory — all command/DRRMO portals share the same dashboard pattern.
Each dashboard shows: map, incident list, analytics, and notifications filtered by role & location.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Incident
from .ai_service import get_incident_stats
def get_portal_dashboard(role_name, template_name):
    """Create a dashboard view for a specific role."""

    @login_required
    def dashboard_view(request):
        if request.user.role != role_name and request.user.role != 'RESCOM':
            messages.error(request, 'Access denied.')
            from django.shortcuts import redirect
            return redirect('dashboard')

        # Command dashboards show ALL incidents across all regions
        incidents = Incident.objects.filter(is_deleted=False)

        stats = get_incident_stats(incidents)

        # Get RCDG locations for map markers
        from references.models import Rcdg, Cdc
        rcdg_locations = list(
            Rcdg.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
            .exclude(latitude='').exclude(longitude='')
            .values('id', 'rcdg_desc', 'rcdg_address', 'rcdg_commander', 'latitude', 'longitude')
        )

        # Get CDC locations for map markers
        cdc_locations = list(
            Cdc.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
            .exclude(latitude='').exclude(longitude='')
            .values('id', 'cdc_code', 'cdc_desc', 'cdc_address', 'cdc_director', 'latitude', 'longitude')
        )

        # Get RESCOM user's location for HQ marker (always show RESCOM, not logged-in user)
        from users.models import User
        rescom_user = User.objects.filter(role='RESCOM').first()
        rescom_lat = str(rescom_user.latitude) if rescom_user and rescom_user.latitude else ''
        rescom_lng = str(rescom_user.longitude) if rescom_user and rescom_user.longitude else ''

        # Reservist locations for map markers (scoped by role)
        reservist_qs = User.objects.filter(
            role='RESERVIST',
            is_approved=True,
        ).exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        if role_name == 'RCDG' and getattr(request.user, 'assigned_rcdg_id', None):
            reservist_qs = reservist_qs.filter(assigned_rcdg_id=request.user.assigned_rcdg_id)
        elif role_name == 'CDC' and getattr(request.user, 'assigned_cdc_id', None):
            reservist_qs = reservist_qs.filter(assigned_cdc_id=request.user.assigned_cdc_id)
        elif role_name in ('PDRRMO', 'MDRRMO') and getattr(request.user, 'assigned_cdc_id', None):
            # PDRRMO/MDRRMO see only reservists under the CDC that created their account
            reservist_qs = reservist_qs.filter(assigned_cdc_id=request.user.assigned_cdc_id)
        # RESCOM: show all reservists with location
        reservist_locations = list(
            reservist_qs.values('id', 'full_name', 'latitude', 'longitude', 'rank', 'mobile_number')
        )
        # Serialize Decimal to float for JSON
        import json
        for r in reservist_locations:
            if r.get('latitude') is not None:
                r['latitude'] = str(r['latitude'])
            if r.get('longitude') is not None:
                r['longitude'] = str(r['longitude'])
        reservist_locations_json = json.dumps(reservist_locations)

        return render(request, template_name, {
            'incidents': incidents[:20],
            'stats': stats,
            'role': role_name,
            'rcdg_locations_json': __import__('json').dumps(rcdg_locations),
            'cdc_locations_json': __import__('json').dumps(cdc_locations),
            'reservist_locations_json': reservist_locations_json,
            'rescom_lat': rescom_lat,
            'rescom_lng': rescom_lng,
            'user_lat': str(request.user.ref_latitude) if request.user.ref_latitude else '',
            'user_lng': str(request.user.ref_longitude) if request.user.ref_longitude else '',
        })

    dashboard_view.__name__ = f'{role_name.lower()}_dashboard'
    return dashboard_view
