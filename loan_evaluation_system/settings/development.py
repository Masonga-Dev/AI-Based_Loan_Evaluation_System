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
