from django.contrib import admin
from .models import Profile

# Register your models here.


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'user', 'created_at']
    search_fields = ['display_name', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
