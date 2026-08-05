from django.db import models


class TouristSpot(models.Model):
    class Category(models.TextChoices):
        ATTRACTION = "ATTRACTION", "관광지"
        RESTAURANT = "RESTAURANT", "맛집"
        LODGING = "LODGING", "숙박"
        FESTIVAL = "FESTIVAL", "축제"

    content_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices)
    address = models.CharField(max_length=500)
    description = models.TextField()
    hours = models.CharField(max_length=500, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    sigungu = models.CharField(max_length=100, blank=True)
    parking_available = models.BooleanField(null=True, blank=True)
    synced_at = models.DateTimeField()

    def __str__(self):
        return self.name


class TouristSpotImage(models.Model):
    spot = models.ForeignKey(
        TouristSpot, related_name="images", on_delete=models.CASCADE
    )
    image_url = models.URLField(max_length=1000)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

