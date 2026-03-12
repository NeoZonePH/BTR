from django.contrib import admin
from .models import Muster, MusterEnrollment, MusterNotification


class MusterEnrollmentInline(admin.TabularInline):
    model = MusterEnrollment
    extra = 0
    raw_id_fields = ('reservist',)


@admin.register(Muster)
class MusterAdmin(admin.ModelAdmin):
    list_display = ('title', 'muster_date', 'cdc', 'created_at')
    list_filter = ('cdc',)
    search_fields = ('title', 'location')
    inlines = (MusterEnrollmentInline,)
    raw_id_fields = ('cdc', 'created_by')


@admin.register(MusterEnrollment)
class MusterEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('muster', 'reservist', 'status', 'enrolled_at')
    list_filter = ('status', 'muster')
    search_fields = ('reservist__full_name',)
    raw_id_fields = ('muster', 'reservist')


@admin.register(MusterNotification)
class MusterNotificationAdmin(admin.ModelAdmin):
    list_display = ('reservist', 'muster', 'created_at', 'read_at')
    list_filter = ('read_at',)
    search_fields = ('reservist__full_name', 'muster__title')
    raw_id_fields = ('reservist', 'muster')
