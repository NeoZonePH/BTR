from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation

from .forms import ReservistRegistrationForm, UserLoginForm
from .models import User, Notification


# ════════════════════════════════════════════════════════════════
# ACCOUNT SETTINGS
# ════════════════════════════════════════════════════════════════

@login_required
def account_settings(request):
    """Settings page: change password and set headquarters location."""
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'password':
            current = request.POST.get('current_password', '')
            new1 = request.POST.get('new_password1', '')
            new2 = request.POST.get('new_password2', '')

            if not request.user.check_password(current):
                messages.error(request, 'Current password is incorrect.')
            elif new1 != new2:
                messages.error(request, 'New passwords do not match.')
            elif len(new1) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
            else:
                request.user.set_password(new1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password updated successfully!')

        elif form_type == 'location':
            try:
                lat_str = request.POST.get('latitude', '').strip()
                lng_str = request.POST.get('longitude', '').strip()
                
                # If RCDG/CDC, save to the reference model directly
                saved_to_ref = False
                if request.user.role == 'RCDG' and request.user.assigned_rcdg:
                    request.user.assigned_rcdg.latitude = lat_str or None
                    request.user.assigned_rcdg.longitude = lng_str or None
                    request.user.assigned_rcdg.save()
                    saved_to_ref = True
                elif request.user.role == 'CDC' and request.user.assigned_cdc:
                    request.user.assigned_cdc.latitude = lat_str or None
                    request.user.assigned_cdc.longitude = lng_str or None
                    request.user.assigned_cdc.save()
                    saved_to_ref = True
                
                if not saved_to_ref:
                    # Fallback to User model (e.g. for RESCOM or DRRMOs)
                    request.user.latitude = Decimal(lat_str) if lat_str else None
                    request.user.longitude = Decimal(lng_str) if lng_str else None
                    request.user.save()
                    
                messages.success(request, 'Headquarters location saved!')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Invalid coordinates. Please enter valid numbers.')

    return render(request, 'users/accounts/settings.html')


# ════════════════════════════════════════════════════════════════
# AUTH VIEWS
# ════════════════════════════════════════════════════════════════

def login_view(request):
    """User login with role-based redirect. Blocks unapproved reservists."""
    if request.user.is_authenticated:
        return redirect(request.user.dashboard_url)

    form = UserLoginForm()
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                if not user.is_approved:
                    messages.warning(
                        request,
                        'Your account is pending approval by your CDC. '
                        'Please wait for your Community Defense Center to verify your registration.',
                    )
                    return render(request, 'users/registration/login.html', {'form': form})
                login(request, user)
                messages.success(request, f'Welcome back, {user.full_name}!')
                return redirect(user.dashboard_url)
            else:
                messages.error(request, 'Invalid username or password.')
    return render(request, 'users/registration/login.html', {'form': form})


def register_view(request):
    """Public registration — Reservists only. Must be approved by CDC."""
    if request.user.is_authenticated:
        return redirect(request.user.dashboard_url)

    form = ReservistRegistrationForm()
    if request.method == 'POST':
        form = ReservistRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Store RCDG/CDC reference selections
            from references.models import Rcdg, Cdc
            rcdg_text = request.POST.get('assigned_rcdg', '').strip()
            cdc_text = request.POST.get('assigned_cdc', '').strip()
            if rcdg_text:
                rcdg_obj = Rcdg.objects.filter(rcdg_desc=rcdg_text).first()
                if rcdg_obj:
                    user.assigned_rcdg = rcdg_obj
            if cdc_text:
                cdc_obj = Cdc.objects.filter(cdc_desc=cdc_text).first()
                if not cdc_obj:
                    cdc_obj = Cdc.objects.filter(cdc_code=cdc_text).first()
                if cdc_obj:
                    user.assigned_cdc = cdc_obj
            user.save()
            messages.info(
                request,
                '🎉 Registration successful! Your account is pending approval. '
                'Your CDC administrator will review and activate your account.',
            )
            return redirect('login')
    return render(request, 'users/registration/register.html', {'form': form})


def logout_view(request):
    """Logout user."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def dashboard_redirect(request):
    """Redirect to role-specific dashboard."""
    return redirect(request.user.dashboard_url)


# ════════════════════════════════════════════════════════════════
# NOTIFICATION VIEWS
# ════════════════════════════════════════════════════════════════

@login_required
def mark_notification_read(request, pk):
    notification = Notification.objects.filter(pk=pk, user=request.user).first()
    if notification:
        notification.is_read = True
        notification.save()
    return redirect(request.META.get('HTTP_REFERER', '/dashboard/'))


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', '/dashboard/'))


# ════════════════════════════════════════════════════════════════
# AJAX ENDPOINTS — cascading dropdowns
# ════════════════════════════════════════════════════════════════

def get_cdc_for_rcdg(request):
    """Return CDC users under a specific RCDG (for cascading dropdowns)."""
    rcdg_id = request.GET.get('rcdg_id')
    if rcdg_id:
        cdcs = User.objects.filter(role='CDC', assigned_rcdg_id=rcdg_id).values('id', 'full_name')
        return JsonResponse(list(cdcs), safe=False)
    return JsonResponse([], safe=False)


def get_rcdg_list(request):
    """Return all RCDG users (for registration dropdown)."""
    rcdgs = User.objects.filter(role='RCDG').values('id', 'full_name')
    return JsonResponse(list(rcdgs), safe=False)
