import requests

from common.exceptions import ApiError, ErrorCode

KAKAO_USER_ME_URL = "https://kapi.kakao.com/v2/user/me"
PLACEHOLDER_EMAIL_DOMAIN = "users.eodiganam.local"


def verify_kakao_token(oauth_token: str) -> dict:
    try:
        response = requests.get(
            KAKAO_USER_ME_URL,
            headers={"Authorization": f"Bearer {oauth_token}"},
            timeout=5,
        )
    except requests.RequestException as exc:
        raise ApiError(ErrorCode.OAUTH_FAILED) from exc

    if response.status_code != 200:
        raise ApiError(ErrorCode.OAUTH_FAILED)

    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError(ErrorCode.OAUTH_FAILED) from exc

    if not isinstance(payload, dict) or payload.get("id") is None:
        raise ApiError(ErrorCode.OAUTH_FAILED)

    provider_id = str(payload["id"])
    kakao_account = payload.get("kakao_account") or {}
    if not isinstance(kakao_account, dict):
        raise ApiError(ErrorCode.OAUTH_FAILED)

    profile = kakao_account.get("profile") or {}
    if not isinstance(profile, dict):
        raise ApiError(ErrorCode.OAUTH_FAILED)

    kakao_email = kakao_account.get("email")
    email = kakao_email if isinstance(kakao_email, str) and kakao_email else (
        f"kakao_{provider_id}@{PLACEHOLDER_EMAIL_DOMAIN}"
    )
    kakao_nickname = profile.get("nickname")
    nickname = (
        kakao_nickname
        if isinstance(kakao_nickname, str) and kakao_nickname
        else f"카카오사용자{provider_id[-6:]}"
    )

    return {
        "provider_id": provider_id,
        "email": email,
        "nickname": nickname,
    }
