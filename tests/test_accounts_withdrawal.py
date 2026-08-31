from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import EmailVerificationCode, User
from accounts.services import withdraw_user
from common.exceptions import ApiError, ErrorCode
from courses.models import Course, CourseProgress
from gamification.models import CompletionCard, Stamp
from interactions.models import Bookmark
from places.models import TouristSpot
from reviews.models import Review, ReviewReaction, ReviewReport


WITHDRAW_URL = "/api/v1/users/me"
PASSWORD = "safe-password-123"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="traveler",
        email="traveler@example.com",
        nickname="여행자",
        password=PASSWORD,
    )


def authenticated_tokens(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def test_password_user_withdrawal_anonymizes_and_invalidates_tokens(api_client, user):
    access, refresh = authenticated_tokens(user)

    response = api_client.delete(
        WITHDRAW_URL,
        {"password": PASSWORD},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )

    assert response.status_code == 200
    assert response.data == {"success": True, "data": None, "error": None}
    user.refresh_from_db()
    assert user.is_active is False
    assert user.withdrawn_at is not None
    assert user.username == f"withdrawn_{user.pk}"
    assert user.email == f"withdrawn+{user.pk}@withdrawn.eodiganam.local"
    assert user.nickname == f"탈퇴한 사용자_{user.pk}"
    assert user.provider is None
    assert user.provider_id is None
    assert user.has_usable_password() is False
    assert BlacklistedToken.objects.filter(token__token=refresh).exists()

    authenticated_response = api_client.get(
        WITHDRAW_URL,
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )
    assert authenticated_response.status_code == 401
    assert authenticated_response.data["error"]["code"] == "AUTH_401"


def test_password_user_withdrawal_rejects_wrong_password(api_client, user):
    access, _ = authenticated_tokens(user)

    response = api_client.delete(
        WITHDRAW_URL,
        {"password": "wrong-password"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "PASSWORD_MISMATCH"
    user.refresh_from_db()
    assert user.is_active is True
    assert user.withdrawn_at is None


def test_social_user_withdrawal_succeeds_without_password(api_client, db):
    social_user = User(
        username="google_123",
        email="social@example.com",
        nickname="소셜여행자",
        provider=User.Provider.GOOGLE,
        provider_id="123",
    )
    social_user.set_unusable_password()
    social_user.save()
    access, _ = authenticated_tokens(social_user)

    response = api_client.delete(
        WITHDRAW_URL,
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )

    assert response.status_code == 200
    social_user.refresh_from_db()
    assert social_user.provider is None
    assert social_user.provider_id is None


def test_withdrawal_allows_same_identity_to_register_again(user):
    withdraw_user(user=user, password=PASSWORD)

    replacement = User.objects.create_user(
        username="traveler",
        email="traveler@example.com",
        nickname="여행자",
        password=PASSWORD,
    )

    assert replacement.pk != user.pk


@patch("accounts.views.verify_google_id_token")
def test_withdrawn_social_identity_can_join_again(mock_verify, api_client, db):
    social_user = User(
        username="google_123",
        email="social@example.com",
        nickname="소셜여행자",
        provider=User.Provider.GOOGLE,
        provider_id="123",
    )
    social_user.set_unusable_password()
    social_user.save()
    withdraw_user(user=social_user)
    mock_verify.return_value = {
        "provider_id": "123",
        "email": "social@example.com",
        "nickname": "소셜여행자",
    }

    response = api_client.post(
        "/api/v1/auth/login/social",
        {"provider": "google", "oauthToken": "valid-token"},
        format="json",
    )

    assert response.status_code == 200
    new_user = User.objects.get(provider="google", provider_id="123")
    assert new_user.pk != social_user.pk
    assert new_user.is_active is True


def test_withdrawn_user_cannot_log_in_and_invalid_social_token_fails(api_client, user):
    withdraw_user(user=user, password=PASSWORD)

    login_response = api_client.post(
        "/api/v1/auth/login",
        {"id": "traveler", "pw": PASSWORD},
        format="json",
    )
    assert login_response.status_code == 401
    assert login_response.data["error"]["code"] == "INVALID_CREDENTIALS"

    with patch("accounts.views.verify_google_id_token") as verify:
        verify.side_effect = ApiError(ErrorCode.OAUTH_FAILED)
        social_response = api_client.post(
            "/api/v1/auth/login/social",
            {"provider": "google", "oauthToken": "old-token"},
            format="json",
        )
    assert social_response.status_code == 401
    assert social_response.data["error"]["code"] == "OAUTH_FAILED"


def test_withdrawal_cleans_private_data_and_preserves_public_content(user):
    place = TouristSpot.objects.create(
        content_id="withdraw-place",
        name="탈퇴 테스트 장소",
        category=TouristSpot.Category.ATTRACTION,
        address="전남",
        description="설명",
        latitude="34.0000000",
        longitude="126.0000000",
        synced_at=timezone.now(),
    )
    course = Course.objects.create(owner=user, name="유지되는 코스")
    CourseProgress.objects.create(
        user=user,
        course=course,
        status=CourseProgress.Status.SAVED,
    )
    Bookmark.objects.create(user=user, place=place)
    Stamp.objects.create(user=user, city_code="1")
    CompletionCard.objects.create(
        user=user,
        course=course,
        card_image_url="https://example.com/card.jpg",
    )
    review = Review.objects.create(
        user=user,
        place=place,
        rating=5,
        content="유지되는 후기",
        like_count=1,
    )
    reacted_review = Review.objects.create(
        user=User.objects.create_user(
            username="author",
            email="author@example.com",
            nickname="작성자",
            password=PASSWORD,
        ),
        place=place,
        rating=4,
        content="반응 대상 후기",
        like_count=1,
    )
    ReviewReaction.objects.create(
        user=user,
        review=reacted_review,
        reaction_type=ReviewReaction.ReactionType.HELPFUL,
    )
    ReviewReport.objects.create(user=user, review=reacted_review, reason="신고")
    EmailVerificationCode.objects.create(
        email=user.email,
        code="123456",
        purpose=EmailVerificationCode.Purpose.SIGNUP,
        expires_at=timezone.now(),
    )

    withdraw_user(user=user, password=PASSWORD)

    assert not Bookmark.objects.filter(user=user).exists()
    assert not CourseProgress.objects.filter(user=user).exists()
    assert not Stamp.objects.filter(user=user).exists()
    assert not CompletionCard.objects.filter(user=user).exists()
    assert not ReviewReaction.objects.filter(user=user).exists()
    assert not ReviewReport.objects.filter(user=user).exists()
    assert not EmailVerificationCode.objects.filter(email="traveler@example.com").exists()
    review.refresh_from_db()
    reacted_review.refresh_from_db()
    course.refresh_from_db()
    assert review.user_id == user.pk
    assert review.user.nickname == f"탈퇴한 사용자_{user.pk}"
    assert reacted_review.like_count == 0
    assert course.owner_id == user.pk


@pytest.mark.django_db(transaction=True)
def test_concurrent_withdrawal_detects_already_withdrawn_account():
    user = User.objects.create_user(
        username="concurrent-traveler",
        email="concurrent@example.com",
        nickname="동시탈퇴자",
        password=PASSWORD,
    )
    barrier = Barrier(2)

    def attempt_withdrawal():
        close_old_connections()
        try:
            barrier.wait()
            withdraw_user(user=user, password=PASSWORD)
            return None
        except ApiError as exc:
            return exc.error_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt_withdrawal(), range(2)))

    assert results.count(None) == 1
    assert results.count(ErrorCode.ACCOUNT_ALREADY_WITHDRAWN) == 1


def test_withdrawal_requires_authentication(api_client, db):
    response = api_client.delete(WITHDRAW_URL, format="json")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "AUTH_401"
