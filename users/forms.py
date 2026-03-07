import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import User

# Optional: disposable email validator (only used if package is installed)
try:
    from disposable_email_checker.validators import validate_disposable_email
except ImportError:
    validate_disposable_email = None


# Minimum seconds the signup form must be visible before submission (anti-bot)
SIGNUP_FORM_MIN_SECONDS = 3

# Regex: 6+ consecutive digits in username — common bot pattern
SUSPICIOUS_USERNAME_NUMERIC_PATTERN = re.compile(r'\d{6,}')


class ReservistRegistrationForm(UserCreationForm):
    """
    Public registration form — only for Reservists.
    Role is hardcoded to RESERVIST. RCDG and CDC are submitted as text
    from cascading dropdowns backed by the references.Rcdg / references.Cdc models.

    Anti-bot: honeypot field "middle_name" (must stay empty); validated in view.
    """

    class Meta:
        model = User
        fields = [
            'username', 'full_name', 'email', 'rank', 'afpsn',
            'region', 'province', 'municipality', 'barangay', 'mobile_number',
            'password1', 'password2',
        ]

    # Honeypot: hidden via CSS; if filled, view rejects with 403
    middle_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control hp-field',
            'tabindex': '-1',
            'autocomplete': 'off',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                field.widget.attrs.setdefault('class', 'form-control')

        placeholders = {
            'username': 'Username',
            'full_name': 'Full Name',
            'email': 'Email (optional)',
            'rank': 'Rank (optional)',
            'afpsn': 'Service Number (optional)',
            'region': 'Region',
            'province': 'Province',
            'municipality': 'Municipality',
            'mobile_number': 'Mobile Number',
            'password1': 'Password',
            'password2': 'Confirm Password',
        }
        for name, placeholder in placeholders.items():
            if name in self.fields:
                self.fields[name].widget.attrs['placeholder'] = placeholder

        # Optional fields
        self.fields['rank'].required = False
        self.fields['afpsn'].required = False
        self.fields['email'].required = False

    def clean_username(self):
        """Reject usernames with long numeric sequences (e.g. user123456789)."""
        username = self.cleaned_data.get('username', '') or ''
        if SUSPICIOUS_USERNAME_NUMERIC_PATTERN.search(username):
            raise ValidationError(
                'This username looks invalid. Please avoid long number sequences.'
            )
        return username

    def clean_email(self):
        """Reject disposable/temporary email domains when email is provided."""
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return email
        if validate_disposable_email is not None:
            try:
                validate_disposable_email(email)
            except ValidationError:
                raise ValidationError('Temporary or disposable email addresses are not allowed.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.RESERVIST
        user.is_approved = False  # Must be approved by CDC
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    """Login form."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
    )


class AccountCreateForm(UserCreationForm):
    """
    Form used by RESCOM/RCDG/CDC to create subordinate accounts.
    The role and parent assignment are set by the view, not the form.
    """

    class Meta:
        model = User
        fields = [
            'username', 'full_name', 'rank', 'afpsn',
            'region', 'province', 'municipality', 'barangay', 'mobile_number',
            'password1', 'password2',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')

        placeholders = {
            'username': 'Username',
            'full_name': 'Full Name',
            'rank': 'Rank (optional)',
            'afpsn': 'Service Number (optional)',
            'region': 'Region',
            'province': 'Province',
            'municipality': 'Municipality',
            'mobile_number': 'Mobile Number',
            'password1': 'Password',
            'password2': 'Confirm Password',
        }
        for name, placeholder in placeholders.items():
            if name in self.fields:
                self.fields[name].widget.attrs['placeholder'] = placeholder

        self.fields['rank'].required = False
        self.fields['afpsn'].required = False


class AccountEditForm(forms.ModelForm):
    """
    Form for editing existing accounts (no password fields).
    Used by RESCOM/RCDG/CDC to update subordinate accounts.
    """

    class Meta:
        model = User
        fields = [
            'username', 'full_name', 'rank', 'afpsn',
            'region', 'province', 'municipality', 'barangay', 'mobile_number',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')

        placeholders = {
            'username': 'Username',
            'full_name': 'Full Name',
            'rank': 'Rank (optional)',
            'afpsn': 'Service Number (optional)',
            'region': 'Region',
            'province': 'Province',
            'municipality': 'Municipality',
            'mobile_number': 'Mobile Number',
        }
        for name, placeholder in placeholders.items():
            if name in self.fields:
                self.fields[name].widget.attrs['placeholder'] = placeholder

        self.fields['rank'].required = False
        self.fields['afpsn'].required = False
