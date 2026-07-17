from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=50)
    agreed_terms_at = models.DateTimeField(null=True, blank=True)
