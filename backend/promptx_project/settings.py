import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent  

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    # Only allow in dev to prevent silent production misconfigurations
    if os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes'):
        SECRET_KEY = 'django-insecure-promptx-dev-key-change-in-production'
    else:
        raise RuntimeError('DJANGO_SECRET_KEY environment variable is required')

DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'social_django',
    'enhancer',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'enhancer.middleware.RequestLoggingMiddleware',
]

if DEBUG:
    MIDDLEWARE.insert(0, 'django.middleware.gzip.GZipMiddleware')
else:
    MIDDLEWARE.insert(0, 'django.middleware.gzip.GZipMiddleware')

AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('GOOGLE_OAUTH2_CLIENT_ID', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('GOOGLE_OAUTH2_CLIENT_SECRET', '')
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False
SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_FIELDS_STORED_IN_SESSION = ['state']
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
    'access_type': 'offline',
    'approval_prompt': 'force',
}
SOCIAL_AUTH_REQUESTS_TIMEOUT = 10
SOCIAL_AUTH_CONNECT_TIMEOUT = 10
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'enhancer.pipeline.send_welcome_email_pipeline',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

LOGIN_REDIRECT_URL = '/choose/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

ROOT_URLCONF = 'promptx_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR.parent,  # project root (index.html lives here)
            os.path.join(BASE_DIR.parent, 'frontend'),
            os.path.join(BASE_DIR.parent, 'frontend', 'pages'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'promptx_project.wsgi.application'

# Database
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL:
    import dj_database_url
    DATABASES = {'default': dj_database_url.config(conn_max_age=600, ssl_require=False)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
    }

# Cache
REDIS_URL = os.getenv('REDIS_URL', '')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
        },
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'promptx-cache',
        },
    }

# Celery — async task queue
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL or "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL or "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", 300))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", 240))
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '100/minute',
        'auth_register': '3/10minutes',
        'auth_verify': '5/minute',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'enhancer.exceptions.custom_exception_handler',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# CORS
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'false').lower() == 'true'
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8000').split(',')
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-key',
]
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']

CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000').split(',')

# Security (enabled in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'same-origin'

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

PORT = int(os.getenv('PORT', 8000))

# PromptX-specific configuration
PROMPTX = {
    'MIN_INPUT_LENGTH': 3,
    'MAX_INPUT_LENGTH': 10000,
    'PIPELINE': {
        'ENABLE_ITERATIVE_REFINEMENT': True,
        'TARGET_QUALITY_SCORE': 0.85,
        'MAX_REFINEMENT_ITERATIONS': 3,
        'ENABLE_FACT_CHECK': os.getenv('ENABLE_FACT_CHECK', 'True').lower() in ('true', '1'),
        'ENABLE_URL_VALIDATION': os.getenv('ENABLE_URL_VALIDATION', 'False').lower() in ('true', '1'),
    },
    'VALIDATION': {
        'CHECK_URL_VALIDITY': os.getenv('CHECK_URL_VALIDITY', 'False').lower() in ('true', '1'),
        'CHECK_CODE_SYNTAX': True,
        'CHECK_LOGICAL_CONSISTENCY': True,
        'URL_TIMEOUT': 5,
        'MAX_URL_CHECKS': 5,
    },
    'SCRAPER': {
        'MAX_PAGES': int(os.getenv('SCRAPER_MAX_PAGES', 8)),
        'CHARS_PER_PAGE': int(os.getenv('SCRAPER_CHARS_PER_PAGE', 6000)),
        'REQUEST_TIMEOUT': int(os.getenv('SCRAPER_TIMEOUT', 12)),
    },
    'AI_CLIENT': {
        'REQUEST_TIMEOUT': int(os.getenv('AI_REQUEST_TIMEOUT', 30)),
        'MAX_TOKENS': int(os.getenv('AI_MAX_TOKENS', 8192)),
        'RETRY_COUNT': int(os.getenv('AI_RETRY_COUNT', 1)),
        'CACHE_SIZE': int(os.getenv('AI_CACHE_SIZE', 500)),
    },
    'SCORING_WEIGHTS': {
        'clarity': 0.20,
        'specificity': 0.20,
        'completeness': 0.18,
        'structure': 0.16,
        'actionability': 0.16,
        'grammar': 0.10,
    },
}

# Sentry
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', 0.1)),
        send_default_pii=False,
        environment=os.getenv('SENTRY_ENVIRONMENT', 'development'),
    )

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
JSON_LOGGER_AVAILABLE = False
try:
    import pythonjsonlogger  # noqa
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    pass

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'enhancer': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

if JSON_LOGGER_AVAILABLE and not DEBUG:
    LOGGING['formatters']['json'] = {
        '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        'format': '%(timestamp)s %(level)s %(name)s %(message)s',
    }
    LOGGING['handlers']['console']['formatter'] = 'json'
