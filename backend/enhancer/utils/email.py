import os
import random
import string
import resend
from django.template.loader import render_to_string

FROM_EMAIL = "PromptX <auth@janhelps.in>"


def get_resend_key():
    return os.getenv("RESEND_API_KEY")


def send_welcome_email(user_email, user_name):
    resend.api_key = get_resend_key()
    if not resend.api_key or resend.api_key == "re_your_resend_api_key_here":
        return False
    html_content = render_to_string('emails/welcome.html', {
        'user_name': user_name,
        'user_email': user_email,
    })
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": user_email,
            "subject": "PROMPTX // Identity Confirmed",
            "html": html_content,
        })
        return True
    except Exception:
        return False


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email, otp):
    api_key = get_resend_key()
    resend.api_key = api_key
    if not api_key or api_key == "re_your_resend_api_key_here":
        return False, "API Key Missing"
    html_content = render_to_string('emails/otp.html', {
        'otp': otp,
        'user_email': email,
    })
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": email,
            "subject": f"PROMPTX // Verification Code: {otp}",
            "html": html_content,
        })
        return True, "Success"
    except Exception as e:
        return False, str(e)
