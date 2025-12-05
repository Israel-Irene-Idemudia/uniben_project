
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
from decouple import config
from datetime import timedelta

# =========================
# 📁 BASE DIRECTORY
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent


# =========================
# 🔐 SECURITY SETTINGS
# =========================
SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-secret")
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")
ALLOWED_HOSTS += ["skholar.onrender.com", "skholar.site", "www.skholar.site"]


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
    'anymail',
    'django_rest_passwordreset',

    # Local Apps
    'accounts',
    'api',
    'core',
    'cbt',
    'course',
    'events',
    'materials.apps.MaterialsConfig',
    'news',
    'notifications',
    'aiassistant',
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
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
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
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}

# Local fallback (only used if DATABASE_URL not set)
if not config('DATABASE_URL', default=None):
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
#  JWT & REST FRAMEWORK
# =========================
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default="").split(',')
CORS_ALLOWED_ORIGINS += [
    "https://skholar.site",
    "https://www.skholar.site",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False, # Keep it simple
    'BLACKLIST_AFTER_ROTATION': True,
}

# =========================
# 📦 STATIC & MEDIA (Render)
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# =========================
# ✉️ EMAIL CONFIGURATION (ZOHO SMTP)
# =========================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.zoho.com"
EMAIL_PORT = 465
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Skholar <theproblemsolvers@skholar.site>")


# =========================
# 🔑 PASSWORD RESET CONFIGURATION
# =========================
DJANGO_REST_PASSWORDRESET = {
    'EMAIL_TEMPLATE': 'reset_password.html',
}

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
ONESIGNAL_APP_ID = config("ONESIGNAL_APP_ID")
ONESIGNAL_REST_API_KEY = config("ONESIGNAL_REST_API_KEY")

DEEPSEEK_API_KEY = config("DEEPSEEK_API_KEY", default="")

# Hugging Face API for Lumora AI
HUGGINGFACE_API_KEY = config("HUGGINGFACE_API_KEY", default="")

# Groq API for Lumora AI (Primary AI Engine)
GROQ_API_KEY = config("GROQ_API_KEY", default="") 


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
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}

cloudinary.config(
    cloud_name=config('CLOUDINARY_CLOUD_NAME'),
    api_key=config('CLOUDINARY_API_KEY'),
    api_secret=config('CLOUDINARY_API_SECRET'),
    secure=True
)

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

print("Cloudinary successfully configured for:", CLOUDINARY_STORAGE['CLOUD_NAME'])

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

    print("Default storage manually switched to:", storage_module.default_storage.__class__)
except Exception as e:
    print("Cloudinary setup issue:", e)
