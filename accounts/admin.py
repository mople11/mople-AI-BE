from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import EmailVerificationCode, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("추가 정보", {"fields": ("nickname", "agreed_terms_at")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("추가 정보", {"fields": ("email", "nickname")}),
    )
    list_display = (*UserAdmin.list_display, "nickname", "email")


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ("email", "purpose", "expires_at", "is_used")
    list_filter = ("purpose", "is_used")
    search_fields = ("email",)
    readonly_fields = ("code",)

    def has_add_permission(self, request):
        return False
