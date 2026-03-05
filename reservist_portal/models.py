import os
from io import BytesIO
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from PIL import Image


def incident_upload_path(instance, filename):
    """Upload path for incident files."""
    return os.path.join('incidents', str(instance.reservist_id), filename)


class Incident(models.Model):
    """Emergency incident report model."""

    class IncidentType(models.TextChoices):
        ACCIDENT = 'accident', 'Accident'
        EARTHQUAKE = 'earthquake', 'Earthquake'
        FLOOD = 'flood', 'Flood'
        TYPHOON = 'typhoon', 'Typhoon'
        FIRE = 'fire', 'Fire'
        LANDSLIDE = 'landslide', 'Landslide'
        OTHERS = 'others', 'Others'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VALIDATED = 'validated', 'Validated'
        RESOLVED = 'resolved', 'Resolved'

    reservist = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='incidents',
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    incident_type = models.CharField(max_length=20, choices=IncidentType.choices, db_index=True)
    video_upload = models.FileField(
        upload_to=incident_upload_path, blank=True, null=True,
        validators=[FileExtensionValidator(
            allowed_extensions=['mp4', 'avi', 'mov', 'mkv', 'wmv', 'webm', 'jpg', 'jpeg', 'png', 'gif', 'webp'],
        )],
        help_text='Upload video or image evidence (max 100MB)',
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    region = models.CharField(max_length=255, blank=True)
    province = models.CharField(max_length=255, blank=True)
    municipality = models.CharField(max_length=255, blank=True)
    barangay = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """Override save to convert JPEG/PNG uploads to WebP."""
        if self.video_upload:
            name = self.video_upload.name.lower()
            if name.endswith(('.jpg', '.jpeg', '.png')):
                try:
                    img = Image.open(self.video_upload)
                    if img.mode in ('RGBA', 'LA'):
                        pass  # keep alpha for WebP
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    buffer = BytesIO()
                    img.save(buffer, format='WEBP', quality=85)
                    buffer.seek(0)
                    new_name = os.path.splitext(self.video_upload.name)[0] + '.webp'
                    self.video_upload = ContentFile(buffer.read(), name=new_name)
                except Exception:
                    pass  # If conversion fails, keep original file
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.get_incident_type_display()} ({self.get_status_display()})"

    @property
    def marker_color(self):
        """Return marker color based on incident type."""
        colors = {
            'accident': '#e74c3c',
            'earthquake': '#9b59b6',
            'flood': '#3498db',
            'typhoon': '#1abc9c',
            'fire': '#e67e22',
            'landslide': '#795548',
            'others': '#95a5a6',
        }
        return colors.get(self.incident_type, '#95a5a6')


class AISummary(models.Model):
    """Stored AI-generated summaries."""

    class Period(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'

    period = models.CharField(max_length=10, choices=Period.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    summary_text = models.TextField()
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'AI Summaries'

    def __str__(self):
        return f"{self.get_period_display()} Summary: {self.period_start} - {self.period_end}"
