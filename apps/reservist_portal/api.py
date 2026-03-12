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


import math
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .tracking_models import ResponderTracking
from .consumers import INCIDENT_ALERTS_GROUP

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two lat/lng coordinates."""
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_responder_location(request):
    """
    Endpoint for reservists to POST their current GPS location.
    Saves to DB and broadcasts via Django Channels WebSocket.
    """
    incident_id = request.data.get('incident_id')
    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    
    if not all([incident_id, lat, lng]):
        return Response({'success': False, 'error': 'Missing required fields'}, status=400)
    
    try:
        incident = Incident.objects.get(id=incident_id)
        current_lat = float(lat)
        current_lng = float(lng)
        
        # Upsert Tracking record
        tracking, created = ResponderTracking.objects.update_or_create(
            reservist=request.user,
            incident=incident,
            defaults={
                'latitude': current_lat,
                'longitude': current_lng,
                'status': 'responding'
            }
        )
        
        # Check if On Scene (within 50 meters)
        incident_lat = float(incident.latitude)
        incident_lng = float(incident.longitude)
        
        dist_meters = haversine_distance(current_lat, current_lng, incident_lat, incident_lng)
        
        if dist_meters < 50:
            tracking.status = 'on_scene'
            tracking.save()

        # Broadcast update to WebSockets
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'incident_tracking_{incident_id}',
            {
                'type': 'tracking_message',
                'data': {
                    'incident_id': str(incident_id),
                    'reservist_id': str(request.user.id),
                    'reservist_name': request.user.full_name,
                    'latitude': current_lat,
                    'longitude': current_lng,
                    'status': tracking.get_status_display()
                }
            }
        )
        
        return Response({'success': True, 'status': tracking.get_status_display()})
        
    except Incident.DoesNotExist:
        return Response({'success': False, 'error': 'Incident not found'}, status=404)
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_responders_list(request):
    """
    Return all active responders (with current lat/lng) so maps can restore
    responder markers after page refresh. Used by RESCOM, CDC, RCDG, PDRRMO, MDRRMO dashboards.
    """
    qs = ResponderTracking.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
    ).exclude(
        status__in=('available', 'completed')
    ).select_related('reservist', 'incident')

    incident_ids = request.query_params.get('incident_ids')
    if incident_ids:
        ids = [i.strip() for i in incident_ids.split(',') if i.strip()]
        if ids:
            qs = qs.filter(incident_id__in=ids)

    payload = []
    for t in qs:
        payload.append({
            'incident_id': str(t.incident_id),
            'reservist_id': str(t.reservist_id),
            'reservist_name': t.reservist.full_name or 'Responder',
            'latitude': float(t.latitude),
            'longitude': float(t.longitude),
            'status': t.get_status_display(),
        })
    return Response({'responders': payload})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_responder(request):
    """
    Stop responding to an incident. Sets ResponderTracking status to completed and
    broadcasts responder_stopped so all dashboards remove the responder's marker.
    """
    incident_id = request.data.get('incident_id')
    if not incident_id:
        return Response({'success': False, 'error': 'Missing incident_id'}, status=400)
    try:
        incident = Incident.objects.get(id=incident_id)
        tracking = ResponderTracking.objects.filter(
            reservist=request.user,
            incident=incident,
        ).first()
        if tracking:
            tracking.status = 'completed'
            tracking.latitude = None
            tracking.longitude = None
            tracking.save()
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'incident_tracking_{incident_id}',
            {
                'type': 'responder_stopped',
                'reservist_id': str(request.user.id),
            },
        )
        # Broadcast globally so every dashboard map can remove this responder
        # even if an incident-specific tracker socket is temporarily disconnected.
        async_to_sync(channel_layer.group_send)(
            INCIDENT_ALERTS_GROUP,
            {
                'type': 'responder_stopped',
                'reservist_id': str(request.user.id),
                'incident_id': str(incident_id),
            },
        )
        return Response({'success': True})
    except Incident.DoesNotExist:
        return Response({'success': False, 'error': 'Incident not found'}, status=404)
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def incident_description_suggest(request):
    """
    AI suggestions for incident description while typing.
    Body: { "text": "partial description" }
    Returns: { "suggestions": ["s1", "s2", ...] }
    """
    from .ai_service import suggest_incident_description
    text = (request.data.get('text') or '').strip()
    if not text:
        return Response({'suggestions': []})
    suggestions = suggest_incident_description(text)
    return Response({'suggestions': suggestions})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def incident_description_improve(request):
    """
    AI-improved full description (spelling, grammar, clarity).
    Body: { "text": "full description" }
    Returns: { "improved": "...", "unchanged": bool }
    """
    from .ai_service import improve_incident_description
    text = (request.data.get('text') or '').strip()
    if not text:
        return Response({'improved': '', 'unchanged': True})
    improved = improve_incident_description(text)
    return Response({
        'improved': improved,
        'unchanged': (improved or '') == (text or ''),
    })
