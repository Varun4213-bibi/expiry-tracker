
from django.contrib import admin
from .models import Item

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'expiry_date', 'barcode', 'added_date', 'user']
    search_fields = ['name', 'barcode']
    list_filter = ['user']
