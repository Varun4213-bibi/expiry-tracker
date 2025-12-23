import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expirytracker.settings')
django.setup()

from django_celery_beat.models import PeriodicTask

task = PeriodicTask.objects.filter(name='Send Expiry Reminders Daily').first()
if task:
    task.last_run_at = None
    task.save()
    print('Reset last_run_at to None')
else:
    print('Task not found')
