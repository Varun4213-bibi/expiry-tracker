# Push Notification Demo Guide for Project Review

## 🎯 **Demo Overview**
This guide shows how to demonstrate the newly implemented push notification feature in your Smart Tracker project. The feature allows users to receive real-time expiry reminders via push notifications in addition to email notifications.

## 📋 **Prerequisites**

### **1. HTTPS Required**
Push notifications require HTTPS in production. For demo purposes:
- Use `localhost` (automatically trusted)
- Or use ngrok/tunnel services for remote demo

### **2. Supported Browsers**
- Chrome/Chromium (recommended)
- Firefox
- Edge
- Safari (limited support)

### **3. Environment Setup**
```bash
cd expirytracker
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

## 🚀 **Demo Steps**

### **Step 1: Start the Application**
```bash
cd expirytracker
python manage.py runserver 8000
```
Open http://localhost:8000 in Chrome

### **Step 2: Register/Login**
1. Create a new user account or login with existing credentials
2. Navigate to the profile page to enable push notifications

### **Step 3: Enable Push Notifications**
1. Go to Profile page (`/profile/`)
2. Enable "Push Notifications" toggle
3. Browser will request notification permission - **ALLOW IT**
4. You should see a success message

### **Step 4: Create Test Items**
1. Add items with expiry dates within 7 days
2. Use "Add Item" form
3. Set expiry dates to tomorrow or in 2-3 days

### **Step 5: Trigger Push Notifications**

#### **Option A: Manual Trigger (Recommended for Demo)**
```bash
cd expirytracker
python manage.py send_expiry_reminders
```

#### **Option B: Celery Worker (Advanced)**
```bash
# Terminal 1: Start Redis (if not running)
redis-server

# Terminal 2: Start Celery worker
cd expirytracker
celery -A expirytracker worker -l info

# Terminal 3: Trigger task
celery -A expirytracker call tracker.tasks.send_expiry_reminders
```

## 📱 **What to Show During Demo**

### **1. Permission Request**
- Show browser asking for notification permission
- Explain this is required for push notifications

### **2. Subscription Success**
- Show success message after enabling push notifications
- Explain VAPID key exchange happens securely

### **3. Push Notification Receipt**
- Show the push notification appearing on screen
- Demonstrate vibration/sound (if enabled)
- Show notification actions: "View Items" and "Dismiss"

### **4. Notification Click Behavior**
- Click "View Items" - should navigate to `/view_items/`
- Click "Dismiss" - notification closes

### **5. Dual Notification System**
- Show that users receive BOTH email AND push notifications
- Demonstrate user preference settings

## 🔧 **Demo Scripts**

### **Quick Setup Script**
```bash
#!/bin/bash
cd expirytracker

# Install dependencies
pip install pywebpush==1.14.0

# Run migrations
python manage.py migrate

# Create test user and items
python manage.py shell -c "
from django.contrib.auth.models import User
from tracker.models import Item, UserProfile
from datetime import date, timedelta

# Create test user
user, created = User.objects.get_or_create(
    username='demo',
    defaults={'email': 'demo@example.com'}
)
if created:
    user.set_password('demo123')
    user.save()

# Create user profile with push notifications enabled
profile, created = UserProfile.objects.get_or_create(
    user=user,
    defaults={'push_reminders_enabled': True, 'email_reminders_enabled': True}
)

# Create test items expiring soon
Item.objects.get_or_create(
    user=user,
    name='Milk',
    category='Dairy',
    expiry_date=date.today() + timedelta(days=2),
    defaults={'notes': 'Demo item for push notifications'}
)

Item.objects.get_or_create(
    user=user,
    name='Bread',
    category='Bakery',
    expiry_date=date.today() + timedelta(days=1),
    defaults={'notes': 'Another demo item'}
)

print('Demo user and items created!')
print('Username: demo')
print('Password: demo123')
"
```

### **Trigger Notifications Script**
```python
# trigger_notifications.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expirytracker.settings')
django.setup()

from tracker.tasks import send_expiry_reminders

if __name__ == '__main__':
    print("Triggering expiry reminders...")
    result = send_expiry_reminders()
    print(f"Result: {result}")
```

## 🎬 **Demo Flow Script**

### **For Project Review Presentation:**

1. **Introduction (30 seconds)**
   - "Our smart tracker now supports push notifications alongside email reminders"
   - "This provides real-time notifications to improve user experience"

2. **Technical Overview (1 minute)**
   - Show backend models (PushSubscription, UserProfile.push_reminders_enabled)
   - Show API endpoints for subscription management
   - Show Celery task integration

3. **Live Demo (2-3 minutes)**
   - Start server and open browser
   - Login as demo user
   - Enable push notifications (show permission dialog)
   - Add expiring items
   - Trigger notifications manually
   - Show push notification appearing
   - Demonstrate click actions

4. **Key Features (1 minute)**
   - User preferences (email vs push)
   - Secure VAPID encryption
   - PWA integration
   - Cross-browser support

## 🐛 **Troubleshooting**

### **Notifications Not Appearing**
1. Check browser console for errors
2. Verify HTTPS (use localhost)
3. Check notification permissions in browser settings
4. Ensure service worker is registered

### **Permission Denied**
1. Reset site permissions in browser
2. Clear site data and try again
3. Check if browser blocks notifications by default

### **VAPID Key Issues**
1. Verify VAPID keys are set in settings.py
2. Check pywebpush installation
3. Ensure keys are base64 encoded

### **Service Worker Issues**
1. Check Application > Service Workers in DevTools
2. Verify service-worker.js is accessible
3. Check for JavaScript errors in service worker

## 📊 **Expected Demo Results**

- ✅ Browser requests notification permission
- ✅ Success message after subscription
- ✅ Push notification appears with vibration
- ✅ Notification shows correct title/body/actions
- ✅ Clicking "View Items" navigates to items page
- ✅ Clicking "Dismiss" closes notification

## 🎯 **Key Points for Review**

1. **Security**: VAPID keys ensure encrypted communication
2. **User Experience**: Real-time notifications improve engagement
3. **Scalability**: Celery handles background processing
4. **Compatibility**: Works across modern browsers
5. **Integration**: Seamlessly extends existing email system

## 📝 **Demo Checklist**

- [ ] HTTPS enabled (localhost)
- [ ] Chrome browser
- [ ] Notification permissions granted
- [ ] Test items with near expiry dates
- [ ] Push notifications enabled in profile
- [ ] Service worker registered
- [ ] VAPID keys configured
- [ ] pywebpush installed
- [ ] Celery/Redis running (optional)

This demo will effectively showcase the push notification feature and demonstrate its value for the smart tracker project!
