import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "promptx_project.settings")

app = Celery("promptrix")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
