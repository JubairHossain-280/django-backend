# users/serializers.py
from django.db import transaction
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        if hasattr(user, "profile"):
            token["first_name"] = user.profile.first_name
            token["last_name"] = user.profile.last_name
        return token

    def validate(self, attrs):
        # Custom validation that uses email instead of username
        credentials = {"email": attrs.get("email"), "password": attrs.get("password")}
        user = User.objects.filter(email=credentials["email"]).first()
        if user is None or not user.check_password(credentials["password"]):
            raise serializers.ValidationError("Invalid email or password")
        data = super().validate(credentials)
        return {
            "token": {
                "accessToken": data["access"],
                "refreshToken": data["refresh"],
            },
            "user": UserWithProfileSerializer(self.user).data,
        }


class UserRegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=150, write_only=True)
    last_name = serializers.CharField(max_length=150, write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email", "password")

    def create(self, validated_data):
        first_name = validated_data.pop("first_name", "")
        last_name = validated_data.pop("last_name", "")
        email = validated_data.pop("email")
        password = validated_data.pop("password")

        with transaction.atomic():
            user = User.objects.create_user(email=email, password=password)
            profile = user.profile
            profile.first_name = first_name
            profile.last_name = last_name
            profile.save(update_fields=["first_name", "last_name"])
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "role",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("id", "first_name", "last_name", "phone")
        read_only_fields = ("id",)


class UserWithProfileSerializer(serializers.ModelSerializer):
    """Serializer that nests the related Profile data inside the User representation."""
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "role",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
            "profile",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CustomTokenRefreshSerializer(serializers.Serializer):
    """Refresh serializer using camelCase `refreshToken` and `accessToken` keys."""
    refreshToken = serializers.CharField()

    def validate(self, attrs):
        serializer = TokenRefreshSerializer(data={"refresh": attrs["refreshToken"]})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = {"accessToken": data["access"]}
        if "refresh" in data:
            result["refreshToken"] = data["refresh"]
        return result


class LogoutSerializer(serializers.Serializer):
    refreshToken = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs["refreshToken"]
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except Exception:
            raise serializers.ValidationError("Token is invalid or already blacklisted")
