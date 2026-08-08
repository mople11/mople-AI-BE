from django.db import transaction
from django.db.models import Prefetch

from common.exceptions import ApiError, ErrorCode
from places.models import TouristSpot
from reviews.models import Review, ReviewPhoto, ReviewReaction, ReviewReport


def create_review(*, user, target_id, rating, text, photos, visit_date, visit_weather) -> Review:
    if rating is None:
        raise ApiError(ErrorCode.RATING_REQUIRED)
    try:
        place = TouristSpot.objects.get(pk=target_id)
    except (TouristSpot.DoesNotExist, ValueError, TypeError) as exc:
        raise ApiError(ErrorCode.PLACE_NOT_FOUND) from exc

    with transaction.atomic():
        review = Review.objects.create(
            user=user, place=place, rating=rating, content=text,
            visit_date=visit_date, weather_at_visit=visit_weather,
        )
        ReviewPhoto.objects.bulk_create([
            ReviewPhoto(review=review, image_url=url, display_order=index)
            for index, url in enumerate(photos)
        ])
    return review


def list_reviews(*, target_id, sort):
    order_by = ("-rating", "-id") if sort == "rating" else ("-id",)
    return (
        Review.objects.filter(place_id=target_id)
        .select_related("user")
        .prefetch_related(Prefetch("photos", queryset=ReviewPhoto.objects.order_by("display_order", "id")))
        .order_by(*order_by)
    )


def _get_review_for_update(review_id) -> Review:
    try:
        return Review.objects.select_for_update().get(pk=review_id)
    except (Review.DoesNotExist, ValueError, TypeError) as exc:
        raise ApiError(ErrorCode.REVIEW_NOT_FOUND) from exc


@transaction.atomic
def toggle_review_helpful(*, review_id, user) -> int:
    review = _get_review_for_update(review_id)
    reaction = ReviewReaction.objects.filter(
        review=review, user=user,
        reaction_type=ReviewReaction.ReactionType.HELPFUL,
    ).first()
    if reaction:
        reaction.delete()
        review.like_count = max(0, review.like_count - 1)
    else:
        ReviewReaction.objects.create(
            review=review, user=user,
            reaction_type=ReviewReaction.ReactionType.HELPFUL,
        )
        review.like_count += 1
    review.save(update_fields=["like_count"])
    return review.like_count


def create_report(*, review_id, user, reason) -> ReviewReport:
    try:
        review = Review.objects.get(pk=review_id)
    except (Review.DoesNotExist, ValueError, TypeError) as exc:
        raise ApiError(ErrorCode.REVIEW_NOT_FOUND) from exc
    report, _ = ReviewReport.objects.get_or_create(
        review=review, user=user, defaults={"reason": reason}
    )
    return report
