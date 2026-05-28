import os
import sys

# Update path to import from the backend directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from dotenv import load_dotenv
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/.env"))
load_dotenv(dotenv_path=dotenv_path)

settings.configure(
    EMAIL_BACKEND=os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"),
    EMAIL_HOST=os.getenv("EMAIL_HOST", ""),
    EMAIL_PORT=int(os.getenv("EMAIL_PORT") or 587),
    EMAIL_HOST_USER=os.getenv("EMAIL_HOST_USER", ""),
    EMAIL_HOST_PASSWORD=os.getenv("EMAIL_HOST_PASSWORD", ""),
    EMAIL_USE_TLS=os.getenv("EMAIL_USE_TLS", "true").lower() in ("true", "1", "yes"),
    EMAIL_USE_SSL=os.getenv("EMAIL_USE_SSL", "false").lower() in ("true", "1", "yes"),
    DEFAULT_FROM_EMAIL=os.getenv("DEFAULT_FROM_EMAIL", "PromptmaX <auth@janhelps.in>"),
)

test_email = os.getenv("SMTP_TEST_TO", "kartikresumes@gmail.com")
print(f"Testing SMTP sender through host: {settings.EMAIL_HOST}")

try:
    message = EmailMultiAlternatives(
        subject="PromptmaX SMTP Test",
        body="Testing PromptmaX SMTP email sender.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[test_email],
    )
    message.attach_alternative("<strong>Testing PromptmaX SMTP email sender.</strong>", "text/html")
    sent = message.send(fail_silently=False)
    print("Success! Emails sent:", sent)
except Exception as e:
    print("FAILED! Error details:", str(e))
