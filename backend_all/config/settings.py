import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if present
load_dotenv(BASE_DIR / '.env')

try:
    import dj_database_url
except ImportError:
    dj_database_url = None

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-z4w+$gq=r24z40t&3+%3c0emj-47!y55carhtu5hsg2$1&ak=0'
)

DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ['true', '1', 'yes']

allowed_hosts_env = os.getenv('DJANGO_ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()]

# Automatically support Render external hostnames
render_host = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if render_host and render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    # Third-party apps
    'corsheaders',
    'rest_framework',
    'drf_spectacular',
    # PrintX Modular Applications
    'apps.common.apps.CommonConfig',
    'apps.devices.apps.DevicesConfig',
    'apps.audit.apps.AuditConfig',
    'apps.payments.apps.PaymentsConfig',
    'apps.printing.apps.PrintingConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database Configuration (DATABASE_URL / PostgreSQL / SQLite)
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and dj_database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif os.getenv('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB'),
            'USER': os.getenv('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Private Document Storage (Stored safely outside public web root)
PRIVATE_STORAGE_ROOT = BASE_DIR / 'private_storage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
}

# DRF Spectacular OpenAPI / Swagger configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'PrintX Platform & Agent API',
    'DESCRIPTION': 'Production-ready REST API for PrintX document printing platform and PC Print Agent',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() in ['true', '1', 'yes']

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:5500',
    'http://localhost:8000',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5500',
    'http://127.0.0.1:8000',
]

cors_extra = os.getenv('CORS_ALLOWED_ORIGINS')
if cors_extra:
    CORS_ALLOWED_ORIGINS.extend([origin.strip() for origin in cors_extra.split(',') if origin.strip()])

# Allow all localhost/127.0.0.1 ports for local frontend development
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:5500',
    'http://localhost:8000',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5500',
    'http://127.0.0.1:8000',
]

csrf_extra = os.getenv('CSRF_TRUSTED_ORIGINS')
if csrf_extra:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in csrf_extra.split(',') if origin.strip()])

if render_host:
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_host}")

# Admin Side Frontend Directory (check env, parent dir, or current dir)
admin_side_env = os.getenv('ADMIN_SIDE_DIR')
if admin_side_env:
    ADMIN_SIDE_DIR = Path(admin_side_env)
elif (BASE_DIR.parent / 'admin_side').exists():
    ADMIN_SIDE_DIR = BASE_DIR.parent / 'admin_side'
elif (BASE_DIR / 'admin_side').exists():
    ADMIN_SIDE_DIR = BASE_DIR / 'admin_side'
else:
    ADMIN_SIDE_DIR = BASE_DIR.parent / 'admin_side'

