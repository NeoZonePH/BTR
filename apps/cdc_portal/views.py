"""
CDC portal views: DRRMO account management, reservist approval, and mustering (CDC-scoped).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from users.models import User
from users.forms import AccountCreateForm, AccountEditForm
from .models import Muster, MusterEnrollment, MusterNotification
from .forms import MusterForm, MusterEnrollmentStatusForm


def _require_cdc(request):
    if request.user.role != 'CDC':
        messages.error(request, 'Access denied.')
        return False
    return True


@login_required
def manage_drrmo_accounts(request):
    """CDC: list and create PDRRMO/MDRRMO accounts under this CDC."""
    if not _require_cdc(request):
        return redirect('dashboard')

    drrmo_users = User.objects.filter(
        role__in=['PDRRMO', 'MDRRMO'], assigned_cdc=request.user.assigned_cdc,
    ).order_by('role', 'full_name')

    return render(request, 'cdc_portal/accounts/manage_accounts.html', {
        'accounts': drrmo_users,
        'account_type': 'DRRMO',
        'account_type_full': 'PDRRMO / MDRRMO',
        'create_url_name': 'cdc:create_drrmo_account',
        'edit_url_name': 'cdc:edit_drrmo_account',
        'delete_url_name': 'cdc:delete_drrmo_account',
        'show_role_picker': True,
    })


@login_required
def create_drrmo_account(request):
    """CDC: create a new PDRRMO or MDRRMO account under this CDC."""
    if not _require_cdc(request):
        return redirect('dashboard')

    form = AccountCreateForm()
    role_choice = request.GET.get('role', 'PDRRMO')
    if role_choice not in ('PDRRMO', 'MDRRMO'):
        role_choice = 'PDRRMO'

    if request.method == 'POST':
        form = AccountCreateForm(request.POST)
        role_choice = request.POST.get('drrmo_role', 'PDRRMO')
        if role_choice not in ('PDRRMO', 'MDRRMO'):
            role_choice = 'PDRRMO'
        if form.is_valid():
            user = form.save(commit=False)
            user.role = role_choice
            user.is_approved = True
            user.assigned_cdc = request.user.assigned_cdc
            user.assigned_rcdg = request.user.assigned_rcdg
            user.save()
            messages.success(request, f'{role_choice} account "{user.full_name}" created successfully.')
            return redirect('cdc:manage_drrmo_accounts')

    return render(request, 'cdc_portal/accounts/create_account.html', {
        'form': form,
        'account_type': role_choice,
        'account_type_full': 'Provincial DRRMO' if role_choice == 'PDRRMO' else 'Municipal DRRMO',
        'back_url_name': 'cdc:manage_drrmo_accounts',
        'show_role_picker': True,
        'current_role': role_choice,
    })


@login_required
def delete_drrmo_account(request, pk):
    """CDC: delete a PDRRMO/MDRRMO account under this CDC."""
    if not _require_cdc(request):
        return redirect('dashboard')

    user = get_object_or_404(
        User, pk=pk, role__in=['PDRRMO', 'MDRRMO'], assigned_cdc=request.user.assigned_cdc
    )
    if request.method == 'POST':
        name = user.full_name
        user.delete()
        messages.success(request, f'DRRMO account "{name}" deleted.')
    return redirect('cdc:manage_drrmo_accounts')


@login_required
def edit_drrmo_account(request, pk):
    """CDC: edit a PDRRMO/MDRRMO account under this CDC."""
    if not _require_cdc(request):
        return redirect('dashboard')

    user = get_object_or_404(
        User, pk=pk, role__in=['PDRRMO', 'MDRRMO'], assigned_cdc=request.user.assigned_cdc
    )
    form = AccountEditForm(instance=user)
    if request.method == 'POST':
        form = AccountEditForm(request.POST, instance=user)
        role_choice = request.POST.get('drrmo_role', user.role)
        if role_choice not in ('PDRRMO', 'MDRRMO'):
            role_choice = user.role
        if form.is_valid():
            user = form.save(commit=False)
            user.role = role_choice
            user.assigned_cdc = request.user.assigned_cdc
            user.assigned_rcdg = request.user.assigned_rcdg
            user.save()
            messages.success(request, f'DRRMO account "{user.full_name}" updated successfully.')
            return redirect('cdc:manage_drrmo_accounts')

    return render(request, 'cdc_portal/accounts/edit_account.html', {
        'form': form,
        'account': user,
        'account_type': 'DRRMO',
        'account_type_full': user.get_role_display(),
        'back_url_name': 'cdc:manage_drrmo_accounts',
        'show_role_picker': True,
        'current_role': user.role,
    })


@login_required
def pending_reservists(request):
    """CDC: list pending reservist sign-ups for this CDC."""
    if not _require_cdc(request):
        return redirect('dashboard')

    pending = User.objects.filter(
        role='RESERVIST', is_approved=False, assigned_cdc=request.user.assigned_cdc,
    ).order_by('-date_joined')

    return render(request, 'cdc_portal/accounts/pending_reservists.html', {
        'pending_users': pending,
        'approve_url_name': 'cdc:approve_reservist',
        'reject_url_name': 'cdc:reject_reservist',
    })


@login_required
def approve_reservist(request, pk):
    """CDC: approve a reservist account."""
    if not _require_cdc(request):
        return redirect('dashboard')

    user = get_object_or_404(
        User, pk=pk, role='RESERVIST', is_approved=False, assigned_cdc=request.user.assigned_cdc,
    )

    if request.method == 'POST':
        user.is_approved = True
        user.save()
        messages.success(request, f'Reservist "{user.full_name}" approved successfully.')
    return redirect('cdc:pending_reservists')


@login_required
def reject_reservist(request, pk):
    """CDC: reject and delete a reservist sign-up."""
    if not _require_cdc(request):
        return redirect('dashboard')

    user = get_object_or_404(
        User, pk=pk, role='RESERVIST', is_approved=False, assigned_cdc=request.user.assigned_cdc,
    )

    if request.method == 'POST':
        name = user.full_name
        user.delete()
        messages.success(request, f'Reservist "{name}" registration rejected.')
    return redirect('cdc:pending_reservists')


# --- Mustering (CRUD, auto-enroll reservists under this CDC) ---


def _enroll_reservists_for_muster(muster):
    """Create MusterEnrollment for every approved reservist under the muster's CDC."""
    reservists = User.objects.filter(
        role='RESERVIST',
        is_approved=True,
        assigned_cdc=muster.cdc,
    )
    created = 0
    for r in reservists:
        _, created_this = MusterEnrollment.objects.get_or_create(
            muster=muster,
            reservist=r,
            defaults={'status': MusterEnrollment.EnrollmentStatus.ENROLLED},
        )
        if created_this:
            created += 1
    return created


