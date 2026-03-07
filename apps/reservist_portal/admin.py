from django.contrib import admin
from .models import Incident, AISummary


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('title', 'incident_type', 'status', 'reservist', 'region', 'created_at')
    list_filter = ('incident_type', 'status', 'region', 'created_at')
    search_fields = ('title', 'description', 'reservist__full_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AISummary)
class AISummaryAdmin(admin.ModelAdmin):
    list_display = ('period', 'period_start', 'period_end', 'created_at')
    list_filter = ('period',)
    readonly_fields = ('created_at',)
