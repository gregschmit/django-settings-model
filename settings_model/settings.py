"""
This module is designed to do 2 things:

 1. Provide an interface (``get_setting``) for getting settings from
    ``django.conf.settings`` with settings in this file being the fallback default.
 2. Provide enough settings for this app to run as a standalone project.
"""

from django.conf import settings
import os
import sys


def get_setting(name):
    """
    Hook for getting Django settings and using properties of this file as the default.
    """
    me = sys.modules[__name__]
    return getattr(settings, name, getattr(me, name, None))


# app-specific settings
SETTINGS_MODEL_REBOOT_FILES = []


# standalone settings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = "not-a-very-good-secret"
DEBUG = True
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "settings_model",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "settings_model.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "settings_model.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"detail": {"format": "%(name)s [%(levelname)s]: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "detail"}},
    "loggers": {"": {"handlers": ["console"], "level": "DEBUG", "propagate": True}},
}
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL = "/static/"
APPEND_SLASH = True

# local development settings
try:
    from .local_settings import *
except ImportError:
    pass

# local config settings
try:
    from settings_model.config import *
except ImportError:
    pass
