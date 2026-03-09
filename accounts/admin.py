from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from django.utils.html import format_html

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Additional Info", {"fields": ("role", "bio")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("role",)}),
    )

    @admin.display(description="Full Name", ordering="first_name")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    # User listing page columns, filters and search queries
    list_display = ("username", "full_name", "role", "email", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")