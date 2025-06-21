from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dashboard:admin_dashboard', permanent=False)),
    path('stats/', views.dashboard_stats, name='stats'),
    path('recent-activity/', views.recent_activity, name='recent_activity'),
    path('admin-dashboard/', views.dashboard_home, name='admin_dashboard'),
]
