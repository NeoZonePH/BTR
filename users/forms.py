from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class ReservistRegistrationForm(UserCreationForm):
    """
    Public registration form — only for Reservists.
    Role is hardcoded to RESERVIST. RCDG and CDC are submitted as text
    from cascading dropdowns backed by the references.Rcdg / references.Cdc models.
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
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
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

        # Make some fields optional
        self.fields['rank'].required = False
        self.fields['afpsn'].required = False

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
