from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User

# User type choices
USER_TYPE_CHOICES = [
    ('donor', 'Donor'),
    ('ngo', 'NGO'),
]

CATEGORY_CHOICES = [
    ('Medicine', 'Medicine'),
    ('Grocery', 'Grocery'),
    ('Household', 'Household'),
    ('Others', 'Others'),
]

DONATION_STATUS_CHOICES = [
    ('available', 'Available for Donation'),
    ('donating', 'Being Donated'),
    ('donated', 'Donated'),
]

DONATION_REQUEST_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='donor')
    email_reminders_enabled = models.BooleanField(default=True, help_text="Enable email reminders for expiring items")
    push_reminders_enabled = models.BooleanField(default=True, help_text="Enable push notifications for expiring items")
    reminder_days = models.PositiveIntegerField(default=7, help_text="Days before expiry to send reminders (1-30)")

    def __str__(self):
        return f"{self.user.username}'s profile ({self.user_type})"

    def is_ngo(self):
        return self.user_type == 'ngo'

    def is_donor(self):
        return self.user_type == 'donor'

class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    endpoint = models.URLField(unique=True, help_text="Push service endpoint URL")
    p256dh = models.CharField(max_length=88, help_text="P-256 elliptic curve Diffie-Hellman public key")
    auth = models.CharField(max_length=24, help_text="Authentication secret")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'endpoint']

    def __str__(self):
        return f"Push subscription for {self.user.username}"


class Item(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Others')
    barcode = models.CharField(max_length=100, blank=True, null=True, help_text="Barcode or QR code value (optional)")
    added_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    donated = models.BooleanField(default=False, help_text="Mark if item has been donated")

    def is_expired(self):
        return timezone.now().date() > self.expiry_date

    def days_until_expiry(self):
        remaining = self.expiry_date - timezone.now().date()
        return remaining.days

    def is_near_expiry(self):
        """Items expiring within 7 days"""
        return 0 <= self.days_until_expiry() <= 7

    def __str__(self):
        return f"{self.name} ({self.category})"
class Product(models.Model):
    id = models.AutoField(primary_key=True)
    barcode = models.CharField(max_length=50)
    product_name = models.CharField(max_length=199)

    class Meta:
        db_table = 'products'  # Exact table name in PostgreSQL
        managed = False        # Django won't try to create or migrate it

    def __str__(self):
        return self.product_name


class NGOProfile(models.Model):
    """Profile for NGO organizations"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization_name = models.CharField(max_length=200, help_text="Full name of the NGO organization")
    registration_number = models.CharField(max_length=100, blank=True, null=True, help_text="NGO registration number")
    contact_person = models.CharField(max_length=100, help_text="Primary contact person")
    phone = models.CharField(max_length=15, help_text="Contact phone number")
    address = models.TextField(help_text="Complete address of the NGO")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    website = models.URLField(blank=True, null=True, help_text="NGO website URL")
    description = models.TextField(blank=True, null=True, help_text="Brief description of NGO activities")
    verified = models.BooleanField(default=False, help_text="Admin verification status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.organization_name} ({self.city})"


class Donation(models.Model):
    """Records donation requests from donors to NGOs"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations_made')
    ngo_profile = models.ForeignKey(NGOProfile, on_delete=models.CASCADE, related_name='donation_requests',null=True, blank=True)
    # Keep legacy fields for backward compatibility with manual Gmail process
    ngo = models.CharField(max_length=200, help_text="NGO organization name")
    ngo_email = models.EmailField(help_text="NGO contact email")
    status = models.CharField(max_length=20, choices=DONATION_REQUEST_STATUS_CHOICES, default='pending')
    pickup_address = models.TextField(help_text="Address for pickup")
    contact_number = models.CharField(max_length=15, help_text="Donor contact number")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")
    donation_date = models.DateTimeField(auto_now_add=True)
    confirmed_date = models.DateTimeField(blank=True, null=True)
    completed_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Donation to {self.ngo} by {self.user.username} - {self.status}"

    def get_total_items(self):
        return self.items_donated.count()

    def get_medicine_items(self):
        return self.items_donated.filter(category='Medicine')


class NGOInventory(models.Model):
    """Inventory of medicines received by NGOs"""
    ngo = models.ForeignKey(NGOProfile, on_delete=models.CASCADE, related_name='inventory')
    item_name = models.CharField(max_length=100, help_text="Name of the medicine/item")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Medicine')
    barcode = models.CharField(max_length=100, blank=True, null=True, help_text="Barcode if available")
    expiry_date = models.DateField(help_text="Expiry date of the medicine")
    quantity = models.PositiveIntegerField(default=1, help_text="Quantity received")
    batch_number = models.CharField(max_length=100, blank=True, null=True, help_text="Batch number")
    source_donation = models.ForeignKey(Donation, on_delete=models.SET_NULL, null=True, blank=True, related_name='ngo_inventory')
    received_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")

    def is_expired(self):
        return timezone.now().date() > self.expiry_date

    def days_until_expiry(self):
        remaining = self.expiry_date - timezone.now().date()
        return remaining.days

    def is_near_expiry(self):
        """Items expiring within 30 days for NGOs (longer than donors)"""
        return 0 <= self.days_until_expiry() <= 30

    def __str__(self):
        return f"{self.item_name} - {self.ngo.organization_name} (Exp: {self.expiry_date})"
