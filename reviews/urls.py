from django.urls import path

from reviews.views import (
    ReviewCollectionView,
    ReviewHelpfulView,
    ReviewReportView,
    ReviewSummaryView,
)


app_name = "reviews"

urlpatterns = [
    path("api/v1/reviews", ReviewCollectionView.as_view(), name="collection"),
    path("api/v1/reviews/summary", ReviewSummaryView.as_view(), name="summary"),
    path("api/v1/reviews/<int:reviewId>/helpful", ReviewHelpfulView.as_view(), name="helpful"),
    path("api/v1/reviews/<int:reviewId>/report", ReviewReportView.as_view(), name="report"),
]
