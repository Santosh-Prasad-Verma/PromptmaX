from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, max_length=128)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128)
    name = serializers.CharField(max_length=150, required=False)

    def validate_password(self, value):
        validate_password(value)
        return value


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)
    password = serializers.CharField(min_length=8, max_length=128)

    def validate_password(self, value):
        validate_password(value)
        return value


class PlanSelectSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=['free', 'pro', 'pro_plus'])


class RazorpayOrderSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=['pro', 'pro_plus'])


class RazorpayVerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=120)
    razorpay_payment_id = serializers.CharField(max_length=120)
    razorpay_signature = serializers.CharField(max_length=255)
