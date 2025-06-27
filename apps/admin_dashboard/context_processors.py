"""
Context processors for admin dashboard
"""
from django.db.models import Count
from apps.loan_application.models import LoanApplication, ApplicationDocument
from apps.admin_dashboard.models import AdminNotification, DocumentFlag


def admin_sidebar_context(request):
    """
    Provide context data for admin sidebar
    """
    context = {}
    
    # Only add admin context for authenticated users with admin roles
    if (request.user.is_authenticated and 
        hasattr(request.user, 'role') and 
        request.user.role in ['admin', 'manager', 'officer']):
        
        try:
            # Get pending applications count
            pending_count = LoanApplication.objects.filter(
                status__in=['submitted', 'under_review']
            ).count()
            
            # Get flagged documents count
            flagged_count = DocumentFlag.objects.filter(
                is_resolved=False
            ).count()
            
            # Get unread notifications count for current user
            notification_count = AdminNotification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
            
            context.update({
                'pending_count': pending_count,
                'flagged_count': flagged_count,
                'notification_count': notification_count,
            })
            
        except Exception as e:
            # Gracefully handle any database errors
            context.update({
                'pending_count': 0,
                'flagged_count': 0,
                'notification_count': 0,
            })
    
    return context