@login_required
def muster_list(request):
    """CDC: list all musters for this CDC."""
    if not _require_cdc(request):
        return redirect('dashboard')

    cdc = request.user.assigned_cdc
    if not cdc:
        messages.warning(request, 'Your account is not assigned to a CDC. Mustering is unavailable.')
        return redirect('cdc:cdc_dashboard')

    musters = Muster.objects.filter(cdc=cdc).select_related('created_by').prefetch_related('enrollments')
    return render(request, 'cdc_portal/mustering/muster_list.html', {
        'musters': musters,
    })


@login_required
def muster_create(request):
    """CDC: create a muster and auto-enroll all approved reservists under this CDC."""
    if not _require_cdc(request):
        return redirect('dashboard')

    cdc = request.user.assigned_cdc
    if not cdc:
        messages.warning(request, 'Your account is not assigned to a CDC. Mustering is unavailable.')
        return redirect('cdc:cdc_dashboard')

    form = MusterForm()
    if request.method == 'POST':
        form = MusterForm(request.POST)
        if form.is_valid():
            muster = form.save(commit=False)
            muster.cdc = cdc
            muster.created_by = request.user
            muster.save()
            enrolled = _enroll_reservists_for_muster(muster)
            # Notify each enrolled reservist about the new muster
            for enr in muster.enrollments.select_related('reservist').all():
                MusterNotification.objects.get_or_create(
                    reservist=enr.reservist,
                    muster=muster,
                    defaults={'read_at': None},
                )
            messages.success(
                request,
                f'Muster "{muster.title}" created. {enrolled} reservist(s) automatically enrolled.',
            )
            return redirect('cdc:muster_detail', pk=muster.pk)

    return render(request, 'cdc_portal/mustering/muster_form.html', {
        'form': form,
        'title': 'Create Muster',
        'submit_label': 'Create & Enroll Reservists',
    })


