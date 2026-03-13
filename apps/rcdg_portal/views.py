"""
RCDG portal views: CDC account management (RCDG-scoped — only CDCs under this RCDG).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from users.models import User
from users.forms import AccountCreateForm, AccountEditForm
from references.models import Rcdg, Cdc
from apps.reservist_portal.tracking_models import ResponderTracking


def _require_rcdg(request):
    if request.user.role != 'RCDG':
        messages.error(request, 'Access denied.')
        return False
    return True


def _generate_cdc_username():
    """Generate unique username for CDC account."""
    import secrets
    base = 'cdc_' + secrets.token_hex(4)
    while User.objects.filter(username=base).exists():
        base = 'cdc_' + secrets.token_hex(4)
    return base


def _generate_random_password():
    """Generate secure random password."""
    return User.objects.make_random_password(length=12)


@login_required
def manage_cdc_accounts(request):
    """RCDG: list and create CDC accounts under this RCDG."""
    if not _require_rcdg(request):
        return redirect('dashboard')

    created_credentials = request.session.pop('created_cdc_credentials', None)

    cdc_users = User.objects.filter(
        role='CDC', assigned_rcdg=request.user.assigned_rcdg
    ).order_by('full_name')

    return render(request, 'rcdg_portal/accounts/manage_accounts.html', {
        'accounts': cdc_users,
        'account_type': 'CDC',
        'account_type_full': 'Community Defense Center',
        'create_url_name': 'rcdg:create_cdc_account',
        'edit_url_name': 'rcdg:edit_cdc_account',
        'delete_url_name': 'rcdg:delete_cdc_account',
        'created_account_credentials': created_credentials,
    })


@login_required
def create_cdc_account(request):
    """RCDG: create a new CDC account under this RCDG. Username and password are auto-generated."""
    if not _require_rcdg(request):
        return redirect('dashboard')

    form = AccountCreateForm()
    if request.method == 'POST':
        data = request.POST.copy()
        data['username'] = _generate_cdc_username()
        gen_password = _generate_random_password()
        data['password1'] = data['password2'] = gen_password
        form = AccountCreateForm(data)
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
            request.session['created_cdc_credentials'] = {
                'username': user.username,
                'password': gen_password,
                'full_name': user.full_name,
                'account_type': 'CDC',
            }
            return redirect('rcdg:manage_cdc_accounts')

    return render(request, 'rcdg_portal/accounts/create_account.html', {
        'form': form,
        'account_type': 'CDC',
        'account_type_full': 'Community Defense Center',
        'back_url_name': 'rcdg:manage_cdc_accounts',
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
        'show_cdc_dropdown': True,
        'autogenerate_credentials': True,
    })


@login_required
def edit_cdc_account(request, pk):
    """RCDG: edit a CDC account under this RCDG."""
    if not _require_rcdg(request):
        return redirect('dashboard')

    user = get_object_or_404(
        User, pk=pk, role='CDC', assigned_rcdg=request.user.assigned_rcdg
    )
    form = AccountEditForm(instance=user)
    if request.method == 'POST':
        form = AccountEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            rcdg_ref_id = request.POST.get('assigned_rcdg_ref', '').strip()
            cdc_ref_id = request.POST.get('assigned_cdc_ref', '').strip()
            if rcdg_ref_id:
                user.assigned_rcdg = Rcdg.objects.filter(pk=rcdg_ref_id).first()
            if cdc_ref_id:
                user.assigned_cdc = Cdc.objects.filter(pk=cdc_ref_id).first()
            user.save()
            messages.success(request, f'CDC account "{user.full_name}" updated successfully.')
            return redirect('rcdg:manage_cdc_accounts')

    return render(request, 'rcdg_portal/accounts/edit_account.html', {
        'form': form,
        'account': user,
        'account_type': 'CDC',
        'account_type_full': 'Community Defense Center',
        'back_url_name': 'rcdg:manage_cdc_accounts',
        'rcdgs': Rcdg.objects.all().order_by('rcdg_desc'),
        'show_cdc_dropdown': True,
    })


@login_required
def delete_cdc_account(request, pk):
    """RCDG: delete a CDC account under this RCDG."""
    if not _require_rcdg(request):
        return redirect('dashboard')

    user = get_object_or_404(
        User, pk=pk, role='CDC', assigned_rcdg=request.user.assigned_rcdg
    )
    if request.method == 'POST':
        name = user.full_name
        user.delete()
        messages.success(request, f'CDC account "{name}" deleted.')
    return redirect('rcdg:manage_cdc_accounts')


# Role filter choices for responder records (responders who clicked Respond and went to incident)
RESPONDER_ROLE_FILTERS = [
    ('', 'All responders'),
    ('PDRRMO', 'PDRRMO'),
    ('MDRRMO', 'MDRRMO'),
    ('RCDG', 'RCDG'),
    ('CDC', 'CDC'),
    ('RESERVIST', 'Reservist'),
]


@login_required
def responder_records(request):
    """RCDG: list all responders (PDRRMO, MDRRMO, RCDG, CDC, Reservist) who clicked Respond and went to an incident."""
    if not _require_rcdg(request):
        return redirect('dashboard')

    qs = ResponderTracking.objects.select_related('reservist', 'incident').order_by('-timestamp')

    role_filter = request.GET.get('role', '').strip().upper()
    if role_filter and role_filter in ('PDRRMO', 'MDRRMO', 'RCDG', 'CDC', 'RESERVIST'):
        qs = qs.filter(reservist__role=role_filter)

    responders = qs[:500]  # cap for performance

    return render(request, 'rcdg_portal/responder_records.html', {
        'responders': responders,
        'role_filters': RESPONDER_ROLE_FILTERS,
        'current_role': role_filter,
    })
