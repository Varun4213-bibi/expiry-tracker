from django.urls import path, include
from . import views
from .api_views import (
    RegisterView, LoginView, ItemListCreateView, ItemDetailView,
    UserProfileView, ProductLookupView, ocr_expiry_api,
    barcode_scan_api, donate_item_api, vapid_public_key,
    subscribe_push, unsubscribe_push
)


# Web URLs
urlpatterns = [
    path('', views.home, name='home'),                       # Homepage
    path('items/', views.view_items, name='view_items'),    # View all tracked items
    path('add-item/', views.add_item, name='add_item'),     # Form to add item (optionally with barcode)
    path('scan/', views.scan_product, name='scan'), # Barcode scanner page
    path('products/', views.product_list, name='product_list'),  # JSON API list of products
    path('lookup-product/', views.lookup_product, name='lookup_product'),
    path('delete-item/<int:item_id>/', views.delete_item, name='delete_item'),
    path('donate-item/<int:item_id>/', views.donate_item, name='donate_item'),
    path('donate-to-ngo/', views.donate_to_ngo, name='donate_to_ngo'),
    path('ocr-expiry/', views.ocr_expiry_view, name='ocr_expiry'),
    path('profile/', views.profile, name='profile'),        # User profile page
# Auth & User
path('signup/', views.signup, name='signup'),

# NGO Auth & Dashboard
path('ngo/register/', views.ngo_register, name='ngo_register'),
path('ngo/login/', views.ngo_login, name='ngo_login'),
path('ngo/dashboard/', views.ngo_dashboard, name='ngo_dashboard'),

# Donation success
path('donation-success/', views.donation_success, name='donation_success'),


]

# API URLs
api_urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='api_register'),
    path('auth/login/', LoginView.as_view(), name='api_login'),
    path('items/', ItemListCreateView.as_view(), name='api_items'),
    path('items/<int:pk>/', ItemDetailView.as_view(), name='api_item_detail'),
    path('profile/', UserProfileView.as_view(), name='api_profile'),
    # path('ngos/', NGOListView.as_view(), name='api_ngos'),  # NGO functionality removed
    path('products/lookup/', ProductLookupView.as_view(), name='api_product_lookup'),
    path('ocr/expiry/', ocr_expiry_api, name='api_ocr_expiry'),
    path('barcode/scan/', barcode_scan_api, name='api_barcode_scan'),
    path('donate/', donate_item_api, name='api_donate'),
    # Push notification endpoints
    path('notifications/vapid-public-key/', vapid_public_key, name='api_vapid_public_key'),
    path('notifications/subscribe/', subscribe_push, name='api_subscribe_push'),
    path('notifications/unsubscribe/', unsubscribe_push, name='api_unsubscribe_push'),
]


urlpatterns += [
    path('api/', include(api_urlpatterns)),
]
