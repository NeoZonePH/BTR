from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Notification, SignupAttempt


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'full_name', 'role', 'region', 'province', 'municipality', 'is_active')
    list_filter = ('role', 'region', 'is_active')
    search_fields = ('username', 'full_name', 'afpsn')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('TARGET Profile', {
            'fields': (
                'full_name', 'rank', 'afpsn',
                'region', 'province', 'municipality', 'mobile_number', 'role',
            ),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('TARGET Profile', {
            'fields': (
                'full_name', 'rank', 'afpsn',
                'region', 'province', 'municipality', 'mobile_number', 'role',
            ),
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__full_name', 'message')


@admin.register(SignupAttempt)
class SignupAttemptAdmin(admin.ModelAdmin):
    """Monitor blocked and successful signup attempts (anti-bot logging)."""
    list_display = ('ip_address', 'username', 'email', 'success', 'block_reason', 'created_at')
    list_filter = ('success', 'block_reason', 'created_at')
    search_fields = ('ip_address', 'username', 'email', 'block_reason')
    readonly_fields = ('ip_address', 'username', 'email', 'success', 'block_reason', 'created_at')
    date_hierarchy = 'created_at'
