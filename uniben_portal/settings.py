"""
Django settings for uniben_portal project.
Clean version (Render + Cloudinary + PostgreSQL)
"""

import os
import sys
from pathlib import Path
import dj_database_url
import cloudinary
import cloudinary.uploader
import cloudinary.api

# =========================
# 📁 BASE DIRECTORY
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent


# =========================
# 🔐 SECURITY SETTINGS
# =========================
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-secret")
DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
ALLOWED_HOSTS += ["skholar.onrender.com"]


# =========================
# 🧩 INSTALLED APPS
# =========================
INSTALLED_APPS = [
    # Django Core Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-Party Apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'cloudinary',
    'cloudinary_storage',
    'django_filters',

    # Local Apps
    'accounts',
    'api',
    'core',
    'cbt',
    'events',
    'materials.apps.MaterialsConfig',
    'news',
    'notifications',
]


# =========================
# ⚙️ MIDDLEWARE
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =========================
# 🧭 URL + WSGI
# =========================
ROOT_URLCONF = "uniben_portal.urls"
WSGI_APPLICATION = "uniben_portal.wsgi.application"


# =========================
# 🎨 TEMPLATES
# =========================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# =========================
# 🗄️ DATABASE
# =========================
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL")
    )
}

# Local fallback (only used if DATABASE_URL not set)
if not os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "uniben_db",
            "USER": "uniben_user",
            "PASSWORD": "problemsolvers",
            "HOST": "localhost",
            "PORT": "5432",
        }
    }


# =========================
# 🧾 AUTH & PERMISSIONS
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]


# =========================
# 🌍 CORS + REST FRAMEWORK
# =========================
CORS_ALLOW_ALL_ORIGINS = True  # ⚠️ Only for dev — restrict later for production!

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
}


# =========================
# 📦 STATIC & MEDIA (Render)
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# =========================
# 🕒 LOCALIZATION
# =========================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =========================
# 🔔 NOTIFICATIONS / OTHERS
# =========================
ONESIGNAL_APP_ID = "34ebccc1-0042-4256-ad0e-0d2dd167da43"
ONESIGNAL_REST_API_KEY = "os_v2_app_gtv4zqiaijbfnliobuw5cz62ionoo2yiekbu43fnqodkxoc6bsjrfloge2aeomukcdrtsvfvxrfru2vzj5pyi5xkv4eelnwwf4lrc5q"

DEEPSEEK_API_KEY = "your_actual_deepseek_api_key_here"


# =========================
# 🪵 LOGGING
# =========================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler", "stream": sys.stdout},
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}


# =========================
# ☁️ CLOUDINARY CONFIGURATION
# =========================
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dsrepnl1c',
    'API_KEY': '817612193932414',
    'API_SECRET': 'IPkq5LMtmfPV3isOqnQRhUp63QU',
}

cloudinary.config(
    cloud_name='dsrepnl1c',
    api_key='817612193932414',
    api_secret='IPkq5LMtmfPV3isOqnQRhUp63QU',
    secure=True
)

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

print("✅ Cloudinary successfully configured for:", CLOUDINARY_STORAGE['CLOUD_NAME'])

# =========================
# ⚙️ FORCE DJANGO TO USE CLOUDINARY STORAGE
# =========================
from importlib import import_module
from django.core.files import storage as storage_module

try:
    # Clear cached storages if Django 5.1+ (they cause fallback to FileSystem)
    if hasattr(storage_module, 'storages'):
        storage_module.storages._storages.clear()

    # Manually force default_storage to Cloudinary
    module_path, class_name = DEFAULT_FILE_STORAGE.rsplit('.', 1)
    storage_class = getattr(import_module(module_path), class_name)
    storage_module.default_storage = storage_class()

    print("✅ Default storage manually switched to:", storage_module.default_storage.__class__)
except Exception as e:
    print("⚠️ Cloudinary setup issue:", e)
