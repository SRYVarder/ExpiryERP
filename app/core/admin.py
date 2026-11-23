
# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    # Columns displayed in the users list
    list_display = (
        "username",
        "email",
        "role",
        "is_staff",
        "is_active",
        "is_superuser",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_active",
        "is_superuser",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("username",)

    # Fields available when editing an existing user
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Information", {
            "fields": ("first_name", "last_name", "email")
        }),
        ("Business Access", {
            "fields": ("role", "branches", "last_branch")
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Important Dates", {
            "fields": ("last_login", "date_joined")
        }),
    )

    # Fields available when creating a new user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "password1",
                "password2",
                "first_name",
                "last_name",
                "role",
                "branches",
                "is_active",
                "is_staff",
            ),
        }),
    )

    filter_horizontal = ("groups", "user_permissions", "branches")
# Register your models here.
