import os
import sys	
sys.path.append('/var/www/cogpheno')
os.environ['DJANGO_SETTINGS_MODULE'] = 'cogpheno.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
