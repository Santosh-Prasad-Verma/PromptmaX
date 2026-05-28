import logging
import uuid
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token

from .serializers_auth import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PlanSelectSerializer,
    RazorpayOrderSerializer,
    RazorpayVerifySerializer,
    RegisterSerializer,
    OTPVerifySerializer,
    ResendOTPSerializer,
)
from .models import PaymentOrder, UserPlan
from .utils.email import (
    generate_otp,
    send_otp_email,
    send_password_reset_otp_email,
    send_welcome_email,
)

logger = logging.getLogger('enhancer')

PLAN_CONFIG = {
    'free': {'label': 'Free', 'price_rs': 0},
    'pro': {'label': 'Pro', 'price_rs': 20},
    'pro_plus': {'label': 'Pro+', 'price_rs': 50},
}


def serialize_plan(user):
    try:
        selected = user.promptmax_plan
    except UserPlan.DoesNotExist:
        return None
    config = PLAN_CONFIG.get(selected.plan, {})
    return {
        'plan': selected.plan,
        'label': config.get('label', selected.get_plan_display()),
        'price_rs': selected.price_rs,
        'selected_at': selected.selected_at.isoformat() if selected.selected_at else None,
    }


def serialize_user(user):
    return {
        'email': user.email,
        'name': user.first_name,
        'plan': serialize_plan(user),
    }


