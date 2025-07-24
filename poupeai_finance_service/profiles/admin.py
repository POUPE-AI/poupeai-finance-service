from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'email', 'first_name', 'last_name', 'is_deactivated', 'created_at')
    search_fields = ('user_id', 'email', 'first_name', 'last_name')
    list_filter = ('is_deactivated', 'created_at', 'deactivation_scheduled_at')
    readonly_fields = ('user_id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Keycloak Information', {
            'fields': ('user_id', 'email', 'first_name', 'last_name')
        }),
        ('Status', {
            'fields': ('is_deactivated', 'deactivation_scheduled_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
