from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=50)
    agreed_terms_at = models.DateTimeField(null=True, blank=True)


class EmailVerificationCode(models.Model):
    class Purpose(models.TextChoices):
        SIGNUP = "signup", "회원가입"
        PASSWORD_RESET = "password_reset", "비밀번호 재설정"

    email = models.CharField(max_length=254)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(
                fields=["email", "purpose", "code", "is_used"],
                name="accounts_evc_lookup_idx",
            ),
            models.Index(
                fields=["is_used", "expires_at"],
                name="accounts_evc_expiry_idx",
            ),
        ]
