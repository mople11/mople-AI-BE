from .base import *  # noqa: F403
from .base import env


SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = [host.strip() for host in env.list("DJANGO_ALLOWED_HOSTS")]
