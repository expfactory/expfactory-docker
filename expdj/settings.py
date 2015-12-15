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
from kombu import Exchange, Queue
matplotlib.use('Agg')

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# MUST BE HTTPS FOR MECHANICAL TURK
DOMAIN_NAME = "brainmeta.org"

ADMINS = (('vsochat', 'vsochat@gmail.com'))

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
    'guardian',
    'dbbackup',
    'djrill'
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
)

ROOT_URLCONF = 'expdj.urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request',
)

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

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'hamlpy.template.loaders.HamlPyFilesystemLoader',
    'hamlpy.template.loaders.HamlPyAppDirectoriesLoader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
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

# Mandrill config
MANDRILL_API_KEY = "z2O_vfFUJB4L2yeF4Be9Tg" # this is a test key replace with a different one in production
EMAIL_BACKEND = "djrill.mail.backends.djrill.DjrillBackend"

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

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
