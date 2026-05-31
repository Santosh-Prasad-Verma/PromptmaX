import jwt
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework import exceptions

User = get_user_model()
logger = logging.getLogger('enhancer')

class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        token = parts[1]
        
        # 1. Fetch Supabase JWT Secret
        secret = getattr(settings, 'SUPABASE_JWT_SECRET', '')
        if not secret:
            # If no secret is configured, bypass this authenticator
            return None

        # 2. Decode the JWT token
        try:
            # Try with standard Supabase audience 'authenticated'
            payload = jwt.decode(
                token,
                secret,
                algorithms=['HS256'],
                options={"verify_aud": True},
                audience="authenticated"
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidAudienceError:
            # Fallback in case of customized/missing audience
            try:
                payload = jwt.decode(
                    token,
                    secret,
                    algorithms=['HS256'],
                    options={"verify_aud": False}
                )
            except Exception as e:
                raise exceptions.AuthenticationFailed(f'Invalid token audience or signature: {str(e)}')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')

        # 3. Retrieve user identifier and email
        sub = payload.get('sub')
        email = payload.get('email')

        if not sub:
            raise exceptions.AuthenticationFailed('Token is missing user identifier (sub)')

        # If email is not present, use a fallback
        if not email:
            email = f"{sub}@supabase.local"

        # 4. Get or provision the user in Django
        try:
            # First, check by email (standard in our system)
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # If not found by email, check if we have a user with username sb_<sub[:30]>
            username = f"sb_{sub[:27]}" # Max username length in Django is 150, sub is a UUID (36 chars)
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                # Provision a new user
                user_metadata = payload.get('user_metadata', {}) or {}
                name = user_metadata.get('full_name') or user_metadata.get('name') or 'Supabase User'
                
                # Check if username is already taken by email, if so modify it
                if User.objects.filter(username=email).exists():
                    django_username = username
                else:
                    django_username = email

                user = User.objects.create_user(
                    username=django_username,
                    email=email,
                    first_name=name[:150],
                    is_active=True
                )
                # Set an unusable password since they are authenticated via Supabase SSO
                user.set_unusable_password()
                user.save()
                
                # Setup a default UserPlan (Free) for this user to be consistent
                from enhancer.models import UserPlan
                UserPlan.objects.get_or_create(
                    user=user,
                    defaults={'plan': 'free', 'price_rs': 0}
                )
                logger.info(f"Successfully provisioned new Supabase user: {email} ({sub})")

        return (user, token)
