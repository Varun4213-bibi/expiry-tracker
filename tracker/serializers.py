from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Item, UserProfile, Product


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['email_reminders_enabled']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'password2', 'profile']
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        return user


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'barcode', 'product_name']


class ItemSerializer(serializers.ModelSerializer):
    days_until_expiry = serializers.SerializerMethodField()
    expiry_status = serializers.SerializerMethodField()
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Item
        fields = [
            'id', 'name', 'category', 'barcode', 'expiry_date', 'notes',
            'added_date', 'user', 'donated', 'days_until_expiry', 'expiry_status', 'product_name'
        ]
        read_only_fields = ['user', 'added_date']

    def get_days_until_expiry(self, obj):
        return obj.days_until_expiry()

    def get_expiry_status(self, obj):
        days = obj.days_until_expiry()
        if days < 0:
            return 'expired'
        elif days <= 7:
            return 'expiring_soon'
        else:
            return 'safe'


class ItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['name', 'category', 'barcode', 'expiry_date', 'notes']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# NGO functionality removed - no NGO model exists
# class NGOSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = NGO
#         fields = ['id', 'name', 'district', 'contact_email', 'contact_phone', 'address']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = UserProfile
        fields = ['email_reminders_enabled', 'first_name', 'last_name', 'email']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()

        return super().update(instance, validated_data)


# OCR and Barcode API Serializers
class OCRRequestSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)


class OCRResponseSerializer(serializers.Serializer):
    expiry_date = serializers.DateField()
    confidence = serializers.FloatField()


class BarcodeRequestSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)


class BarcodeResponseSerializer(serializers.Serializer):
    barcode = serializers.CharField()
    product = ProductSerializer(read_only=True)


class DonationRequestSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    ngo_id = serializers.IntegerField()
    message = serializers.CharField(required=False, allow_blank=True)