@login_required
def muster_edit(request, pk):
    """CDC: edit a muster (enrollments are not re-created; use detail to manage)."""
    if not _require_cdc(request):
        return redirect('dashboard')

    cdc = request.user.assigned_cdc
    if not cdc:
        return redirect('cdc:cdc_dashboard')

    muster = get_object_or_404(Muster, pk=pk, cdc=cdc)
    form = MusterForm(instance=muster)
    if request.method == 'POST':
        form = MusterForm(request.POST, instance=muster)
        if form.is_valid():
            form.save()
            messages.success(request, f'Muster "{muster.title}" updated.')
            return redirect('cdc:muster_detail', pk=muster.pk)

    return render(request, 'cdc_portal/mustering/muster_form.html', {
        'form': form,
        'muster': muster,
        'title': 'Edit Muster',
        'submit_label': 'Save',
    })


@login_required
def muster_detail(request, pk):
    """CDC: view muster and enrolled reservists; optionally update enrollment status."""
    if not _require_cdc(request):
        return redirect('dashboard')

    cdc = request.user.assigned_cdc
    if not cdc:
        return redirect('cdc:cdc_dashboard')

    muster = get_object_or_404(Muster.objects.select_related('cdc', 'cdc__rcdg'), pk=pk, cdc=cdc)
    # Only show reservists who are members of this CDC (assigned_cdc = this muster's CDC)
    enrollments = (
        muster.enrollments
        .filter(reservist__assigned_cdc=cdc)
        .select_related('reservist')
        .order_by('reservist__full_name')
    )

    # Optional: re-enroll (add any new approved reservists that joined CDC after muster was created)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reenroll':
            added = _enroll_reservists_for_muster(muster)
            messages.success(request, f'Added {added} new reservist(s) to this muster.')
            return redirect('cdc:muster_detail', pk=pk)
        if action == 'update_enrollment':
            enrollment_id = request.POST.get('enrollment_id')
            if enrollment_id:
                enrollment = get_object_or_404(
                    MusterEnrollment,
                    pk=enrollment_id,
                    muster=muster,
                )
                form = MusterEnrollmentStatusForm(request.POST, instance=enrollment)
                if form.is_valid():
                    form.save()
                    messages.success(request, 'Enrollment updated.')
                    return redirect('cdc:muster_detail', pk=pk)

    # Locations of reservists who marked present (for MapLibre map)
    present_locations = []
    for enr in enrollments:
        if enr.status == MusterEnrollment.EnrollmentStatus.PRESENT and enr.latitude is not None and enr.longitude is not None:
            present_locations.append({
                'name': enr.reservist.full_name or 'Reservist',
                'lat': float(enr.latitude),
                'lng': float(enr.longitude),
            })
    import json
    present_locations_json = json.dumps(present_locations)

    # RCDG and CDC locations for map markers (muster's CDC and its parent RCDG)
    rcdg_location = None
    cdc_location = None
    muster_cdc = muster.cdc
    if muster_cdc:
        try:
            if muster_cdc.latitude and muster_cdc.longitude:
                cdc_location = {
                    'lat': float(muster_cdc.latitude),
                    'lng': float(muster_cdc.longitude),
                    'name': muster_cdc.cdc_desc or muster_cdc.cdc_code or 'CDC',
                }
        except (TypeError, ValueError):
            pass
        if muster_cdc.rcdg_id:
            rcdg = muster_cdc.rcdg
            if rcdg and rcdg.latitude and rcdg.longitude:
                try:
                    rcdg_location = {
                        'lat': float(rcdg.latitude),
                        'lng': float(rcdg.longitude),
                        'name': rcdg.rcdg_desc or 'RCDG',
                    }
                except (TypeError, ValueError):
                    pass
    rcdg_location_json = json.dumps(rcdg_location)
    cdc_location_json = json.dumps(cdc_location)

    return render(request, 'cdc_portal/mustering/muster_detail.html', {
        'muster': muster,
        'enrollments': enrollments,
        'enrollment_status_form': MusterEnrollmentStatusForm(),
        'present_locations': present_locations,
        'present_locations_json': present_locations_json,
        'rcdg_location_json': rcdg_location_json,
        'cdc_location_json': cdc_location_json,
    })


@login_required
def muster_delete(request, pk):
    """CDC: delete a muster (and all enrollments)."""
    if not _require_cdc(request):
        return redirect('dashboard')

    cdc = request.user.assigned_cdc
    if not cdc:
        return redirect('cdc:cdc_dashboard')

    muster = get_object_or_404(Muster, pk=pk, cdc=cdc)
    if request.method == 'POST':
        title = muster.title
        muster.delete()
        messages.success(request, f'Muster "{title}" deleted.')
        return redirect('cdc:muster_list')
    return render(request, 'cdc_portal/mustering/muster_confirm_delete.html', {'muster': muster})
