"""
Management command to create admin profiles for existing users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.admin_dashboard.models import AdminUserProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Create admin profiles for existing users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing profiles',
        )

    def handle(self, *args, **options):
        users = User.objects.all()
        created_count = 0
        updated_count = 0
        
        for user in users:
            profile, created = AdminUserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'risk_level': 'low',
                    'is_verified': False,
                    'total_logins': 0,
                    'total_applications_submitted': 0,
                    'total_documents_uploaded': 0,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created profile for {user.username}')
                )
            elif options['force']:
                # Update existing profile if force flag is used
                profile.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated profile for {user.username}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {users.count()} users. '
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )
