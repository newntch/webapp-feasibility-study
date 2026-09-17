import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-development-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin
]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.study",
]
MIDDLEWARE = [
    "config.middleware.NoStoreMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = []
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.auth.EmailBackend"]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.BCryptPasswordHasher",
]
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = "cohort_lens_session"
SESSION_COOKIE_AGE = 28800
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE


def pg_database(prefix, fallback):
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get(f"{prefix}_DB_NAME", fallback),
        "USER": os.environ.get(f"{prefix}_DB_USER", "postgres"),
        "PASSWORD": os.environ.get(f"{prefix}_DB_PASSWORD", ""),
        "HOST": os.environ.get(f"{prefix}_DB_HOST", "localhost"),
        "PORT": os.environ.get(f"{prefix}_DB_PORT", "5432"),
        "CONN_HEALTH_CHECKS": True,
    }


DATABASES = {
    "default": pg_database("APP", "application_db"),
    "clinical": pg_database("CLINICAL", "clinical_db"),
}
DATABASES["clinical"]["OPTIONS"] = {
    "options": "-c max_parallel_workers_per_gather=0 -c statement_timeout=300000"
}
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
STATIC_URL = "/assets/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "public" / "assets"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("SMTP_HOST", "")
EMAIL_PORT = int(os.environ.get("SMTP_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("SMTP_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASS", "")
EMAIL_USE_TLS = os.environ.get("SMTP_SECURE", "0") != "1"
EMAIL_USE_SSL = os.environ.get("SMTP_SECURE", "0") == "1"
DEFAULT_FROM_EMAIL = os.environ.get("SMTP_FROM", EMAIL_HOST_USER)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")
GOOGLE_ALLOWED_EMAILS = {
    email.strip()
    for email in os.environ.get("GOOGLE_ALLOWED_EMAILS", "").lower().split(",")
    if email.strip()
}
CLINICAL_DATASET_VERSION = os.environ.get("CLINICAL_DATASET_VERSION", "ehrshot-omop-v5.3.1")
