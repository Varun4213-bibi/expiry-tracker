import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expirytracker.settings')
django.setup()

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from tracker.models import Item
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# Get items expiring soon
items = Item.objects.filter(
    expiry_date__gte=timezone.now().date(),
    expiry_date__lte=timezone.now().date() + timedelta(days=7),
    user__email__isnull=False
).exclude(user__email='').select_related('user')

print(f"Found {items.count()} items expiring soon")

if items.exists():
    user = items.first().user
    print(f"Sending email to: {user.email}")

    context = {'user': user, 'items': items, 'days_range': 7}
    html_content = render_to_string('emails/expiry_reminder.html', context)
    text_content = 'The following items are expiring soon. Please check and use them before expiry:\n\n'

    for item in items:
        days = item.days_until_expiry()
        text_content += f'- {item.name} ({item.category}): expires in {days} day(s)\n'

    text_content += '\n\nRegards,\nExpiry Tracker'

    email = EmailMultiAlternatives(
        'Expiry Reminder: Items Expiring Soon',
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [user.email]
    )
    email.attach_alternative(html_content, 'text/html')
    result = email.send()
    print(f'Email send result: {result}')
else:
    print("No items expiring soon")
