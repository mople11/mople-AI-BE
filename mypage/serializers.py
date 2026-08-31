from rest_framework import serializers

from common.serializers import PageQuerySerializer
from courses.models import CourseProgress
from interactions.models import Bookmark
from reviews.models import Review


class MypageListQuerySerializer(PageQuerySerializer):
    pass


class ProfileSerializer(serializers.Serializer):
    nickname = serializers.CharField()
    profileImg = serializers.URLField(source="profile_img", allow_null=True)


class ProfileStatsSerializer(serializers.Serializer):
    completedCourses = serializers.IntegerField()
    stamps = serializers.IntegerField()
    reviews = serializers.IntegerField()


class ProfileSummarySerializer(serializers.Serializer):
    profile = ProfileSerializer()
    stats = ProfileStatsSerializer()


class ProfileUpdateSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=50, required=False)
    profileImg = serializers.URLField(
        source="profile_img",
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "nickname 또는 profileImg 중 하나 이상을 입력해야 합니다."
            )
        return attrs


class SavedCourseSerializer(serializers.ModelSerializer):
    courseId = serializers.CharField(source="course.id")
    name = serializers.CharField(source="course.name")

    class Meta:
        model = CourseProgress
        fields = ("courseId", "name")


class MyReviewSerializer(serializers.ModelSerializer):
    reviewId = serializers.CharField(source="id")
    targetName = serializers.CharField(source="place.name")

    class Meta:
        model = Review
        fields = ("reviewId", "targetName", "rating")


class LikedPlaceSerializer(serializers.ModelSerializer):
    placeId = serializers.CharField(source="place.id")
    name = serializers.CharField(source="place.name")

    class Meta:
        model = Bookmark
        fields = ("placeId", "name")


class MypageErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = serializers.JSONField()


class WithdrawalSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = serializers.JSONField(allow_null=True)
