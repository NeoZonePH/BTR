import logging
import time
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from decimal import Decimal, InvalidOperation
from django.urls import reverse
from django_ratelimit.decorators import ratelimit

from .forms import ReservistRegistrationForm, UserLoginForm, SIGNUP_FORM_MIN_SECONDS
from .models import User, Notification, SignupAttempt

logger = logging.getLogger(__name__)

# Maximum successful signups per IP per day (anti-bot)
MAX_SIGNUPS_PER_IP_PER_DAY = 5


def get_client_ip(request):
    """Return client IP; respects X-Forwarded-For when behind a proxy."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '').strip()
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or '0.0.0.0'


def _log_blocked_signup(request, reason, username='', email=''):
    """Record blocked signup attempt for monitoring; also log to Python logger."""
    ip = get_client_ip(request)
    SignupAttempt.objects.create(
        ip_address=ip,
        username=(username or '')[:150],
        email=(email or '')[:254],
        success=False,
        block_reason=reason[:255],
    )
    logger.warning(
        'Signup blocked: ip=%s reason=%s username=%s email=%s',
        ip, reason, username or '(none)', email or '(none)',
    )


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

        elif form_type == 'branding' and request.user.role == 'RESCOM':
            from references.models import AppBranding
            branding = AppBranding.get()
            branding.name_code = request.POST.get('name_code', '').strip() or 'TARGET'
            branding.name_desc = request.POST.get('name_desc', '').strip() or 'TARGET — Emergency Tracker'
            branding.save()
            messages.success(request, 'Application name updated!')

    from references.models import AppBranding
    branding = AppBranding.get()
    return render(request, 'users/accounts/settings.html', {
        'app_branding': branding,
    })


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


@ratelimit(key=lambda g, r: get_client_ip(r), rate='20/h', method='POST', block=False)
@ratelimit(key=lambda g, r: get_client_ip(r), rate='3/m', method='POST', block=False)
def register_view(request):
    """
    Public registration — Reservists only. Must be approved by CDC.
    Anti-bot: rate limit (3/min, 20/h per IP), honeypot, form timing,
    disposable email, suspicious username, IP daily signup cap. Returns 403 when blocked.
    """
    if request.user.is_authenticated:
        return redirect(request.user.dashboard_url)

    # ─── POST: run all server-side checks before form validation ───
    if request.method == 'POST':
        # Rate limit (decorators set request.limited when exceeded)
        if getattr(request, 'limited', False):
            _log_blocked_signup(request, 'rate_limit')
            return HttpResponseForbidden(
                '<h1>403 Forbidden</h1><p>Too many attempts. Try again later.</p>',
                content_type='text/html',
            )

        # Honeypot: hidden field must be empty
        if request.POST.get('middle_name', '').strip():
            _log_blocked_signup(
                request, 'honeypot',
                username=request.POST.get('username', ''),
                email=request.POST.get('email', ''),
            )
            return HttpResponseForbidden(
                '<h1>403 Forbidden</h1><p>Invalid request.</p>',
                content_type='text/html',
            )

        # Form submission timing: must have been on page at least SIGNUP_FORM_MIN_SECONDS
        try:
            ts_str = request.POST.get('form_load_timestamp', '').strip()
            if not ts_str:
                _log_blocked_signup(request, 'missing_form_timestamp')
                return HttpResponseForbidden(
                    '<h1>403 Forbidden</h1><p>Invalid request.</p>',
                    content_type='text/html',
                )
            elapsed = time.time() - float(ts_str)
            if elapsed < SIGNUP_FORM_MIN_SECONDS:
                _log_blocked_signup(
                    request, 'form_submitted_too_fast',
                    username=request.POST.get('username', ''),
                    email=request.POST.get('email', ''),
                )
                return HttpResponseForbidden(
                    '<h1>403 Forbidden</h1><p>Please wait a moment before submitting.</p>',
                    content_type='text/html',
                )
        except (ValueError, TypeError):
            _log_blocked_signup(request, 'invalid_form_timestamp')
            return HttpResponseForbidden(
                '<h1>403 Forbidden</h1><p>Invalid request.</p>',
                content_type='text/html',
            )

        # IP-based daily signup limit
        ip = get_client_ip(request)
        today = date.today()
        successful_today = SignupAttempt.objects.filter(
            ip_address=ip, success=True, created_at__date=today,
        ).count()
        if successful_today >= MAX_SIGNUPS_PER_IP_PER_DAY:
            _log_blocked_signup(
                request, 'ip_daily_limit_exceeded',
                username=request.POST.get('username', ''),
                email=request.POST.get('email', ''),
            )
            return HttpResponseForbidden(
                '<h1>403 Forbidden</h1><p>Maximum signups from your network for today reached. Try again tomorrow.</p>',
                content_type='text/html',
            )

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

            # Record successful signup for IP daily limit
            SignupAttempt.objects.create(
                ip_address=ip,
                success=True,
            )

            messages.info(
                request,
                '🎉 Registration successful! Your account is pending approval. '
                'Your CDC administrator will review and activate your account.',
            )
            return redirect('login')
    else:
        form = ReservistRegistrationForm()

    # GET or form errors: pass timestamp so template can send it back on submit
    form_load_timestamp = str(time.time())
    return render(request, 'users/registration/register.html', {
        'form': form,
        'form_load_timestamp': form_load_timestamp,
    })


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
        
        if notification.incident:
            # Dynamically route to the correct incident detail page based on user role
            role = request.user.role.lower()
            try:
                if role == 'reservist':
                    url_name = 'reservist:incident_detail'
                else:
                    url_name = f'{role}:{role}_incident_detail'
                return redirect(reverse(url_name, args=[notification.incident.id]))
            except Exception as e:
                pass

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
