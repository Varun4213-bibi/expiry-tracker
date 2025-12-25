import logging
import time
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from tracker.models import Item, UserProfile
from tracker.api_views import send_push_notification
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send expiry reminders to users for items expiring within 7 days'

    def handle(self, *args, **options):
        logger.info('Starting expiry reminders command')

        # Get items that are near expiry and not expired for all users with emails
        # We'll filter by each user's reminder_days setting
        all_near_expiry_items = Item.objects.filter(
            expiry_date__gte=timezone.now().date(),
            user__email__isnull=False
        ).exclude(user__email='').select_related('user')

        near_expiry_items = []
        for item in all_near_expiry_items:
            try:
                reminder_days = item.user.userprofile.reminder_days
            except UserProfile.DoesNotExist:
                reminder_days = 7  # Default fallback

            if item.expiry_date <= timezone.now().date() + timedelta(days=reminder_days):
                near_expiry_items.append(item)

        if not near_expiry_items:
            self.stdout.write('No items nearing expiry.')
            logger.info('No items nearing expiry found')
            return

        # Group by user and check profile preferences
        users_with_items = {}
        for item in near_expiry_items:
            # Check if user has enabled email reminders
            try:
                profile = item.user.userprofile
                if not profile.email_reminders_enabled and not profile.push_reminders_enabled:
                    continue  # Skip this user if both email and push are disabled
            except UserProfile.DoesNotExist:
                pass  # No profile, assume enabled (default)

            if item.user not in users_with_items:
                users_with_items[item.user] = []
            users_with_items[item.user].append(item)

        # Send emails and push notifications
        for user, items in users_with_items.items():
            # Send email if enabled
            try:
                profile = user.userprofile
                if profile.email_reminders_enabled:
                    self.send_reminder_email_with_retry(user, items)
            except UserProfile.DoesNotExist:
                self.send_reminder_email_with_retry(user, items)  # Default to email enabled

            # Send push notification if enabled
            try:
                profile = user.userprofile
                if profile.push_reminders_enabled:
                    self.send_push_notification(user, items)
            except UserProfile.DoesNotExist:
                self.send_push_notification(user, items)  # Default to push enabled

    def send_reminder_email_with_retry(self, user, items, max_retries=3):
        """Send reminder email with exponential backoff retry logic"""
        subject = 'Expiry Reminder: Items Expiring Soon'

        # Get user's reminder days setting
        try:
            user_reminder_days = user.userprofile.reminder_days
        except UserProfile.DoesNotExist:
            user_reminder_days = 7

        # Prepare context for HTML template
        context = {
            'user': user,
            'items': items,
            'days_range': user_reminder_days,
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

                self.stdout.write(f'Sent reminder to {user.email} for {len(items)} item(s)')
                logger.info(f'Successfully sent reminder to {user.email} for {len(items)} items')
                return  # Success, exit retry loop

            except Exception as e:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f'Attempt {attempt + 1} failed to send email to {user.email}: {e}')
                self.stderr.write(f'Attempt {attempt + 1} failed to send email to {user.email}: {e}')

                if attempt < max_retries - 1:
                    self.stdout.write(f'Retrying in {wait_time} seconds...')
                    time.sleep(wait_time)
                else:
                    logger.error(f'Failed to send email to {user.email} after {max_retries} attempts')
                    self.stderr.write(f'Failed to send email to {user.email} after {max_retries} attempts')

    def send_push_notification(self, user, items):
        """Send push notification to a user"""
        try:
            # Create notification message based on number of items
            if len(items) == 1:
                item = items[0]
                title = "Item Expiring Soon"
                body = f"{item.name} expires in {item.days_until_expiry()} days"
            else:
                title = "Items Expiring Soon"
                body = f"You have {len(items)} items expiring soon"

            # Send the push notification
            success = send_push_notification(user, title, body)

            if success:
                self.stdout.write(f'Sent push notification to {user.username} for {len(items)} item(s)')
                logger.info(f'Successfully sent push notification to {user.username} for {len(items)} items')
            else:
                self.stdout.write(f'Failed to send push notification to {user.username}')
                logger.warning(f'Failed to send push notification to {user.username}')

        except Exception as e:
            self.stderr.write(f'Error sending push notification to {user.username}: {e}')
            logger.error(f'Error sending push notification to {user.username}: {e}')
