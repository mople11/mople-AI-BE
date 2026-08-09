from django.db import models


class Bookmark(models.Model):
    user = models.ForeignKey(
        "accounts.User", related_name="bookmarks", on_delete=models.CASCADE
    )
    place = models.ForeignKey(
        "places.TouristSpot", related_name="bookmarks", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "place"],
                name="interactions_bookmark_user_place_unique",
            )
        ]
