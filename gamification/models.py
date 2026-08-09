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


class HiddenCourse(models.Model):
    class Rarity(models.TextChoices):
        LEGENDARY = "LEGENDARY", "LEGENDARY"
        RARE = "RARE", "RARE"
        UNCOMMON = "UNCOMMON", "UNCOMMON"
        COMMON = "COMMON", "COMMON"

    course = models.OneToOneField("courses.Course", on_delete=models.CASCADE)
    rarity = models.CharField(max_length=9, choices=Rarity.choices)
    unlock_condition = models.TextField(blank=True)


class UserHiddenCourseUnlock(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        related_name="hidden_course_unlocks",
        on_delete=models.CASCADE,
    )
    hidden_course = models.ForeignKey(
        HiddenCourse,
        related_name="unlocks",
        on_delete=models.CASCADE,
    )
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "hidden_course"],
                name="gamification_unlock_user_hidden_course_unique",
            )
        ]


class CompletionCard(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        related_name="completion_cards",
        on_delete=models.CASCADE,
    )
    course = models.ForeignKey(
        "courses.Course",
        related_name="completion_cards",
        on_delete=models.CASCADE,
    )
    user_photo = models.URLField(null=True, blank=True)
    card_image_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                name="gamification_card_user_course_unique",
            )
        ]
