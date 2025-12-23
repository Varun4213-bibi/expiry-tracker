#!/usr/bin/env python
"""
Script to register an FCM token for testing push notifications
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expirytracker.settings')
django.setup()

from tracker.models import User, PushSubscription

def register_test_fcm_token():
    """Register a test FCM token for the first user"""
    try:
        # Get the first user
        user = User.objects.first()
        if not user:
            print("❌ No users found in the database. Please create a user first.")
            return

        # Test FCM token (this is a sample token - in real usage, this would come from Firebase SDK)
        test_fcm_token = "eXAMPLE_FCM_TOKEN_FOR_TESTING_1234567890123456789012345678901234567890"

        print(f"🔗 Registering FCM token for user: {user.username}")

        # Check if token already exists
        existing_subscription = PushSubscription.objects.filter(
            user=user,
            fcm_token=test_fcm_token
        ).first()

        if existing_subscription:
            print("✅ FCM token already registered for this user")
            return

        # Create new subscription with FCM token
        subscription = PushSubscription.objects.create(
            user=user,
            fcm_token=test_fcm_token
        )

        print("✅ FCM token registered successfully!")
        print(f"   User: {user.username}")
        print(f"   Token: {test_fcm_token[:20]}...")

    except Exception as e:
        print(f"❌ Error registering FCM token: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    register_test_fcm_token()
