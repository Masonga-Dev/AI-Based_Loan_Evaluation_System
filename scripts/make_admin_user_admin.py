# This script will update your user to have role='admin', is_staff=True, is_superuser=True
from apps.authentication.models import User

username = input('Enter the username to make admin: ')
try:
    user = User.objects.get(username=username)
    user.role = 'admin'
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"User '{username}' updated to admin successfully.")
except User.DoesNotExist:
    print(f"User '{username}' does not exist.")
