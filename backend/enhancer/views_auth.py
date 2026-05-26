import logging
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token

from .serializers_auth import (
    LoginSerializer,
    RegisterSerializer,
    OTPVerifySerializer,
    ResendOTPSerializer,
)
from .utils.email import send_otp_email, generate_otp, send_welcome_email

logger = logging.getLogger('enhancer')


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth_register'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': 'INVALID_REQUEST', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        name = serializer.validated_data.get('name', '')

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            if user.is_active:
                return Response({'success': False, 'error': 'Email already registered'}, status=status.HTTP_409_CONFLICT)
            user.delete()

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
            is_active=False,
        )

        otp = generate_otp()
        cache_key = f'otp:{email}'
        cache.set(cache_key, otp, timeout=600)

        success, msg = send_otp_email(email, otp)
        if not success:
            logger.warning(f"OTP email failed for {email}: {msg}")

        return Response({
            'success': True,
            'message': 'Registration initiated. Please verify your email with the OTP sent.',
        }, status=status.HTTP_201_CREATED)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth_verify'

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': 'INVALID_REQUEST', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        cache_key = f'otp:{email}'
        stored_otp = cache.get(cache_key)

        if stored_otp is None:
            return Response({'success': False, 'error': 'OTP expired or not found. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        if stored_otp != otp:
            return Response({'success': False, 'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(cache_key)

        try:
            user = User.objects.get(email=email, is_active=False)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        user.is_active = True
        user.save()

        send_welcome_email(email, user.first_name or 'Operator')

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'message': 'Email verified successfully',
            'token': token.key,
        }, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth_verify'

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': 'INVALID_REQUEST', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']

        if not User.objects.filter(email=email, is_active=False).exists():
            return Response({'success': False, 'error': 'No pending registration found for this email'}, status=status.HTTP_404_NOT_FOUND)

        otp = generate_otp()
        cache_key = f'otp:{email}'
        cache.set(cache_key, otp, timeout=600)

        success, msg = send_otp_email(email, otp)
        if not success:
            logger.warning(f"OTP resend failed for {email}: {msg}")

        return Response({'success': True, 'message': 'New OTP sent to your email'}, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': 'INVALID_REQUEST', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({'success': False, 'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'success': False, 'error': 'Account not verified. Please verify your email first.'}, status=status.HTTP_403_FORBIDDEN)

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'success': True,
            'message': 'Login successful',
            'token': token.key,
            'user': {
                'email': user.email,
                'name': user.first_name,
            },
        }, status=status.HTTP_200_OK)


class TokenObtainView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({'success': False, 'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_200_OK)
