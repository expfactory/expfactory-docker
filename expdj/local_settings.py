#import os
DEBUG = True
TEMPLATE_DEBUG = True

DOMAIN_NAME="http://127.0.0.1"

#CSRF_COOKIE_SECURE = False
#SESSION_COOKIE_SECURE = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'expfactory.db',
    }
}

STATIC_ROOT = 'assets/'
STATIC_URL = '/assets/'
MEDIA_ROOT = 'static/'
MEDIA_URL  = '/static/'

