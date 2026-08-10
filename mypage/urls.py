from django.urls import path

from mypage.views import MeView, MyCoursesView, MyLikesView, MyReviewsView


app_name = "mypage"

urlpatterns = [
    path("api/v1/users/me", MeView.as_view(), name="me"),
    path("api/v1/users/me/courses", MyCoursesView.as_view(), name="courses"),
    path("api/v1/users/me/reviews", MyReviewsView.as_view(), name="reviews"),
    path("api/v1/users/me/likes", MyLikesView.as_view(), name="likes"),
]
