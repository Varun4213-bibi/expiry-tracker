from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

class Command(BaseCommand):
    help = 'Set up periodic task for daily expiry reminders'

    def handle(self, *args, **options):
        # Create or get daily interval schedule
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.DAYS,
        )

        if created:
            self.stdout.write('Created daily interval schedule')
        else:
            self.stdout.write('Daily interval schedule already exists')

        # Create periodic task for expiry reminders
        task, created = PeriodicTask.objects.get_or_create(
            name='Send Expiry Reminders Daily',
            defaults={
                'task': 'tracker.tasks.send_expiry_reminders',
                'interval': schedule,
                'enabled': True,
            }
        )

        if created:
            self.stdout.write('Created periodic task for expiry reminders')
        else:
            self.stdout.write('Periodic task for expiry reminders already exists')

        self.stdout.write(self.style.SUCCESS('Expiry reminders scheduling setup complete!'))
        self.stdout.write('The task will run daily. Make sure to start Celery worker and beat scheduler:')
        self.stdout.write('  celery -A expirytracker worker --loglevel=info')
        self.stdout.write('  celery -A expirytracker beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler')
