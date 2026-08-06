from django.urls import path

from courses.views import (
    CourseCompleteView,
    CourseSaveView,
    CourseShareView,
    CourseStartView,
)


app_name = "courses"

urlpatterns = [
    path("<int:courseId>/save", CourseSaveView.as_view(), name="save"),
    path("<int:courseId>/start", CourseStartView.as_view(), name="start"),
    path("<int:courseId>/complete", CourseCompleteView.as_view(), name="complete"),
    path("<int:courseId>/share", CourseShareView.as_view(), name="share"),
]
