from django import forms
from .models import Incident


class IncidentForm(forms.ModelForm):
    """Form for creating/editing incidents."""

    latitude = forms.DecimalField(
        max_digits=10, decimal_places=7,
        widget=forms.HiddenInput(attrs={'id': 'id_latitude'}),
    )
    longitude = forms.DecimalField(
        max_digits=10, decimal_places=7,
        widget=forms.HiddenInput(attrs={'id': 'id_longitude'}),
    )

    class Meta:
        model = Incident
        fields = [
            'title', 'description', 'incident_type', 'video_upload',
            'latitude', 'longitude', 'region', 'province', 'municipality', 'barangay',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Incident Title',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the incident in detail...',
            }),
            'incident_type': forms.Select(attrs={'class': 'form-select'}),
            'video_upload': forms.ClearableFileInput(attrs={
                'class': 'form-control', 'accept': 'video/*,image/*',
            }),
            'region': forms.Select(attrs={
                'class': 'form-select', 'id': 'sel_region',
            }, choices=[('', 'Select Region')]),
            'province': forms.Select(attrs={
                'class': 'form-select', 'id': 'sel_province',
            }, choices=[('', 'Select Province')]),
            'municipality': forms.Select(attrs={
                'class': 'form-select', 'id': 'sel_city',
            }, choices=[('', 'Select City/Municipality')]),
            'barangay': forms.Select(attrs={
                'class': 'form-select', 'id': 'sel_brgy',
            }, choices=[('', 'Select Barangay')]),
        }

    def clean_video_upload(self):
        """Validate file size (max 100MB)."""
        video = self.cleaned_data.get('video_upload')
        if video and video.size > 104857600:
            raise forms.ValidationError('File size must be under 100MB.')
        return video
