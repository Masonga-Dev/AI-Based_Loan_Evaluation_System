from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    
    # AJAX endpoints
    path('check-email/', views.check_email_availability, name='check_email'),
    path('check-username/', views.check_username_availability, name='check_username'),
]
