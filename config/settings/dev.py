from .base import *  # noqa: F403
from .base import env


SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me-in-env")
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
