from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model with role-based access.

    Organizational Hierarchy:
      RESCOM (Administrator) — Reserve Command, highest authority, oversees 17 RCDGs
        └── RCDG — Regional Community Defense Group, each has its own CDCs
              └── CDC — Community Defense Center, under their respective RCDG

    Civilian Counterparts (created by CDC):
      PDRRMO — Provincial Disaster Risk Reduction & Management Office
      MDRRMO — Municipal Disaster Risk Reduction & Management Office

    Field Personnel:
      RESERVIST — Signs up publicly, must be approved by their CDC before login

    Account creation rules:
      - RESCOM creates RCDG accounts
      - RCDG creates CDC accounts
      - CDC creates PDRRMO & MDRRMO accounts
      - CDC approves Reservist sign-ups
    """

    class Role(models.TextChoices):
        RESERVIST = 'RESERVIST', 'Reservist'
        CDC = 'CDC', 'Community Defense Center'
        RCDG = 'RCDG', 'Regional Community Defense Group'
        RESCOM = 'RESCOM', 'Reserve Command (Administrator)'
        PDRRMO = 'PDRRMO', 'Provincial DRRMO'
        MDRRMO = 'MDRRMO', 'Municipal DRRMO'

    full_name = models.CharField(max_length=255)
    rank = models.CharField(max_length=100, blank=True)
    afpsn = models.CharField(max_length=100, blank=True, verbose_name='AFPSN')
    region = models.CharField(max_length=255, blank=True)
    province = models.CharField(max_length=255, blank=True)
    municipality = models.CharField(max_length=255, blank=True)
    barangay = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RESERVIST)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    @property
    def ref_latitude(self):
        """Return reference latitude if RCDG/CDC, else User latitude."""
        if self.role == self.Role.RCDG and self.assigned_rcdg and self.assigned_rcdg.latitude:
            return float(self.assigned_rcdg.latitude)
        if self.role == self.Role.CDC and self.assigned_cdc and self.assigned_cdc.latitude:
            return float(self.assigned_cdc.latitude)
        return self.latitude

    @property
    def ref_longitude(self):
        """Return reference longitude if RCDG/CDC, else User longitude."""
        if self.role == self.Role.RCDG and self.assigned_rcdg and self.assigned_rcdg.longitude:
            return float(self.assigned_rcdg.longitude)
        if self.role == self.Role.CDC and self.assigned_cdc and self.assigned_cdc.longitude:
            return float(self.assigned_cdc.longitude)
        return self.longitude

    # Organizational hierarchy links (reference models)
    assigned_rcdg = models.ForeignKey(
        'references.Rcdg', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users',
        help_text='The RCDG this user belongs to',
    )
    assigned_cdc = models.ForeignKey(
        'references.Cdc', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users',
        help_text='The CDC this user belongs to',
    )

    # Approval workflow
    is_approved = models.BooleanField(
        default=True,
        help_text='Reservists default to False until CDC approves them',
    )

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    @property
    def is_admin(self):
        """RESCOM is the system administrator."""
        return self.role == self.Role.RESCOM

    @property
    def dashboard_url(self):
        """Return the dashboard URL based on user role."""
        role_urls = {
            self.Role.RESERVIST: '/reservist/dashboard/',
            self.Role.RESCOM: '/rescom/dashboard/',
            self.Role.RCDG: '/rcdg/dashboard/',
            self.Role.CDC: '/cdc/dashboard/',
            self.Role.PDRRMO: '/pdrrmo/dashboard/',
            self.Role.MDRRMO: '/mdrrmo/dashboard/',
        }
        return role_urls.get(self.role, '/reservist/dashboard/')


class Notification(models.Model):
    """Notification model for incident alerts."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    incident = models.ForeignKey(
        'reservist_portal.Incident', on_delete=models.CASCADE,
        related_name='notifications', null=True, blank=True,
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.full_name}: {self.message[:50]}"


class ActivityLog(models.Model):
    """Log of actions performed by Reservists, trackable by RESCOM."""

    class Action(models.TextChoices):
        LOGIN = 'LOGIN', 'Logged In'
        LOGOUT = 'LOGOUT', 'Logged Out'
        CREATE_INCIDENT = 'CREATE_INCIDENT', 'Submitted Incident'
        EDIT_INCIDENT = 'EDIT_INCIDENT', 'Edited Incident'
        DELETE_INCIDENT = 'DELETE_INCIDENT', 'Deleted Incident'
        RESTORE_INCIDENT = 'RESTORE_INCIDENT', 'Restored Incident'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=50, choices=Action.choices)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.get_action_display()} at {self.created_at}"
