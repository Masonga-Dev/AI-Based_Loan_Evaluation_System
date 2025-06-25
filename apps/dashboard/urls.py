from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('stats/', views.dashboard_stats, name='stats'),
    path('recent-activity/', views.recent_activity, name='recent_activity'),
    path('admin-dashboard/', views.dashboard_home, name='admin_dashboard'),
    path('applicant-dashboard/', views.dashboard_home, name='applicant_dashboard'),
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/page/', views.notifications_page, name='notifications'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
]
