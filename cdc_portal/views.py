"""
CDC portal views: DRRMO account management and reservist approval (CDC-scoped).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from users.models import User
from users.forms import AccountCreateForm, AccountEditForm


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
