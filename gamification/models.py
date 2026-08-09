from django.db import models

from places.tourist_congestion import SIGUNGU_NAME_TO_CODE


CITY_CODE_CHOICES = [(code, name) for name, code in SIGUNGU_NAME_TO_CODE.items()]


class Stamp(models.Model):
    user = models.ForeignKey(
        "accounts.User", related_name="stamps", on_delete=models.CASCADE
    )
    city_code = models.CharField(max_length=5, choices=CITY_CODE_CHOICES)
    acquired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "city_code"],
                name="gamification_stamp_user_city_code_unique",
            )
        ]
