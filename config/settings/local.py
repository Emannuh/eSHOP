"""Local development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True

INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]  # noqa: F405

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

# Simpler static storage for dev
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Allow all hosts locally
ALLOWED_HOSTS = ["*"]

# Fast password hasher for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Show emails in console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
