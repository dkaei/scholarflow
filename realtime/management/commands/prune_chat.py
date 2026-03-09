from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from realtime.models import CourseMessage

class Command(BaseCommand):
    help = "Delete old course chat messages"

    def handle(self, *args, **options):
        days = getattr(settings, "CHAT_RETENTION_DAYS", 7)
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = CourseMessage.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} old messages (cutoff: {cutoff})."))
