"""
URL configuration for loan_evaluation_system project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('auth/', include('apps.authentication.urls')),

    # Main applications
    path('', include('apps.dashboard.urls')),
    path('applications/', include('apps.loan_application.urls')),
    path('documents/', include('apps.document_processing.urls')),
    path('ai/', include('apps.ai_evaluation.urls')),
    # Admin dashboard
    path('admin-dashboard/', include('apps.admin_dashboard.urls')),
    # API
    path('api/', include('apps.api.urls')),

    # Redirect for login
    path('accounts/login/', RedirectView.as_view(url='/auth/login/', permanent=False)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'
