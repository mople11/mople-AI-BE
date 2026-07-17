from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("추가 정보", {"fields": ("nickname", "agreed_terms_at")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("추가 정보", {"fields": ("email", "nickname")}),
    )
    list_display = (*UserAdmin.list_display, "nickname", "email")