def _razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise RuntimeError('RAZORPAY_NOT_CONFIGURED')
    try:
        import razorpay
    except ImportError as exc:
        raise RuntimeError('RAZORPAY_PACKAGE_MISSING') from exc
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


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
            logger.warning(f"Verification email failed for {email}: {msg}")
            user.delete()
            cache.delete(cache_key)
            return Response({
                'success': False,
                'error': 'EMAIL_DELIVERY_FAILED',
                'message': 'Could not send the verification email right now. Please try again later.',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({
            'success': True,
            'message': 'Registration initiated. Please verify your email with the code sent.',
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
            return Response({'success': False, 'error': 'Verification code expired or not found. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        if stored_otp != otp:
            return Response({'success': False, 'error': 'Invalid verification code'}, status=status.HTTP_400_BAD_REQUEST)

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
            'user': serialize_user(user),
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
            logger.warning(f"Verification email resend failed for {email}: {msg}")
            cache.delete(cache_key)
            return Response({
                'success': False,
                'error': 'EMAIL_DELIVERY_FAILED',
                'message': 'Could not send the verification email right now. Please try again later.',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({'success': True, 'message': 'New verification code sent to your email'}, status=status.HTTP_200_OK)


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
            'user': serialize_user(user),
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


class CurrentUserView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'success': True,
            'user': serialize_user(request.user),
        }, status=status.HTTP_200_OK)


class SelectPlanView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PlanSelectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': 'INVALID_REQUEST', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        plan = serializer.validated_data['plan']
        config = PLAN_CONFIG[plan]

        if plan != 'free':
            return Response({
                'success': False,
                'error': 'PAYMENT_REQUIRED',
                'message': 'Paid checkout is not connected yet. Select Free to continue now.',
                'plan': {
                    'plan': plan,
                    'label': config['label'],
                    'price_rs': config['price_rs'],
                },
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        selected, _ = UserPlan.objects.update_or_create(
            user=request.user,
            defaults={'plan': plan, 'price_rs': config['price_rs']},
        )
        return Response({
            'success': True,
            'message': 'Free plan selected.',
            'plan': serialize_plan(selected.user),
            'user': serialize_user(selected.user),
        }, status=status.HTTP_200_OK)


class RazorpayCreateOrderView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RazorpayOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': 'INVALID_REQUEST', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        plan = serializer.validated_data['plan']
        config = PLAN_CONFIG[plan]
        amount_paise = config['price_rs'] * 100

        try:
            client = _razorpay_client()
            receipt = f"pmx_{request.user.id}_{plan}_{uuid.uuid4().hex[:12]}"
            order = client.order.create({
                'amount': amount_paise,
                'currency': settings.RAZORPAY_CURRENCY,
                'receipt': receipt[:40],
                'payment_capture': 1,
                'notes': {
                    'user_id': str(request.user.id),
                    'email': request.user.email,
                    'plan': plan,
                },
            })
        except RuntimeError as exc:
            logger.warning("Razorpay configuration error: %s", exc)
            return Response({
                'success': False,
                'error': str(exc),
                'message': 'Payment checkout is not configured yet.',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:
            logger.exception("Razorpay order creation failed")
            return Response({
                'success': False,
                'error': 'RAZORPAY_ORDER_FAILED',
                'message': 'Could not start payment checkout right now.',
            }, status=status.HTTP_502_BAD_GATEWAY)

        PaymentOrder.objects.create(
            user=request.user,
            plan=plan,
            amount_rs=config['price_rs'],
            amount_paise=amount_paise,
            currency=settings.RAZORPAY_CURRENCY,
            razorpay_order_id=order['id'],
            raw_response=order,
        )

        return Response({
            'success': True,
            'key_id': settings.RAZORPAY_KEY_ID,
            'order': {
                'id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
            },
            'plan': {
                'plan': plan,
                'label': config['label'],
                'price_rs': config['price_rs'],
            },
            'user': serialize_user(request.user),
        }, status=status.HTTP_201_CREATED)


class RazorpayVerifyPaymentView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RazorpayVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': 'INVALID_REQUEST', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            payment = PaymentOrder.objects.get(
                user=request.user,
                razorpay_order_id=data['razorpay_order_id'],
                status=PaymentOrder.STATUS_CREATED,
            )
        except PaymentOrder.DoesNotExist:
            return Response({'success': False, 'error': 'Payment order not found or already used'}, status=status.HTTP_404_NOT_FOUND)

        try:
            client = _razorpay_client()
            client.utility.verify_payment_signature({
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature'],
            })
        except RuntimeError as exc:
            logger.warning("Razorpay verification configuration error: %s", exc)
            return Response({
                'success': False,
                'error': str(exc),
                'message': 'Payment verification is not configured yet.',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception:
            logger.warning("Razorpay signature verification failed for order %s", data['razorpay_order_id'])
            payment.status = PaymentOrder.STATUS_FAILED
            payment.razorpay_payment_id = data['razorpay_payment_id']
            payment.razorpay_signature = data['razorpay_signature']
            payment.save(update_fields=['status', 'razorpay_payment_id', 'razorpay_signature', 'updated_at'])
            return Response({'success': False, 'error': 'Payment verification failed'}, status=status.HTTP_400_BAD_REQUEST)

        payment.status = PaymentOrder.STATUS_PAID
        payment.razorpay_payment_id = data['razorpay_payment_id']
        payment.razorpay_signature = data['razorpay_signature']
        payment.save(update_fields=['status', 'razorpay_payment_id', 'razorpay_signature', 'updated_at'])

        config = PLAN_CONFIG[payment.plan]
        UserPlan.objects.update_or_create(
            user=request.user,
            defaults={'plan': payment.plan, 'price_rs': config['price_rs']},
        )
        request.user.refresh_from_db()

        return Response({
            'success': True,
            'message': f"{config['label']} plan activated.",
            'plan': serialize_plan(request.user),
            'user': serialize_user(request.user),
        }, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth_verify'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': 'INVALID_REQUEST', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        generic_response = {
            'success': True,
            'message': 'If an active account exists for this email, a reset code has been sent.',
        }

        if not User.objects.filter(email=email, is_active=True).exists():
            return Response(generic_response, status=status.HTTP_200_OK)

        otp = generate_otp()
        cache_key = f'password-reset-otp:{email}'
        cache.set(cache_key, otp, timeout=600)

        success, msg = send_password_reset_otp_email(email, otp)
        if not success:
            logger.warning(f"Password reset email failed for {email}: {msg}")
            cache.delete(cache_key)
            return Response({
                'success': False,
                'error': 'EMAIL_DELIVERY_FAILED',
                'message': 'Could not send the password reset email right now. Please try again later.',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(generic_response, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth_verify'

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': 'INVALID_REQUEST', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        password = serializer.validated_data['password']

        cache_key = f'password-reset-otp:{email}'
        stored_otp = cache.get(cache_key)
        if stored_otp is None:
            return Response({'success': False, 'error': 'Reset code expired or not found. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        if stored_otp != otp:
            return Response({'success': False, 'error': 'Invalid reset code'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'Active account not found'}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(password)
        user.save()
        cache.delete(cache_key)
        Token.objects.filter(user=user).delete()

        return Response({'success': True, 'message': 'Password reset successfully. Please sign in with your new password.'}, status=status.HTTP_200_OK)
