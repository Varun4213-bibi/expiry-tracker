import logging
import time
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import Item
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

@shared_task
def send_expiry_reminders():
    """Celery task to send expiry reminders to all users with items expiring within 7 days"""
    logger.info('Starting expiry reminders task')

    # Get items that are near expiry and not expired for all users with emails
    near_expiry_items = Item.objects.filter(
        expiry_date__gte=timezone.now().date(),
        expiry_date__lte=timezone.now().date() + timedelta(days=7),
        user__email__isnull=False
    ).exclude(user__email='').select_related('user')

    if not near_expiry_items.exists():
        logger.info('No items nearing expiry found')
        return 'No items nearing expiry'

    # Group by user and check profile preferences
    users_with_items = {}
    for item in near_expiry_items:
        # Check if user has enabled email reminders
        try:
            profile = item.user.userprofile
            if not profile.email_reminders_enabled:
                continue  # Skip this user
        except UserProfile.DoesNotExist:
            pass  # No profile, assume enabled (default)

        if item.user not in users_with_items:
            users_with_items[item.user] = []
        users_with_items[item.user].append(item)

    sent_count = 0
    failed_count = 0

    # Send emails with retry logic
    for user, items in users_with_items.items():
        if send_reminder_email_with_retry(user, items):
            sent_count += 1
        else:
            failed_count += 1

    result = f'Sent reminders to {sent_count} users, failed for {failed_count} users'
    logger.info(result)
    return result

def send_reminder_email_with_retry(user, items, max_retries=3):
    """Send reminder email with exponential backoff retry logic"""
    subject = 'Expiry Reminder: Items Expiring Soon'

    # Prepare context for HTML template
    context = {
        'user': user,
        'items': items,
        'days_range': 7,
    }

    # Render HTML content
    html_content = render_to_string('emails/expiry_reminder.html', context)

    # Plain text fallback
    text_content = 'The following items are expiring soon. Please check and use them before expiry:\n\n'
    for item in items:
        days = item.days_until_expiry()
        text_content += f'- {item.name} ({item.category}): expires in {days} day(s)\n'
    text_content += '\n\nRegards,\nExpiry Tracker'

    for attempt in range(max_retries):
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f'Successfully sent reminder to {user.email} for {len(items)} items')
            return True  # Success

        except Exception as e:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(f'Attempt {attempt + 1} failed to send email to {user.email}: {e}')

            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                logger.error(f'Failed to send email to {user.email} after {max_retries} attempts')

    return False  # Failed after all retries
