from django.conf import settings
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from common.exceptions import ApiError, ErrorCode


def verify_google_id_token(oauth_token: str) -> dict:
    try:
        payload = id_token.verify_oauth2_token(
            oauth_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except (ValueError, GoogleAuthError) as exc:
        raise ApiError(ErrorCode.OAUTH_FAILED) from exc

    provider_id = payload.get("sub")
    email = payload.get("email")
    if (
        not isinstance(provider_id, str)
        or not provider_id
        or not isinstance(email, str)
        or not email
        or payload.get("email_verified") is not True
    ):
        raise ApiError(ErrorCode.OAUTH_FAILED)

    name = payload.get("name")
    return {
        "provider_id": provider_id,
        "email": email,
        "nickname": name if isinstance(name, str) and name else email.split("@")[0],
    }
