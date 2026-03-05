"""GeoJSON API for incidents — used by MapLibre map."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, time, timedelta

from .models import Incident


def _start_of_today():
    """Start of current day (midnight) in the active timezone."""
    local_date = timezone.localdate()
    return timezone.make_aware(datetime.combine(local_date, time.min))


def _start_of_week():
    """Start of current week (Monday 00:00) in the active timezone."""
    local_date = timezone.localdate()
    monday = local_date - timedelta(days=local_date.weekday())
    return timezone.make_aware(datetime.combine(monday, time.min))


def _start_of_month():
    """Start of current month in the active timezone."""
    local_date = timezone.localdate()
    first = local_date.replace(day=1)
    return timezone.make_aware(datetime.combine(first, time.min))


def _start_of_year():
    """Start of current year in the active timezone."""
    local_date = timezone.localdate()
    first = local_date.replace(month=1, day=1)
    return timezone.make_aware(datetime.combine(first, time.min))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def incidents_geojson(request):
    """Return incidents in GeoJSON format for map rendering."""
    incidents = Incident.objects.select_related('reservist').filter(is_deleted=False)

    # Time filters: use start of period so "Today" = only today's incidents, not last 24h
    time_filter = request.query_params.get('time')
    if time_filter:
        period_starts = {
            'day': _start_of_today,
            'week': _start_of_week,
            'month': _start_of_month,
            'year': _start_of_year,
        }
        if time_filter in period_starts:
            start = period_starts[time_filter]()
            incidents = incidents.filter(created_at__gte=start)

    # Location filters
    region = request.query_params.get('region')
    province = request.query_params.get('province')
    municipality = request.query_params.get('municipality')
    incident_type = request.query_params.get('type')
    status = request.query_params.get('status')

    if region:
        incidents = incidents.filter(region__icontains=region)
    if province:
        incidents = incidents.filter(province__icontains=province)
    if municipality:
        incidents = incidents.filter(municipality__icontains=municipality)
    if incident_type:
        incidents = incidents.filter(incident_type=incident_type)
    if status:
        incidents = incidents.filter(status=status)

    role_prefix = request.user.role.lower() if request.user.is_authenticated and hasattr(request.user, 'role') else 'reservist'

    features = []
    for inc in incidents.select_related('reservist'):
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(inc.longitude), float(inc.latitude)],
            },
            'properties': {
                'id': inc.id,
                'title': inc.title,
                'description': inc.description,
                'incident_type': inc.incident_type,
                'incident_type_display': inc.get_incident_type_display(),
                'status': inc.status,
                'status_display': inc.get_status_display(),
                'region': inc.region,
                'province': inc.province,
                'municipality': inc.municipality,
                'latitude': str(inc.latitude),
                'longitude': str(inc.longitude),
                'marker_color': inc.marker_color,
                'reporter': inc.reservist.full_name,
                'created_at': timezone.localtime(inc.created_at).strftime('%b %d, %Y %I:%M %p'),
                'detail_url': f'/{role_prefix}/incidents/{inc.id}/',
            },
        })

    return Response({
        'type': 'FeatureCollection',
        'features': features,
    })
