from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from datetime import datetime
import base64
import io
from PIL import Image
import json
from pywebpush import webpush, WebPushException


from .models import Item, UserProfile, Product
from .serializers import (
    UserSerializer, ItemSerializer, ItemCreateSerializer,
    UserProfileUpdateSerializer, ProductSerializer, OCRRequestSerializer, OCRResponseSerializer,
    BarcodeRequestSerializer, BarcodeResponseSerializer, DonationRequestSerializer
)
# from .barcode_scanner import scan_expiry_date
# from pyzbar.pyzbar import decode
# import cv2
# import numpy as np


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Please provide both username and password'},
                          status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
        return Response({'error': 'Invalid credentials'},
                       status=status.HTTP_401_UNAUTHORIZED)


class ItemListCreateView(generics.ListCreateAPIView):
    serializer_class = ItemSerializer

    def get_queryset(self):
        return Item.objects.filter(user=self.request.user).order_by('expiry_date')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ItemCreateSerializer
        return ItemSerializer


class ItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ItemSerializer

    def get_queryset(self):
        return Item.objects.filter(user=self.request.user)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileUpdateSerializer

    def get_object(self):
        return self.request.user.userprofile


# NGO functionality removed - no NGO model exists
# class NGOListView(generics.ListAPIView):
#     queryset = NGO.objects.all()
#     serializer_class = NGOSerializer
#     permission_classes = [permissions.AllowAny]


class ProductLookupView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        barcode = request.query_params.get('barcode')
        print(f"DEBUG: Received barcode lookup request for: '{barcode}'")
        if not barcode:
            return Response({'error': 'Barcode parameter required'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(barcode=barcode)
            serializer = ProductSerializer(product)
            print(f"DEBUG: Found product: {product.product_name}")
            return Response(serializer.data)
        except Product.DoesNotExist:
            print(f"DEBUG: Product not found for barcode: '{barcode}'")
            return Response({'error': 'Product not found'},
                          status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def ocr_expiry_api(request):
    """API endpoint for OCR expiry date detection"""
    try:
        image_data = request.data.get('image')
        if not image_data:
            return Response({'error': 'No image provided'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Decode base64 image
        if 'data:image' in image_data:
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        # Convert PIL image to numpy array for OpenCV
        import numpy as np
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Use the OCR function from barcode_scanner.py
        expiry_date_str = scan_expiry_date_from_image(opencv_image)

        if expiry_date_str:
            # Parse the date string
            try:
                # Assuming format "DD MMM YYYY"
                parsed_date = datetime.strptime(expiry_date_str, "%d %b %Y").date()
                return Response({
                    'expiry_date': parsed_date.isoformat(),
                    'confidence': 0.85  # Placeholder confidence score
                })
            except ValueError:
                return Response({'error': 'Could not parse detected date'},
                              status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'No expiry date detected'},
                          status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({'error': str(e)},
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def barcode_scan_api(request):
    """API endpoint for barcode scanning"""
    try:
        image_data = request.data.get('image')
        if not image_data:
            return Response({'error': 'No image provided'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Decode base64 image
        if 'data:image' in image_data:
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to OpenCV format
        # opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Decode barcode
        # barcodes = decode(opencv_image)
        barcodes = []  # Temporarily disabled due to import issues
        if barcodes:
            barcode_data = barcodes[0].data.decode('utf-8')

            # Try to find product
            try:
                product = Product.objects.get(barcode=barcode_data)
                product_serializer = ProductSerializer(product)
                return Response({
                    'barcode': barcode_data,
                    'product': product_serializer.data
                })
            except Product.DoesNotExist:
                return Response({
                    'barcode': barcode_data,
                    'product': None
                })
        else:
            return Response({'error': 'No barcode detected'},
                          status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({'error': str(e)},
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def donate_item_api(request):
    """API endpoint for donating items"""
    serializer = DonationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        item = Item.objects.get(id=serializer.validated_data['item_id'], user=request.user)
        # NGO functionality removed - just mark as donated
        # ngo = NGO.objects.get(id=serializer.validated_data['ngo_id'])

        # Mark item as donated
        item.donated = True
        item.save()

        # Here you could send email to NGO
        # send_donation_email(item, ngo, serializer.validated_data.get('message', ''))

        return Response({'message': 'Item marked for donation successfully'})

    except Item.DoesNotExist:
        return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
    # except NGO.DoesNotExist:
    #     return Response({'error': 'NGO not found'}, status=status.HTTP_404_NOT_FOUND)


# Push Notification API Views
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def vapid_public_key(request):
    """Return the VAPID public key for push notifications"""
    try:
        from ecdsa import SigningKey, NIST256p
        import base64

        # Generate VAPID keys if not set
        private_key = settings.VAPID_PRIVATE_KEY
        if private_key == 'your-private-key-here':
            # Generate new keys for demo purposes
            sk = SigningKey.generate(curve=NIST256p)
            private_key = base64.urlsafe_b64encode(sk.to_pem()).decode('utf-8')
            public_key = base64.urlsafe_b64encode(sk.verifying_key.to_pem()).decode('utf-8')
        else:
            # Load existing private key and derive public key
            sk = SigningKey.from_pem(base64.urlsafe_b64decode(private_key))
            public_key = base64.urlsafe_b64encode(sk.verifying_key.to_pem()).decode('utf-8')

        return Response({'public_key': public_key})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def subscribe_push(request):
    """Subscribe user to push notifications"""
    try:
        subscription_data = request.data.get('subscription')
        if not subscription_data:
            return Response({'error': 'Subscription data required'}, status=status.HTTP_400_BAD_REQUEST)

        # Save or update subscription
        subscription, created = PushSubscription.objects.get_or_create(
            user=request.user,
            defaults={'subscription': subscription_data}
        )

        if not created:
            subscription.subscription = subscription_data
            subscription.save()

        return Response({'message': 'Successfully subscribed to push notifications'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unsubscribe_push(request):
    """Unsubscribe user from push notifications"""
    try:
        PushSubscription.objects.filter(user=request.user).delete()
        return Response({'message': 'Successfully unsubscribed from push notifications'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Push Notification Utility Functions
def send_push_notification(user, title, body, url=None, icon=None):
    """Send push notification to a user"""
    try:
        subscription = PushSubscription.objects.filter(user=user).first()
        if not subscription:
            return False

        subscription_data = subscription.subscription

        payload = {
            'title': title,
            'body': body,
            'icon': icon or '/static/images/icon-192.png',
            'badge': '/static/images/icon-192.png',
            'url': url or '/view_items/'
        }

        webpush(
            subscription_info=subscription_data,
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=settings.VAPID_CLAIMS
        )

        return True
    except WebPushException as e:
        print(f"WebPushException: {e}")
        # Remove invalid subscription
        if subscription:
            subscription.delete()
        return False
    except Exception as e:
        print(f"Push notification error: {e}")
        return False


# Helper function for OCR (adapted from existing barcode_scanner.py)
def scan_expiry_date_from_image(image):
    """Extract expiry date from image using OCR"""
    try:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=False)
        result = reader.readtext(image)

        detected_text = " ".join([res[1] for res in result])

        # Date patterns
        import re
        date_patterns = [
            r'(\d{1,2}\s*[A-Za-z]{3,9}\s*\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{2,4})',
            r'(\d{4}-\d{1,2}-\d{1,2})'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, detected_text)
            if match:
                date_str = match.group(1)
                try:
                    for fmt in ("%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            if 2000 <= parsed_date.year <= 2100:
                                return parsed_date.strftime("%d %b %Y")
                        except ValueError:
                            continue
                except Exception:
                    continue
        return None
    except Exception:
        return None
