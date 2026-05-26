FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=promptx_project.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

RUN python -m spacy download en_core_web_md

COPY . /app/

WORKDIR /app/backend

RUN python manage.py collectstatic --noinput

ENV PORT=10000
EXPOSE 10000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn promptx_project.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 2 --threads 4 --timeout 120"]
