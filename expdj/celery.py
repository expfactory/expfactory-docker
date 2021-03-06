from __future__ import absolute_import

import os

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expdj.settings')
expcelery = Celery('expdj')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
expcelery.config_from_object('django.conf:settings')
expcelery.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
