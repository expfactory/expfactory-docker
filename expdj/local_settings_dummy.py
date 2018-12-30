DEBUG = True
TEMPLATE_DEBUG = True

# THIS MUST BE HTTPS
DOMAIN_NAME = "https://52.34.71.182:8000"

#CSRF_COOKIE_SECURE = False
#SESSION_COOKIE_SECURE = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'expfactory.db',
    }
}

# DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.postgresql_psycopg2',
#        'NAME': 'expfactory',
#        'USER': 'expfactory',
#        'PASSWORD':'expfactory',
#        'HOST': 'localhost',
#        'PORT': '5432',
#    }
# }

STATIC_ROOT = 'assets/'
STATIC_URL = '/assets/'
MEDIA_ROOT = 'static/'
MEDIA_URL = '/static/'
