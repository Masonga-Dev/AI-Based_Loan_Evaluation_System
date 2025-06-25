"""
Development settings for loan_evaluation_system project.
"""

from .base import *

# Override any development-specific settings below
DEBUG = True

# Optionally, override email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Optionally, override static files storage for development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Security settings for development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS = [
    'apps.authentication',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'crispy_forms',
    'crispy_bootstrap5',
    'apps.dashboard',
    'apps.loan_application',
    'apps.admin_dashboard',
    'apps.document_processing',
    'apps.api',
    'apps.ai_evaluation',
    # ...add any other project apps as needed...
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
