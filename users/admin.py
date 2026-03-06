from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Notification


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
