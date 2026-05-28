import random
import string
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger('enhancer')


def is_email_configured():
    if 'smtp.EmailBackend' not in settings.EMAIL_BACKEND:
        return True
    return bool(
        settings.EMAIL_HOST
        and settings.EMAIL_HOST_USER
        and settings.EMAIL_HOST_PASSWORD
        and settings.DEFAULT_FROM_EMAIL
    )


def send_html_email(user_email, subject, template_name, context):
    if not is_email_configured():
        return False, "SMTP email configuration is missing"

    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content) or subject

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )
        message.attach_alternative(html_content, "text/html")
        message.send(fail_silently=False)
        return True, "Success"
    except Exception as exc:
        logger.warning("SMTP email failed for %s: %s", user_email, exc)
        return False, str(exc)


def send_welcome_email(user_email, user_name):
    success, _ = send_html_email(
        user_email=user_email,
        subject="PromptmaX - Identity confirmed",
        template_name='emails/welcome.html',
        context={
            'user_name': user_name,
            'user_email': user_email,
        },
    )
    return success


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email, otp):
    return send_html_email(
        user_email=email,
        subject=f"PromptmaX verification code: {otp}",
        template_name='emails/otp.html',
        context={
            'otp': otp,
            'user_email': email,
        },
    )


def send_password_reset_otp_email(email, otp):
    return send_html_email(
        user_email=email,
        subject=f"PromptmaX password reset code: {otp}",
        template_name='emails/password_reset_otp.html',
        context={
            'otp': otp,
            'user_email': email,
        },
    )
