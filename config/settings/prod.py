from .base import *  # noqa: F403
from .base import env


SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = [host.strip() for host in env.list("DJANGO_ALLOWED_HOSTS")]
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in env.list("CORS_ALLOWED_ORIGINS", default=[])
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in env.list("CSRF_TRUSTED_ORIGINS", default=[])
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
