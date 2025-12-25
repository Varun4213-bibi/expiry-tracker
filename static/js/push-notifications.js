// Push Notifications JavaScript for PWA
class PushNotificationManager {
  constructor() {
    this.registration = null;
    this.isSubscribed = false;
    this.vapidPublicKey = null;
  }

  async init() {
    // Check for basic service worker support
    if (!('serviceWorker' in navigator)) {
      console.warn('Service Worker not supported in this browser');
      return false;
    }

    // Allow localhost for development (HTTP is fine for localhost)
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
      console.log('Running on localhost - push notifications allowed for development');
    } else if (location.protocol !== 'https:') {
      console.warn('Push notifications require HTTPS in production');
      return false;
    }

    try {
      // Register service worker if not already registered
this.registration = await navigator.serviceWorker.register('/service-worker.js', {
    scope: '/'
});
await navigator.serviceWorker.ready;
console.log('Service Worker active and ready');
console.log('Service Worker registered at root scope');


      // Check if already subscribed
      const subscription = await this.registration.pushManager.getSubscription();
      this.isSubscribed = !(subscription === null);

      // Get VAPID public key from server
      await this.getVapidPublicKey();

      return true;
    } catch (error) {
      console.error('Service Worker registration failed:', error);
      return false;
    }
  }


  async getVapidPublicKey() {
    try {
      const response = await fetch('/api/notifications/vapid-public-key/');
      if (response.ok) {
        const data = await response.json();
        this.vapidPublicKey = data.public_key;
      }
    } catch (error) {
      console.error('Failed to get VAPID public key:', error);
    }
  }

  async subscribe() {
  if (!this.registration) return false;

  if (!this.vapidPublicKey) {
    console.error('VAPID public key missing');
    return false;
  }

  try {
    const subscription = await this.registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
    });

    const response = await fetch('/api/notifications/subscribe/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCsrfToken()
      },
      body: JSON.stringify({
        subscription: subscription.toJSON()
      })
    });

    if (response.ok) {
      this.isSubscribed = true;
      console.log('Successfully subscribed to push notifications');
      return true;
    } else {
      console.error('Failed to subscribe on server');
      return false;
    }
  } catch (error) {
    console.error('Failed to subscribe to push notifications:', error);
    return false;
  }
}


  async unsubscribe() {
    if (!this.registration) return false;

    try {
      const subscription = await this.registration.pushManager.getSubscription();
      if (subscription) {
        const result = await subscription.unsubscribe();

        if (result) {
          // Notify server
          await fetch('/api/notifications/unsubscribe/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
              endpoint: subscription.endpoint
            })
          });

          this.isSubscribed = false;
          console.log('Successfully unsubscribed from push notifications');
          return true;
        }
      }
    } catch (error) {
      console.error('Failed to unsubscribe from push notifications:', error);
    }
    return false;
  }

  async requestPermission() {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }
    return false;
  }

  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  getCsrfToken() {
    // Get CSRF token from cookie or meta tag
    const token = document.querySelector('meta[name="csrf-token"]');
    if (token) {
      return token.getAttribute('content');
    }

    // Fallback: get from cookie
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];

    return cookieValue || '';
  }

  // Test notification (for development)
  async testNotification() {
    if (!this.registration) return;

    const options = {
      body: 'This is a test notification from ExpiryTracker!',
      icon: '/static/images/icon-192.png',
      badge: '/static/images/icon-192.png',
      vibrate: [200, 100, 200],
      data: {
        url: '/view_items/'
      },
      actions: [
        {
          action: 'view',
          title: 'View Items'
        }
      ]
    };

    await this.registration.showNotification('Test Notification', options);
  }
}

// Initialize push notifications when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
  const pushManager = new PushNotificationManager();
  window.pushNotifications = pushManager;

  const initialized = await pushManager.init();
  if (initialized) {
    console.log('Push notifications initialized');

    // Handle profile page push notification checkbox
    const pushCheckbox = document.getElementById('id_push_reminders_enabled');
    if (pushCheckbox) {
      // Set initial checkbox state based on subscription status
      pushCheckbox.checked = pushManager.isSubscribed;

      // Add event listener for checkbox changes
      pushCheckbox.addEventListener('change', async (event) => {
        if (event.target.checked) {
          // User wants to enable push notifications
          console.log('Enabling push notifications...');
          const permission = await pushManager.requestPermission();
          if (permission) {
            const success = await pushManager.subscribe();
            if (!success) {
              // If subscription failed, uncheck the box
              event.target.checked = false;
              alert('Failed to enable push notifications. Please check your browser settings.');
            }
          } else {
            // If permission denied, uncheck the box
            event.target.checked = false;
            alert('Push notification permission denied. Please allow notifications in your browser settings.');
          }
        } else {
          // User wants to disable push notifications
          console.log('Disabling push notifications...');
          const success = await pushManager.unsubscribe();
          if (!success) {
            // If unsubscription failed, recheck the box
            event.target.checked = true;
            alert('Failed to disable push notifications.');
          }
        }
      });
    }

    // Add event listeners to notification buttons if they exist (for other pages)
    const subscribeBtn = document.getElementById('subscribe-notifications');
    const unsubscribeBtn = document.getElementById('unsubscribe-notifications');
    const testBtn = document.getElementById('test-notification');

    if (subscribeBtn) {
      subscribeBtn.addEventListener('click', async () => {
        const permission = await pushManager.requestPermission();
        if (permission) {
          const success = await pushManager.subscribe();
          if (success) {
            subscribeBtn.style.display = 'none';
            if (unsubscribeBtn) unsubscribeBtn.style.display = 'inline-block';
            if (testBtn) testBtn.style.display = 'inline-block';
            // Also update checkbox if it exists
            if (pushCheckbox) pushCheckbox.checked = true;
          }
        }
      });
    }

    if (unsubscribeBtn) {
      unsubscribeBtn.addEventListener('click', async () => {
        const success = await pushManager.unsubscribe();
        if (success) {
          unsubscribeBtn.style.display = 'none';
          if (testBtn) testBtn.style.display = 'none';
          if (subscribeBtn) subscribeBtn.style.display = 'inline-block';
          // Also update checkbox if it exists
          if (pushCheckbox) pushCheckbox.checked = false;
        }
      });
    }

    if (testBtn) {
      testBtn.addEventListener('click', () => {
        pushManager.testNotification();
      });
    }

    // Update button visibility based on subscription status (for other pages)
    if (pushManager.isSubscribed) {
      if (subscribeBtn) subscribeBtn.style.display = 'none';
      if (unsubscribeBtn) unsubscribeBtn.style.display = 'inline-block';
      if (testBtn) testBtn.style.display = 'inline-block';
    } else {
      if (subscribeBtn) subscribeBtn.style.display = 'inline-block';
      if (unsubscribeBtn) unsubscribeBtn.style.display = 'none';
      if (testBtn) testBtn.style.display = 'none';
    }
  } else {
    console.warn('Push notifications not supported or failed to initialize');
    // Disable checkbox if push notifications are not supported
    const pushCheckbox = document.getElementById('id_push_reminders_enabled');
    if (pushCheckbox) {
      pushCheckbox.disabled = true;
      pushCheckbox.parentElement.style.opacity = '0.5';
    }
  }
});
