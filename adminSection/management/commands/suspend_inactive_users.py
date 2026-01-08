from django.core.management.base import BaseCommand
from django.utils import timezone
from adminSection.models import Profile

class Command(BaseCommand):
    help = 'Suspend accounts that were created 3+ days ago and never logged in'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        expired_users = Profile.objects.filter(
            user__last_login__isnull=True,
            created_at__lt=now - timezone.timedelta(days=3),
            is_suspended=False
        )
        for profile in expired_users:
            profile.is_suspended = True
            profile.save()
            self.stdout.write(f"Suspended: {profile.user.username}")
