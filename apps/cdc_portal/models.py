from django.db import models
from django.conf import settings


class Muster(models.Model):
    """
    A mustering event created by a CDC. When created, all approved reservists
    under that CDC are automatically enrolled via MusterEnrollment.
    """
    class Location(models.TextChoices):
        ONLINE = 'Online', 'Online'
        FACE_TO_FACE = 'Face to Face', 'Face to Face'

    title = models.CharField(max_length=255)
    activities = models.TextField(blank=True)
    muster_date = models.DateField()
    location = models.CharField(
        max_length=50,
        blank=True,
        choices=Location.choices,
    )
    cdc = models.ForeignKey(
        'references.Cdc',
        on_delete=models.CASCADE,
        related_name='musters',
        null=False,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_musters',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-muster_date', '-created_at']
        verbose_name_plural = 'Musters'

    def __str__(self):
        return f"{self.title} ({self.muster_date})"


class MusterEnrollment(models.Model):
    """
    Links a reservist to a muster. Created automatically for all approved
    reservists under the CDC when a Muster is created; can be adjusted manually.
    """
    class EnrollmentStatus(models.TextChoices):
        ENROLLED = 'ENROLLED', 'Enrolled'
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        EXCUSED = 'EXCUSED', 'Excused'

    muster = models.ForeignKey(
        Muster,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    reservist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='muster_enrollments',
        limit_choices_to={'role': 'RESERVIST'},
    )
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED,
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text='Reservist location when marking present',
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text='Reservist location when marking present',
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['muster', 'reservist__full_name']
        unique_together = ('muster', 'reservist')
        verbose_name_plural = 'Muster enrollments'

    def __str__(self):
        return f"{self.reservist.full_name} — {self.muster.title}"


class MusterNotification(models.Model):
    """
    Notifies a reservist when their CDC creates a muster they are enrolled in.
    read_at is set when the reservist visits the mustering list page.
    """
    reservist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='muster_notifications',
        limit_choices_to={'role': 'RESERVIST'},
    )
    muster = models.ForeignKey(
        Muster,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('reservist', 'muster')
        verbose_name_plural = 'Muster notifications'

    def __str__(self):
        return f"{self.reservist.full_name} — {self.muster.title}"
