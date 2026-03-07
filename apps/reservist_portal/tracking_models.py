from django.db import models
from django.conf import settings

class ResponderTracking(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        RESPONDING = 'responding', 'Responding'
        ON_SCENE = 'on_scene', 'On Scene'
        COMPLETED = 'completed', 'Completed'

    reservist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='active_responses')
    incident = models.ForeignKey('reservist_portal.Incident', on_delete=models.CASCADE, related_name='responders')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-timestamp']
        unique_together = ('reservist', 'incident')

    def __str__(self):
        return f"{self.reservist.full_name} -> {self.incident.title} ({self.get_status_display()})"
