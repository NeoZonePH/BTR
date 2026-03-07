"""
RESCOM portal views: RCDG account management, RCDG/CDC reference CRUD,
and RESCOM-scoped CDC, DRRMO, and reservist approval.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count

from users.models import User
from users.forms import AccountCreateForm, AccountEditForm
from references.models import Rcdg, Cdc


def _require_rescom(request):
    if request.user.role != 'RESCOM':
        messages.error(request, 'Access denied.')
        return False
    return True


# ════════════════════════════════════════════════════════════════
# INCIDENT MANAGEMENT (RESCOM only)
# ════════════════════════════════════════════════════════════════

@login_required
def hard_delete_incident(request, pk):
    """RESCOM: Permanently delete a soft-deleted incident."""
    if not _require_rescom(request):
        return redirect('dashboard')
        
    # Import Incident here or at the top of the file
    from apps.reservist_portal.models import Incident
    
    incident = get_object_or_404(Incident, pk=pk)
    if request.method == 'POST':
        incident.delete()
        messages.success(request, 'Incident permanently deleted.')
    return redirect('reservist:recycle_bin')


@login_required
def reservist_activity_logs(request):
    """RESCOM: View activity logs of all reservists."""
    if not _require_rescom(request):
        return redirect('dashboard')
        
    from users.models import ActivityLog
    logs = ActivityLog.objects.all().select_related('user')
    return render(request, 'rescom_portal/activity_logs.html', {
        'logs': logs
    })


@login_required
def database_management(request):
    """RESCOM: Database backup and restore operations via pg_dump and psql."""
    if not _require_rescom(request):
        return redirect('dashboard')
        
    import os
    import subprocess
    from datetime import datetime
    from django.conf import settings
    from django.http import HttpResponse

    db_settings = settings.DATABASES['default']
    db_name = db_settings.get('NAME')
    db_user = db_settings.get('USER')
    db_password = db_settings.get('PASSWORD')
    db_host = db_settings.get('HOST', 'localhost')
    db_port = db_settings.get('PORT', '5432')

    # Ensure PG environment variables are set for subprocess
    env = os.environ.copy()
    if db_password:
        env['PGPASSWORD'] = db_password

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'backup':
            # Execute pg_dump
            cmd = [
                'pg_dump',
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '--clean',   # Include DROP statements for restore
                '--if-exists',
                db_name
            ]
            try:
                result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
                # Return the SQL as a downloadable file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"backup_{db_name}_{timestamp}.sql"
                response = HttpResponse(result.stdout, content_type='application/sql')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            except subprocess.CalledProcessError as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Backup failed: {e.stderr}")
                messages.error(request, f"Database backup failed. Check server logs.")

        elif action == 'restore':
            backup_file = request.FILES.get('backup_file')
            if not backup_file:
                messages.error(request, "Please provide a valid .sql backup file.")
            elif not backup_file.name.endswith('.sql'):
                messages.error(request, "Invalid file format. Please upload a .sql file.")
            else:
                # Save the uploaded file temporarily
                import tempfile
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as temp_file:
                        for chunk in backup_file.chunks():
                            temp_file.write(chunk)
                        temp_file_path = temp_file.name

                    # Execute psql to restore
                    cmd = [
                        'psql',
                        '-h', db_host,
                        '-p', str(db_port),
                        '-U', db_user,
                        '-d', db_name,
                        '-f', temp_file_path
                    ]
                    
                    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                    if result.returncode == 0:
                        messages.success(request, "Database successfully restored from backup!")
                    else:
                        messages.error(request, f"Database restore encountered errors. Error output: {result.stderr[:200]}")
                        
                except Exception as e:
                    messages.error(request, f"Restore process failed: {str(e)}")
                finally:
                    # Clean up the temporary file
                    if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
        
        return redirect('rescom:database_management')

    return render(request, 'rescom_portal/database_management.html')

@login_required
def server_storage_status(request):
    """RESCOM: Monitor server disk storage usage."""
    if not _require_rescom(request):
        return redirect('dashboard')
        
    import shutil
    
    # Get disk usage for the root partition
    total, used, free = shutil.disk_usage('/')
    
    # Convert bytes to gigabytes
    gb = 1024 ** 3
    total_gb = round(total / gb, 2)
    used_gb = round(used / gb, 2)
    free_gb = round(free / gb, 2)
    
    # Calculate percentages for the UI
    used_percentage = round((used / total) * 100, 1)
    
    context = {
        'total_gb': total_gb,
        'used_gb': used_gb,
        'free_gb': free_gb,
        'used_percentage': used_percentage,
    }
    
    return render(request, 'rescom_portal/server_storage.html', context)


# ════════════════════════════════════════════════════════════════
# RCDG ACCOUNT MANAGEMENT (RESCOM only)
# ════════════════════════════════════════════════════════════════

@login_required
def manage_rcdg_accounts(request):
    """RESCOM: list and create RCDG accounts."""
    if not _require_rescom(request):
        return redirect('dashboard')

    rcdg_users = User.objects.filter(role='RCDG').order_by('full_name')
    return render(request, 'rescom_portal/accounts/manage_accounts.html', {
        'accounts': rcdg_users,
        'account_type': 'RCDG',
        'account_type_full': 'Regional Community Defense Group',
        'create_url_name': 'rescom:create_rcdg_account',
        'edit_url_name': 'rescom:edit_rcdg_account',
        'delete_url_name': 'rescom:delete_rcdg_account',
    })


@login_required
def create_rcdg_account(request):
    """RESCOM: create a new RCDG account."""
    if not _require_rescom(request):
        return redirect('dashboard')

    form = AccountCreateForm()
    if request.method == 'POST':
        form = AccountCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.RCDG
            user.is_approved = True
            user.save()
            messages.success(request, f'RCDG account "{user.full_name}" created successfully.')
            return redirect('rescom:manage_rcdg_accounts')
    return render(request, 'rescom_portal/accounts/create_account.html', {
        'form': form,
        'account_type': 'RCDG',
        'account_type_full': 'Regional Community Defense Group',
        'back_url_name': 'rescom:manage_rcdg_accounts',
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
    })


@login_required
def edit_rcdg_account(request, pk):
    """RESCOM: edit an existing RCDG account."""
    if not _require_rescom(request):
        return redirect('dashboard')
    user = get_object_or_404(User, pk=pk, role='RCDG')

    form = AccountEditForm(instance=user)
    if request.method == 'POST':
        form = AccountEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'RCDG account "{user.full_name}" updated successfully.')
            return redirect('rescom:manage_rcdg_accounts')
    return render(request, 'rescom_portal/accounts/edit_account.html', {
        'form': form,
        'account': user,
        'account_type': 'RCDG',
        'account_type_full': 'Regional Community Defense Group',
        'back_url_name': 'rescom:manage_rcdg_accounts',
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
    })


@login_required
def delete_rcdg_account(request, pk):
    """RESCOM: delete an RCDG account."""
    if not _require_rescom(request):
        return redirect('dashboard')
    user = get_object_or_404(User, pk=pk, role='RCDG')
    if request.method == 'POST':
        name = user.full_name
        user.delete()
        messages.success(request, f'RCDG account "{name}" deleted.')
    return redirect('rescom:manage_rcdg_accounts')


# ════════════════════════════════════════════════════════════════
# RESCOM-SCOPED CDC ACCOUNT MANAGEMENT (all CDCs)
# ════════════════════════════════════════════════════════════════

@login_required
def manage_cdc_accounts(request):
    """RESCOM: list all CDC accounts."""
    if not _require_rescom(request):
        return redirect('dashboard')

    cdc_users = User.objects.filter(role='CDC').order_by('full_name')
    return render(request, 'rescom_portal/accounts/manage_accounts.html', {
        'accounts': cdc_users,
        'account_type': 'CDC',
        'account_type_full': 'Community Defense Center',
        'create_url_name': 'rescom:create_cdc_account',
        'delete_url_name': 'rescom:delete_cdc_account',
    })


@login_required
def create_cdc_account(request):
    """RESCOM: create a new CDC account."""
    if not _require_rescom(request):
        return redirect('dashboard')

    form = AccountCreateForm()
    if request.method == 'POST':
        form = AccountCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.CDC
            user.is_approved = True
            rcdg_ref_id = request.POST.get('assigned_rcdg_ref', '').strip()
            cdc_ref_id = request.POST.get('assigned_cdc_ref', '').strip()
            if rcdg_ref_id:
                user.assigned_rcdg = Rcdg.objects.filter(pk=rcdg_ref_id).first()
            if cdc_ref_id:
                user.assigned_cdc = Cdc.objects.filter(pk=cdc_ref_id).first()
            user.save()
            messages.success(request, f'CDC account "{user.full_name}" created successfully.')
            return redirect('rescom:manage_cdc_accounts')
    return render(request, 'rescom_portal/accounts/create_account.html', {
        'form': form,
        'account_type': 'CDC',
        'account_type_full': 'Community Defense Center',
        'back_url_name': 'rescom:manage_cdc_accounts',
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
        'show_cdc_dropdown': True,
    })


@login_required
def delete_cdc_account(request, pk):
    """RESCOM: delete a CDC account."""
    if not _require_rescom(request):
        return redirect('dashboard')
    user = get_object_or_404(User, pk=pk, role='CDC')
    if request.method == 'POST':
        name = user.full_name
        user.delete()
        messages.success(request, f'CDC account "{name}" deleted.')
    return redirect('rescom:manage_cdc_accounts')


# ════════════════════════════════════════════════════════════════
# RESCOM-SCOPED DRRMO ACCOUNT MANAGEMENT (all PDRRMO/MDRRMO)
# ════════════════════════════════════════════════════════════════

@login_required
def manage_drrmo_accounts(request):
    """RESCOM: list all PDRRMO/MDRRMO accounts."""
    if not _require_rescom(request):
        return redirect('dashboard')

    drrmo_users = User.objects.filter(role__in=['PDRRMO', 'MDRRMO']).order_by('role', 'full_name')
    return render(request, 'rescom_portal/accounts/manage_accounts.html', {
        'accounts': drrmo_users,
        'account_type': 'DRRMO',
        'account_type_full': 'PDRRMO / MDRRMO',
        'create_url_name': 'rescom:create_drrmo_account',
        'edit_url_name': None,
        'delete_url_name': 'rescom:delete_drrmo_account',
        'show_role_picker': True,
    })


@login_required
def create_drrmo_account(request):
    """RESCOM: create a new PDRRMO or MDRRMO account."""
    if not _require_rescom(request):
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
            user.save()
            messages.success(request, f'{role_choice} account "{user.full_name}" created successfully.')
            return redirect('rescom:manage_drrmo_accounts')
    return render(request, 'rescom_portal/accounts/create_account.html', {
        'form': form,
        'account_type': role_choice,
        'account_type_full': 'Provincial DRRMO' if role_choice == 'PDRRMO' else 'Municipal DRRMO',
        'back_url_name': 'rescom:manage_drrmo_accounts',
        'show_role_picker': True,
        'current_role': role_choice,
    })


@login_required
def delete_drrmo_account(request, pk):
    """RESCOM: delete a PDRRMO/MDRRMO account."""
    if not _require_rescom(request):
        return redirect('dashboard')
    user = get_object_or_404(User, pk=pk, role__in=['PDRRMO', 'MDRRMO'])
    if request.method == 'POST':
        name = user.full_name
        user.delete()
        messages.success(request, f'DRRMO account "{name}" deleted.')
    return redirect('rescom:manage_drrmo_accounts')


# ════════════════════════════════════════════════════════════════
# RESCOM-SCOPED PENDING RESERVISTS (all pending)
# ════════════════════════════════════════════════════════════════

@login_required
def pending_reservists(request):
    """RESCOM: list all pending reservist sign-ups."""
    if not _require_rescom(request):
        return redirect('dashboard')

    pending = User.objects.filter(role='RESERVIST', is_approved=False).order_by('-date_joined')
    return render(request, 'rescom_portal/accounts/pending_reservists.html', {
        'pending_users': pending,
        'approve_url_name': 'rescom:approve_reservist',
        'reject_url_name': 'rescom:reject_reservist',
    })


@login_required
def approve_reservist(request, pk):
    """RESCOM: approve a reservist account."""
    if not _require_rescom(request):
        return redirect('dashboard')

    user = get_object_or_404(User, pk=pk, role='RESERVIST', is_approved=False)

    if request.method == 'POST':
        user.is_approved = True
        user.save()
        messages.success(request, f'Reservist "{user.full_name}" approved successfully.')
    return redirect('rescom:pending_reservists')


@login_required
def reject_reservist(request, pk):
    """RESCOM: reject and delete a reservist sign-up."""
    if not _require_rescom(request):
        return redirect('dashboard')

    user = get_object_or_404(User, pk=pk, role='RESERVIST', is_approved=False)

    if request.method == 'POST':
        name = user.full_name
        user.delete()
        messages.success(request, f'Reservist "{name}" registration rejected.')
    return redirect('rescom:pending_reservists')


# ════════════════════════════════════════════════════════════════
# RCDG / CDC REFERENCE CRUD (RESCOM only — organization data)
# ════════════════════════════════════════════════════════════════

@login_required
def rcdg_list(request):
    if not _require_rescom(request):
        return redirect('dashboard')
    q = request.GET.get('q', '').strip()
    rcdgs = Rcdg.objects.annotate(cdc_count=Count('cdc')).order_by('rcdg_desc')
    if q:
        rcdgs = rcdgs.filter(
            Q(rcdg_desc__icontains=q) |
            Q(rcdg_address__icontains=q) |
            Q(rcdg_commander__icontains=q)
        )
    return render(request, 'rescom_portal/rcdg_list.html', {
        'rcdgs': rcdgs,
        'search_query': q,
    })


@login_required
def rcdg_create(request):
    if not _require_rescom(request):
        return redirect('dashboard')
    if request.method == 'POST':
        rcdg = Rcdg(
            rcdg_desc=request.POST.get('rcdg_desc', '').strip(),
            rcdg_address=request.POST.get('rcdg_address', '').strip(),
            rcdg_commander=request.POST.get('rcdg_commander', '').strip(),
            cp_no=request.POST.get('cp_no', '').strip() or None,
            latitude=request.POST.get('latitude', '').strip() or None,
            longitude=request.POST.get('longitude', '').strip() or None,
        )
        try:
            rcdg.save()
            messages.success(request, f'RCDG "{rcdg.rcdg_desc}" created successfully.')
            return redirect('rescom:ref_rcdg_list')
        except Exception as e:
            messages.error(request, f'Error creating RCDG: {e}')
    return render(request, 'rescom_portal/rcdg_form.html', {
        'title': 'Create RCDG',
        'submit_label': 'Create RCDG',
    })


@login_required
def rcdg_edit(request, pk):
    if not _require_rescom(request):
        return redirect('dashboard')
    rcdg = get_object_or_404(Rcdg, pk=pk)
    if request.method == 'POST':
        rcdg.rcdg_desc = request.POST.get('rcdg_desc', '').strip()
        rcdg.rcdg_address = request.POST.get('rcdg_address', '').strip()
        rcdg.rcdg_commander = request.POST.get('rcdg_commander', '').strip()
        rcdg.cp_no = request.POST.get('cp_no', '').strip() or None
        rcdg.latitude = request.POST.get('latitude', '').strip() or None
        rcdg.longitude = request.POST.get('longitude', '').strip() or None
        try:
            rcdg.save()
            messages.success(request, f'RCDG "{rcdg.rcdg_desc}" updated.')
            return redirect('rescom:ref_rcdg_list')
        except Exception as e:
            messages.error(request, f'Error updating RCDG: {e}')
    return render(request, 'rescom_portal/rcdg_form.html', {
        'title': 'Edit RCDG',
        'submit_label': 'Save Changes',
        'rcdg': rcdg,
    })


@login_required
def rcdg_delete(request, pk):
    if not _require_rescom(request):
        return redirect('dashboard')
    rcdg = get_object_or_404(Rcdg, pk=pk)
    if request.method == 'POST':
        name = rcdg.rcdg_desc
        rcdg.delete()
        messages.success(request, f'RCDG "{name}" deleted.')
    return redirect('rescom:ref_rcdg_list')


@login_required
def cdc_list(request):
    if not _require_rescom(request):
        return redirect('dashboard')
    q = request.GET.get('q', '').strip()
    cdcs = Cdc.objects.select_related('rcdg').order_by('cdc_code')
    if q:
        cdcs = cdcs.filter(
            Q(cdc_code__icontains=q) |
            Q(cdc_desc__icontains=q) |
            Q(cdc_address__icontains=q) |
            Q(cdc_director__icontains=q) |
            Q(rcdg__rcdg_desc__icontains=q)
        )
    rcdg_filter = request.GET.get('rcdg', '')
    if rcdg_filter:
        cdcs = cdcs.filter(rcdg_id=rcdg_filter)
    return render(request, 'rescom_portal/cdc_list.html', {
        'cdcs': cdcs,
        'search_query': q,
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
        'selected_rcdg': rcdg_filter,
    })


@login_required
def cdc_create(request):
    if not _require_rescom(request):
        return redirect('dashboard')
    if request.method == 'POST':
        rcdg_id = request.POST.get('rcdg')
        cdc = Cdc(
            rcdg_id=rcdg_id,
            cdc_code=request.POST.get('cdc_code', '').strip(),
            cdc_desc=request.POST.get('cdc_desc', '').strip() or None,
            cdc_address=request.POST.get('cdc_address', '').strip() or None,
            cdc_director=request.POST.get('cdc_director', '').strip() or None,
            cp_no=request.POST.get('cp_no', '').strip() or None,
            latitude=request.POST.get('latitude', '').strip() or None,
            longitude=request.POST.get('longitude', '').strip() or None,
        )
        try:
            cdc.save()
            messages.success(request, f'CDC "{cdc.cdc_code}" created successfully.')
            return redirect('rescom:ref_cdc_list')
        except Exception as e:
            messages.error(request, f'Error creating CDC: {e}')
    return render(request, 'rescom_portal/cdc_form.html', {
        'title': 'Create CDC',
        'submit_label': 'Create CDC',
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
    })


@login_required
def cdc_edit(request, pk):
    if not _require_rescom(request):
        return redirect('dashboard')
    cdc = get_object_or_404(Cdc, pk=pk)
    if request.method == 'POST':
        cdc.rcdg_id = request.POST.get('rcdg')
        cdc.cdc_code = request.POST.get('cdc_code', '').strip()
        cdc.cdc_desc = request.POST.get('cdc_desc', '').strip() or None
        cdc.cdc_address = request.POST.get('cdc_address', '').strip() or None
        cdc.cdc_director = request.POST.get('cdc_director', '').strip() or None
        cdc.cp_no = request.POST.get('cp_no', '').strip() or None
        cdc.latitude = request.POST.get('latitude', '').strip() or None
        cdc.longitude = request.POST.get('longitude', '').strip() or None
        try:
            cdc.save()
            messages.success(request, f'CDC "{cdc.cdc_code}" updated.')
            return redirect('rescom:ref_cdc_list')
        except Exception as e:
            messages.error(request, f'Error updating CDC: {e}')
    return render(request, 'rescom_portal/cdc_form.html', {
        'title': 'Edit CDC',
        'submit_label': 'Save Changes',
        'cdc': cdc,
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
    })


@login_required
def cdc_delete(request, pk):
    if not _require_rescom(request):
        return redirect('dashboard')
    cdc = get_object_or_404(Cdc, pk=pk)
    if request.method == 'POST':
        code = cdc.cdc_code
        cdc.delete()
        messages.success(request, f'CDC "{code}" deleted.')
    return redirect('rescom:ref_cdc_list')
