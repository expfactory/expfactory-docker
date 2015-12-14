import os
import sys	
os.environ['DJANGO_SETTINGS_MODULE'] = 'expdj.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
