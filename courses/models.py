from django.db import models


class Course(models.Model):
    class Status(models.TextChoices):
        TEMP = "TEMP", "임시"
        SAVED = "SAVED", "저장"

    owner = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=255)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    recommend_reason = models.TextField(blank=True)
    mood = models.CharField(max_length=50, blank=True)
    companion_type = models.CharField(max_length=50, blank=True)
    transport_type = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.TEMP,
    )


class CoursePlace(models.Model):
    course = models.ForeignKey(
        Course,
        related_name="places",
        on_delete=models.CASCADE,
    )
    place = models.ForeignKey("places.TouristSpot", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()
    travel_time_from_prev = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"],
                name="courses_courseplace_course_order_unique",
            ),
        ]


class CourseProgress(models.Model):
    class Status(models.TextChoices):
        SAVED = "SAVED", "저장"
        IN_PROGRESS = "IN_PROGRESS", "진행 중"
        COMPLETED = "COMPLETED", "완료"

    user = models.ForeignKey(
        "accounts.User",
        related_name="course_progresses",
        on_delete=models.CASCADE,
    )
    course = models.ForeignKey(
        Course,
        related_name="progresses",
        on_delete=models.CASCADE,
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                name="courses_courseprogress_user_course_unique",
            ),
        ]
