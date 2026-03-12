"""
Django settings for TARGET project.
Tactical Automated Response & Geolocation Emergency Tracker
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', '10rcdgrescompa.com']

# Security Headers (Security Engineer Guidelines)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap5',
    'channels',
    'disposable_email_checker',  # Anti-bot: block disposable/temporary email domains
    # Local apps
    'users.apps.UsersConfig',
    'references.apps.ReferencesConfig',
    'apps.reservist_portal.apps.ReservistPortalConfig',
    'apps.rescom_portal.apps.RescomPortalConfig',
    'apps.rcdg_portal.apps.RcdgPortalConfig',
    'apps.cdc_portal.apps.CdcPortalConfig',
    'apps.pdrrmo_portal.apps.PdrrmoPortalConfig',
    'apps.mdrrmo_portal.apps.MdrrmoPortalConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'target.middleware.ManilaTimezoneMiddleware',  # Always use Asia/Manila (Philippines) local time
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'target.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'users.context_processors.notifications_processor',
                'apps.cdc_portal.context_processors.reservist_approval_notification',
                'apps.cdc_portal.context_processors.muster_notification_for_reservist',
            ],
        },
    },
]

WSGI_APPLICATION = 'target.wsgi.application'
ASGI_APPLICATION = 'target.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(os.getenv('REDIS_HOST', '127.0.0.1'), int(os.getenv('REDIS_PORT', 6379)))],
        },
    },
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'target_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'root'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Auth
AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization — application uses Philippines local time everywhere
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'  # Philippines; all datetimes displayed and interpreted in this zone
USE_I18N = True
USE_TZ = True  # Store UTC in DB; ManilaTimezoneMiddleware activates Asia/Manila per request

# Static files
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Cache (used by django-ratelimit for signup rate limiting)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Anti-bot: signup rate limits (3/min and 20/h enforced in users.views.register_view)
# django-ratelimit uses the default cache above

# DRF
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

# OpenRouter AI
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
OPENROUTER_MODEL = 'openai/gpt-oss-120b:free'

# SMS
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'console')
SMS_API_KEY = os.getenv('SMS_API_KEY', '')
SMS_API_SECRET = os.getenv('SMS_API_SECRET', '')

# Django Channels
ASGI_APPLICATION = 'target.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

CSRF_TRUSTED_ORIGINS = [
    'https://10rcdgrescompa.com',
    'https://www.10rcdgrescompa.com',
]
