from django import forms
from .models import Muster, MusterEnrollment


class MusterForm(forms.ModelForm):
    """Form for creating and editing a Muster."""

    class Meta:
        model = Muster
        fields = ('title', 'activities', 'muster_date', 'location')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Monthly readiness muster'}),
            'activities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional activities'}),
            'muster_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
        }


class MusterEnrollmentStatusForm(forms.ModelForm):
    """Form to update enrollment status (e.g. Present / Absent / Excused) on detail page."""

    class Meta:
        model = MusterEnrollment
        fields = ('status', 'notes')
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'notes': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Optional note'}),
        }
