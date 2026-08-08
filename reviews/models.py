from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Review(models.Model):
    user = models.ForeignKey(
        "accounts.User", related_name="reviews", on_delete=models.CASCADE
    )
    place = models.ForeignKey(
        "places.TouristSpot", related_name="reviews", on_delete=models.CASCADE
    )
    course = models.ForeignKey(
        "courses.Course",
        related_name="reviews",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    content = models.TextField()
    visit_date = models.DateField(null=True, blank=True)
    weather_at_visit = models.CharField(max_length=100, blank=True)
    like_count = models.PositiveIntegerField(default=0)


class ReviewPhoto(models.Model):
    review = models.ForeignKey(Review, related_name="photos", on_delete=models.CASCADE)
    image_url = models.URLField(max_length=1000)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]


class ReviewReaction(models.Model):
    class ReactionType(models.TextChoices):
        HELPFUL = "HELPFUL", "도움돼요"

    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=20, choices=ReactionType.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["review", "user"],
                name="reviews_reaction_review_user_unique",
            )
        ]


class ReviewReport(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["review", "user"],
                name="reviews_report_review_user_unique",
            )
        ]
