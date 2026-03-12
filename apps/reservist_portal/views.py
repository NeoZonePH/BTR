from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Incident, AISummary
from .forms import IncidentForm
from .notifications import notify_on_incident
from .ai_service import get_incident_stats, generate_ai_summary, _serialize_stats
from .consumers import INCIDENT_ALERTS_GROUP
from users.models import ActivityLog
from apps.cdc_portal.models import Muster, MusterEnrollment, MusterNotification


def role_required(role):
    """Decorator to enforce role-based access. RESCOM has admin-level access to all portals."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.role != role and request.user.role != 'RESCOM':
                messages.error(request, 'Access denied. Insufficient permissions.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return login_required(wrapper)
    return decorator


@role_required('RESERVIST')
def reservist_dashboard(request):
    """Reservist dashboard with their incidents, map with reservist + RCDG/CDC markers."""
    import json
    from references.models import Rcdg, Cdc
    incidents = Incident.objects.filter(reservist=request.user, is_deleted=False)
    
    stats = get_incident_stats(incidents)

    # Reservist's own location for map marker
    reservist_lat = ''
    reservist_lng = ''
    if request.user.latitude is not None and request.user.longitude is not None:
        reservist_lat = str(request.user.latitude)
        reservist_lng = str(request.user.longitude)

    # Single RCDG and CDC for this reservist (for map markers)
    rcdg_locations = []
    cdc_locations = []
    if getattr(request.user, 'assigned_rcdg_id', None):
        rcdg = Rcdg.objects.filter(pk=request.user.assigned_rcdg_id).first()
        if rcdg and rcdg.latitude and rcdg.longitude:
            rcdg_locations = [{
                'id': rcdg.id,
                'rcdg_desc': rcdg.rcdg_desc or '',
                'rcdg_address': rcdg.rcdg_address or '',
                'rcdg_commander': rcdg.rcdg_commander or '',
                'latitude': rcdg.latitude,
                'longitude': rcdg.longitude,
            }]
    if getattr(request.user, 'assigned_cdc_id', None):
        cdc = Cdc.objects.filter(pk=request.user.assigned_cdc_id).first()
        if cdc and cdc.latitude and cdc.longitude:
            cdc_locations = [{
                'id': cdc.id,
                'cdc_code': cdc.cdc_code or '',
                'cdc_desc': cdc.cdc_desc or '',
                'cdc_address': cdc.cdc_address or '',
                'cdc_director': cdc.cdc_director or '',
                'latitude': cdc.latitude,
                'longitude': cdc.longitude,
            }]

    return render(request, 'reservist_portal/reservist_dashboard.html', {
        'incidents': incidents[:10],
        'stats': stats,
        'reservist_lat': reservist_lat,
        'reservist_lng': reservist_lng,
        'rcdg_locations_json': json.dumps(rcdg_locations),
        'cdc_locations_json': json.dumps(cdc_locations),
    })


@role_required('RESERVIST')
def create_incident(request):
    """Create a new incident report."""
    form = IncidentForm()
    if request.method == 'POST':
        form = IncidentForm(request.POST, request.FILES)
        if form.is_valid():
            incident = form.save(commit=False)
            incident.reservist = request.user
            incident.save()
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.Action.CREATE_INCIDENT,
                details=f"Submitted incident: {incident.title} ({incident.get_incident_type_display()})"
            )
            # Broadcast to all dashboards so other accounts hear alarm without refresh
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    INCIDENT_ALERTS_GROUP,
                    {
                        'type': 'new_incident_alert',
                        'incident_id': incident.pk,
                        'title': incident.title,
                        'incident_type': incident.incident_type,
                        'reservist_id': incident.reservist_id,
                    }
                )
            # Notify relevant personnel
            count = notify_on_incident(incident)
            messages.success(
                request,
                f'Incident reported successfully! {count} personnel notified.',
            )
            return redirect('reservist:reservist_dashboard')
    return render(request, 'reservist_portal/create_incident.html', {'form': form})


@role_required('RESERVIST')
def edit_incident(request, pk):
    """Edit an existing incident report."""
    incident = get_object_or_404(Incident, pk=pk, reservist=request.user, is_deleted=False)
    
    if request.method == 'POST':
        form = IncidentForm(request.POST, request.FILES, instance=incident)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.Action.EDIT_INCIDENT,
                details=f"Edited incident: {incident.title} ({incident.get_incident_type_display()})"
            )
            messages.success(request, 'Incident report updated successfully!')
            return redirect('reservist:incident_list')
    else:
        form = IncidentForm(instance=incident)

    return render(request, 'reservist_portal/edit_incident.html', {
        'form': form,
        'incident': incident,
    })


@login_required
def incident_detail(request, pk):
    """View incident details."""
    incident = get_object_or_404(Incident, pk=pk)
    status_choices = [
        {
            'value': choice[0],
            'label': choice[1],
            'selected': 'selected' if incident.status == choice[0] else '',
        }
        for choice in Incident.Status.choices
    ]
    return render(request, 'reservist_portal/incident_detail.html', {
        'incident': incident,
        'status_choices': status_choices,
    })


@login_required
def incident_list(request):
    """List all incidents (filtered by role access)."""
    if request.user.role == 'RESERVIST':
        incidents = Incident.objects.filter(reservist=request.user, is_deleted=False)
    else:
        incidents = Incident.objects.filter(is_deleted=False)

    # Apply filters
    incident_type = request.GET.get('type')
    status = request.GET.get('status')
    region = request.GET.get('region')

    if incident_type:
        incidents = incidents.filter(incident_type=incident_type)
    if status:
        incidents = incidents.filter(status=status)
    if region:
        incidents = incidents.filter(region__icontains=region)

    incident_types = [
        {'value': c[0], 'label': c[1], 'selected': 'selected' if incident_type == c[0] else ''}
        for c in Incident.IncidentType.choices
    ]
    statuses = [
        {'value': c[0], 'label': c[1], 'selected': 'selected' if status == c[0] else ''}
        for c in Incident.Status.choices
    ]

    return render(request, 'reservist_portal/incident_list.html', {
        'incidents': incidents,
        'incident_types': incident_types,
        'statuses': statuses,
    })


@login_required
def update_incident_status(request, pk):
    """Update incident status (for command/admin roles)."""
    if request.user.role in ('RESERVIST',):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    incident = get_object_or_404(Incident, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Incident.Status.choices):
            incident.status = new_status
            incident.save()
            messages.success(request, f'Incident status updated to {incident.get_status_display()}.')

    # Redirect back to the incident detail page.
    # The status URL is always at /<portal>/incidents/<pk>/status/
    # so the detail page is the parent: /<portal>/incidents/<pk>/
    detail_url = request.path.replace('/status/', '/')
    return redirect(detail_url)


@login_required
def analytics_dashboard(request):
    """AI analytics dashboard with charts."""
    all_incidents = Incident.objects.filter(is_deleted=False)
    now = timezone.now()

    stats = get_incident_stats(all_incidents)

    # Get AI summaries
    latest_summaries = AISummary.objects.all()[:4]

    return render(request, 'reservist_portal/analytics_dashboard.html', {
        'stats': stats,
        'latest_summaries': latest_summaries,
    })


@login_required
def generate_summary(request):
    """Generate AI summary on demand."""
    period = request.GET.get('period', 'daily')
    now = timezone.now()
    all_incidents = Incident.objects.filter(is_deleted=False)

    period_map = {
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(days=30),
        'yearly': timedelta(days=365),
    }

    delta = period_map.get(period, timedelta(days=1))
    start_date = now - delta
    filtered = all_incidents.filter(created_at__gte=start_date)
    stats = get_incident_stats(filtered)
    summary_text = generate_ai_summary(stats, period)

    # Store in DB
    summary = AISummary.objects.create(
        period=period,
        period_start=start_date.date(),
        period_end=now.date(),
        summary_text=summary_text,
        raw_data=_serialize_stats(stats),
    )

    return JsonResponse({
        'summary': summary_text,
        'period': period,
        'total_incidents': stats.get('total', 0),
    })


@login_required
def chart_data(request):
    """Return chart data as JSON for AJAX."""
    all_incidents = Incident.objects.filter(is_deleted=False)
    now = timezone.now()

    # Filter by time range
    range_filter = request.GET.get('range', 'month')
    range_map = {
        'day': timedelta(days=1),
        'week': timedelta(weeks=1),
        'month': timedelta(days=30),
        'year': timedelta(days=365),
    }
    delta = range_map.get(range_filter, timedelta(days=30))
    filtered = all_incidents.filter(created_at__gte=now - delta)

    stats = get_incident_stats(filtered)

    # Process for Chart.js format
    type_labels = [t[1] for t in Incident.IncidentType.choices]
    type_data = [stats['by_type'].get(t[0], 0) for t in Incident.IncidentType.choices]

    status_labels = [s[1] for s in Incident.Status.choices]
    status_data = [stats['by_status'].get(s[0], 0) for s in Incident.Status.choices]

    daily_labels = [d['day'].strftime('%b %d') for d in stats.get('daily', []) if d.get('day')]
    daily_data = [d['count'] for d in stats.get('daily', [])]

    region_labels = list(stats.get('by_region', {}).keys())
    region_data = list(stats.get('by_region', {}).values())

    return JsonResponse({
        'type': {'labels': type_labels, 'data': type_data},
        'status': {'labels': status_labels, 'data': status_data},
        'daily': {'labels': daily_labels, 'data': daily_data},
        'region': {'labels': region_labels, 'data': region_data},
        'total': stats.get('total', 0),
    })


@login_required
def recycle_bin(request):
    """View soft-deleted incidents."""
    if request.user.role == 'RESERVIST':
        incidents = Incident.objects.filter(reservist=request.user, is_deleted=True)
    else:
        incidents = Incident.objects.filter(is_deleted=True)
    return render(request, 'reservist_portal/recycle_bin.html', {'incidents': incidents})


@role_required('RESERVIST')
def soft_delete_incident(request, pk):
    """Soft delete an incident."""
    incident = get_object_or_404(Incident, pk=pk, reservist=request.user)
    if request.method == 'POST':
        incident.is_deleted = True
        incident.save()
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.Action.DELETE_INCIDENT,
            details=f"Deleted incident: {incident.title} ({incident.get_incident_type_display()})"
        )
        messages.success(request, 'Incident moved to recycle bin.')
    return redirect('reservist:incident_list')


@login_required
def restore_incident(request, pk):
    """Restore a soft-deleted incident."""
    if request.user.role == 'RESERVIST':
        incident = get_object_or_404(Incident, pk=pk, reservist=request.user)
    else:
        incident = get_object_or_404(Incident, pk=pk)
        
    if request.method == 'POST':
        incident.is_deleted = False
        incident.save()
        if request.user.role == 'RESERVIST':
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.Action.RESTORE_INCIDENT,
                details=f"Restored incident: {incident.title} ({incident.get_incident_type_display()})"
            )
        messages.success(request, 'Incident restored successfully.')
    return redirect('reservist:recycle_bin')


# --- Mustering (incoming schedules; mark present on day of muster) ---


@role_required('RESERVIST')
def mustering_list(request):
    """Reservist: list incoming mustering schedules (muster_date >= today)."""
    from django.utils import timezone
    today = timezone.localdate()
    # Mark all muster notifications as read when reservist visits this page
    MusterNotification.objects.filter(
        reservist=request.user,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    enrollments = (
        MusterEnrollment.objects
        .filter(reservist=request.user)
        .select_related('muster')
        .filter(muster__muster_date__gte=today)
        .order_by('muster__muster_date', 'muster__title')
    )
    return render(request, 'reservist_portal/mustering/mustering_list.html', {
        'enrollments': enrollments,
        'today': today,
    })


@role_required('RESERVIST')
def muster_mark_present(request, enrollment_id):
    """Reservist: mark self as present for a muster (only on muster date); submit lat/lng."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    enrollment = get_object_or_404(
        MusterEnrollment,
        pk=enrollment_id,
        reservist=request.user,
    )
    today = timezone.localdate()
    if enrollment.muster.muster_date != today:
        return JsonResponse({
            'success': False,
            'error': 'You can only mark present on the day of the muster.',
        }, status=400)

    import json
    if request.content_type == 'application/json' and request.body:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST
    else:
        data = request.POST

    lat = data.get('latitude') or data.get('lat')
    lng = data.get('longitude') or data.get('lng')
    if lat is None or lng is None:
        return JsonResponse({'success': False, 'error': 'Latitude and longitude required.'}, status=400)

    try:
        from decimal import Decimal
        lat = Decimal(str(lat))
        lng = Decimal(str(lng))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid latitude or longitude.'}, status=400)

    enrollment.status = MusterEnrollment.EnrollmentStatus.PRESENT
    enrollment.latitude = lat
    enrollment.longitude = lng
    enrollment.save()

    return JsonResponse({'success': True, 'message': 'Marked as present.'})
