#!/usr/bin/env python
"""
Send a test push notification to demonstrate the system works
"""
import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expirytracker.settings')

# Setup Django
django.setup()

def send_test_push():
    """Send a test push notification"""
    print("🔔 Sending Test Push Notification")
    print("=" * 40)

    try:
        from tracker.api_views import send_push_notification
        from tracker.models import PushSubscription, UserProfile
        from django.contrib.auth.models import User

        # Get the first user with push notifications enabled
        user = User.objects.filter(userprofile__push_reminders_enabled=True).first()

        if not user:
            print("❌ No users found with push notifications enabled")
            print("💡 Enable push notifications in your profile first")
            return False

        print(f"✅ Found user: {user.username}")

        # Check if user has push subscriptions
        subscriptions = PushSubscription.objects.filter(user=user)
        if not subscriptions.exists():
            print("❌ No push subscriptions found for this user")
            print("💡 Visit the Smart Tracker website and allow notifications")
            return False

        print(f"✅ Found {subscriptions.count()} push subscription(s)")

        # Send test notification
        test_message = "🔔 Test Push Notification: Smart Tracker is working perfectly!"
        print(f"📤 Sending: '{test_message}'")

        success = send_push_notification(user, test_message)

        if success:
            print("✅ Push notification sent successfully!")
            print("💡 Check your browser for the notification popup")
            return True
        else:
            print("❌ Failed to send push notification")
            print("💡 Check your browser's notification settings")
            return False

    except Exception as e:
        print(f"❌ Error sending push notification: {e}")
        return False

if __name__ == '__main__':
    success = send_test_push()
    sys.exit(0 if success else 1)
