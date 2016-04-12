"""
Django settings for expdj project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
from datetime import timedelta
import matplotlib
import tempfile
from celery import Celery
from kombu import Exchange, Queue
matplotlib.use('Agg')

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DOMAIN_NAME = "https://expfactory.org" # MUST BE HTTPS FOR MECHANICAL TURK
DOMAIN_NAME_HTTP = "http://expfactory.org" # MUST BE HTTPS FOR MECHANICAL TURK

ADMINS = (('vsochat', 'vsochat@gmail.com'),)

MANAGERS = ADMINS

# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

DEBUG = False
TEMPLATE_DEBUG = False
ALLOWED_HOSTS = ["*"]

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

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
    'django_user_agents',
    'django.contrib.staticfiles',
    'django_extensions',
    'expdj.apps.main',
    'expdj.apps.turk',
    'expdj.apps.experiments',
    'expdj.apps.users',
    'social.apps.django_app.default',
    'crispy_forms',
    'polymorphic',
    'guardian',
    'dbbackup',
    'djrill',
    'djcelery',
    'rest_framework',
    'rest_framework.authtoken',
    'opbeat.contrib.django',
)


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.google.GoogleOAuth2',
    'guardian.backends.ObjectPermissionBackend'
)

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.get_username',
    'social.pipeline.social_auth.associate_by_email',  # <--- enable this one
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details'
)

SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']


MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
    'opbeat.contrib.django.middleware.OpbeatAPMMiddleware',
)

ROOT_URLCONF = 'expdj.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': (),
        'OPTIONS': {'context_processors': ("django.contrib.auth.context_processors.auth",
                                            "django.core.context_processors.debug",
                                            "django.core.context_processors.i18n",
                                            "django.core.context_processors.media",
                                            "django.core.context_processors.static",
                                            "django.core.context_processors.tz",
                                            "django.contrib.messages.context_processors.messages",
                                            'django.core.context_processors.request'),
                    'loaders': ('django.template.loaders.filesystem.Loader',
                                'django.template.loaders.app_directories.Loader',
                                )}
    }
]

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

WSGI_APPLICATION = 'expdj.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
SITE_ID = 1
ANONYMOUS_USER_ID = -1 # django-guardian

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

MEDIA_ROOT = '/var/www/static'
MEDIA_URL = '/static/'
STATIC_ROOT = '/var/www/assets'
STATIC_URL = '/assets/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

#STATICFILES_DIRS = (
#    ('site', os.path.join(BASE_DIR,'static')), #store site-specific media here.
#)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

SENDFILE_BACKEND = 'sendfile.backends.development'
PRIVATE_MEDIA_REDIRECT_HEADER = 'X-Accel-Redirect'
CRISPY_TEMPLATE_PACK = 'bootstrap3'

CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
}

# Mandrill config
MANDRILL_API_KEY = "z2O_vfFUJB4L2yeF4Be9Tg" # this is a test key replace with a different one in production
EMAIL_BACKEND = "djrill.mail.backends.djrill.DjrillBackend"

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
#CELERYBEAT_SCHEDULE = {
#    'task name': {
#        'task': 'task_name',
#        'schedule': timedelta(days=1)
#    },
#}

CELERY_TIMEZONE = 'Europe/Berlin'

# REST FRAMEWORK
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissions',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'PAGE_SIZE':10,
}

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# SSL ENABLED
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

# Bogus secret key.
try:
    from secrets import *
except ImportError:
    from bogus_secrets import *

# Local settings
try:
    from local_settings import *
except ImportError:
    pass
