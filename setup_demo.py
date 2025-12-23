#!/usr/bin/env python
"""
Quick setup script for push notification demo
Run this to create demo user and test items
"""
import os
import django
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expirytracker.settings')
django.setup()

from django.contrib.auth.models import User
from tracker.models import Item, UserProfile
from datetime import date, timedelta

def setup_demo():
    print("🚀 Setting up push notification demo...")

    # Create test user
    user, created = User.objects.get_or_create(
        username='demo',
        defaults={
            'email': 'demo@example.com',
            'first_name': 'Demo',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('demo123')
        user.save()
        print("✅ Created demo user: demo/demo123")

    # Create user profile with push notifications enabled
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'push_reminders_enabled': True,
            'email_reminders_enabled': True
        }
    )
    if created:
        print("✅ Created user profile with push notifications enabled")

    # Delete existing demo items to avoid duplicates
    Item.objects.filter(user=user, notes__icontains='Demo item').delete()

    # Create test items expiring soon
    items_data = [
        ('Milk', 'Dairy', 2, 'Fresh whole milk'),
        ('Bread', 'Bakery', 1, 'Whole grain bread'),
        ('Cheese', 'Dairy', 3, 'Cheddar cheese block'),
        ('Yogurt', 'Dairy', 4, 'Greek yogurt'),
        ('Chicken', 'Meat', 1, 'Chicken breast'),
    ]

    created_items = []
    for name, category, days, notes in items_data:
        item, created = Item.objects.get_or_create(
            user=user,
            name=name,
            category=category,
            expiry_date=date.today() + timedelta(days=days),
            defaults={
                'notes': f'{notes} - Demo item for push notifications',
                'barcode': f'DEMO{hash(name) % 10000:04d}'
            }
        )
        if created:
            created_items.append(f"{name} (expires in {days} days)")
            print(f"✅ Created item: {name} (expires in {days} days)")

    print(f"\n🎯 Demo setup complete!")
    print(f"📧 Login credentials: demo / demo123")
    print(f"📱 Items created: {len(created_items)}")
    print(f"🔔 Push notifications: ENABLED")
    print(f"📧 Email notifications: ENABLED")

    print(f"\n📋 Demo items:")
    for item in created_items:
        print(f"   • {item}")

    print(f"\n🚀 Next steps:")
    print(f"   1. Run: python manage.py runserver 8000")
    print(f"   2. Open: http://localhost:8000")
    print(f"   3. Login with: demo / demo123")
    print(f"   4. Go to Profile and enable push notifications")
    print(f"   5. Run: python manage.py send_expiry_reminders")
    print(f"   6. Watch push notifications appear!")

if __name__ == '__main__':
    setup_demo()
