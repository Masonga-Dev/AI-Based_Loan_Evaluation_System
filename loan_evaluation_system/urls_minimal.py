"""
Minimal URL configuration for frontend testing
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.shortcuts import render

def home_view(request):
    return HttpResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI-Based Loan Evaluation System</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="text-center">
                <h1 class="text-primary">🏦 AI-Based Loan Evaluation System</h1>
                <p class="lead">Frontend is working! Django server is running successfully.</p>
                <div class="alert alert-success">
                    <strong>✅ Success!</strong> Your Django application is running.
                </div>
                <div class="mt-4">
                    <a href="/admin/" class="btn btn-primary">Admin Panel</a>
                    <a href="../frontend_preview.html" class="btn btn-outline-primary">View Frontend Preview</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
