from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # Main dashboard views
    path('', views.dashboard_overview, name='dashboard_home'),
    path('loan-applications/', views.loan_applications, name='loan_applications'),
    path('uploaded-documents/', views.uploaded_documents, name='uploaded_documents'),
    path('ocr-data/', views.ocr_data, name='ocr_data'),
    path('ai-predictions/', views.ai_predictions, name='ai_predictions'),
    path('approve-reject/', views.approve_reject, name='approve_reject'),
    path('flag-documents/', views.flag_documents, name='flag_documents'),

    # User management
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/', views.user_profile_detail, name='user_profile_detail'),
    path('users/promote/<int:user_id>/', views.promote_user, name='promote_user'),
    path('users/deactivate/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('api/users/<int:user_id>/update/', views.update_user_profile, name='update_user_profile'),
    path('api/users/bulk-actions/', views.bulk_user_actions, name='bulk_user_actions'),

    # Notifications
    path('notifications/', views.notifications_center, name='notifications_center'),
    path('notifications/templates/', views.notification_templates, name='notification_templates'),

    # Analytics & Reporting
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/reports/', views.analytics_reports, name='analytics_reports'),
    path('analytics/reports/<int:report_id>/', views.view_analytics_report, name='view_analytics_report'),

    # AI Model Management
    path('ai-models/', views.ai_model_management, name='ai_model_management'),
    path('ai-models/<int:model_id>/', views.ai_model_detail, name='ai_model_detail'),
    path('ai-models/performance/', views.ai_performance_analytics, name='ai_performance_analytics'),

    # System Settings
    path('settings/', views.system_settings, name='system_settings'),
    path('settings/logs/', views.system_logs, name='system_logs'),

    # AJAX endpoints
    path('api/bulk-approve/', views.bulk_approve_applications, name='bulk_approve_applications'),
    path('api/verify-document/<int:document_id>/', views.verify_document, name='verify_document'),
    path('api/application-details/<uuid:application_id>/', views.get_application_details, name='get_application_details'),
    path('api/notifications/<uuid:notification_id>/action/', views.notification_action, name='notification_action'),
    path('api/notifications/bulk-actions/', views.bulk_notification_actions, name='bulk_notification_actions'),
    path('api/notifications/templates/create/', views.create_notification_template, name='create_notification_template'),
    path('api/notifications/send-bulk/', views.send_bulk_notification, name='send_bulk_notification'),
    path('api/analytics/data/', views.analytics_api_data, name='analytics_api_data'),
    path('api/analytics/reports/create/', views.create_analytics_report, name='create_analytics_report'),
    path('api/ai-models/<int:model_id>/activate/', views.activate_ai_model, name='activate_ai_model'),
    path('api/ai-models/manual-override/', views.create_manual_override, name='create_manual_override'),
    path('api/ai-models/training/start/', views.start_model_training, name='start_model_training'),
    path('api/settings/update/', views.update_system_setting, name='update_system_setting'),
    path('api/settings/create/', views.create_system_setting, name='create_system_setting'),
    path('api/settings/backup/', views.create_system_backup, name='create_system_backup'),

    # Debug
    path('debug-url-test/', views.debug_url_test, name='debug_url_test'),
]
