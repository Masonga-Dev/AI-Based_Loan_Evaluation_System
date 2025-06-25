from apps.dashboard.models import Notification

def create_notification(user, message, link=None):
    """
    Helper to create a notification for a user.
    """
    Notification.objects.create(user=user, message=message, link=link)
