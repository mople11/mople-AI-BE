from django.urls import path

from courses.views import (
    CourseCompleteView,
    CourseSaveView,
    CourseShareView,
    CourseStartView,
)


app_name = "courses"

urlpatterns = [
    path("<int:course_id>/save", CourseSaveView.as_view(), name="save"),
    path("<int:course_id>/start", CourseStartView.as_view(), name="start"),
    path("<int:course_id>/complete", CourseCompleteView.as_view(), name="complete"),
    path("<int:course_id>/share", CourseShareView.as_view(), name="share"),
]
