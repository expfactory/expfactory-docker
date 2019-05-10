"""
Django settings for expdj project.
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
import tempfile
from datetime import timedelta

try:
    from .secrets import *
except:
    from .bogus_secrets import *

import matplotlib
from celery import Celery
from kombu import Exchange, Queue

matplotlib.use('Agg')

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DOMAIN_NAME = "https://expfactory.org"  # MUST BE HTTPS FOR MECHANICAL TURK
DOMAIN_NAME_HTTP = "http://expfactory.org"  # MUST BE HTTPS FOR MECHANICAL TURK

ADMINS = (('rblair', 'rosswilsonblair@gmail.com'),)

MANAGERS = ADMINS

DEBUG = True
MTURK_ALLOW = False # Allow users to deploy to real Mturk (not just sandbox)
TEMPLATE_DEBUG = False
ALLOWED_HOSTS = ["*"]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
        'USER': 'postgres',
        'HOST': 'db',
        'PORT': '5432',
    }
}

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django_user_agents',
    'django.contrib.staticfiles',
    'django_extensions',
    'expdj.apps.main',
    'expdj.apps.turk',
    'expdj.apps.experiments',
    'expdj.apps.users',
    'crispy_forms',
    'polymorphic',
    'guardian',
    'dbbackup',
    'djcelery',
    'rest_framework',
    'rest_framework.authtoken',
)


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend'
)


MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
)


ROOT_URLCONF = 'expdj.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

WSGI_APPLICATION = 'expdj.wsgi.application'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
SITE_ID = 1
ANONYMOUS_USER_ID = -1  # django-guardian

# Static files (CSS, JavaScript, Images)
MEDIA_ROOT = './static'
MEDIA_URL = '/static/'
STATIC_ROOT = './assets'
STATIC_URL = '/assets/'
# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

SENDFILE_BACKEND = 'sendfile.backends.development'
PRIVATE_MEDIA_REDIRECT_HEADER = 'X-Accel-Redirect'
CRISPY_TEMPLATE_PACK = 'bootstrap3'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Celery config
BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_DEFAULT_QUEUE = 'default'
CELERY_QUEUES = (
    Queue('default', Exchange('default'), routing_key='default'),
)
CELERY_IMPORTS = ('expdj.apps.turk.tasks', )

# here is how to run a task regularly
# CELERYBEAT_SCHEDULE = {
#    'task name': {
#        'task': 'task_name',
#        'schedule': timedelta(days=1)
#    },
# }

CELERY_TIMEZONE = 'Europe/Berlin'

# REST FRAMEWORK
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
}

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# SSL ENABLED
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

EXP_REPO = os.path.join(BASE_DIR, 'expdj/experiment_repo')

# Local settings
try:
    from local_settings import *
except ImportError:
    pass
