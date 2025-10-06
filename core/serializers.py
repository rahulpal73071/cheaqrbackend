from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import AllowedEmail, UserItemStatus, StatusChoices, QRToken, Menu

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if not AllowedEmail.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is not pre-approved by admin.")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        full_name = validated_data.pop('full_name', '')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=full_name
        )
        # ❌ no auto init with hardcoded items anymore
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'public_id', 'username', 'email', 'first_name', 'last_name', 'is_staff')


class UserItemStatusSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = UserItemStatus
        fields = ('item', 'item_name', 'status', 'updated_at')


class QRTokenSerializer(serializers.Serializer):
    data = serializers.CharField()
    expires_at = serializers.DateTimeField()


class AdminScanResolveSerializer(serializers.Serializer):
    qr = serializers.CharField()


class AdminActionSerializer(serializers.Serializer):
    qr = serializers.CharField()
    item = serializers.IntegerField()  # Menu ID
    status = serializers.ChoiceField(choices=StatusChoices.choices)


# ✅ NEW
class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = "__all__"
