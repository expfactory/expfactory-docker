from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls import patterns, include, url
from django.http import Http404, HttpResponse
from django.conf.urls.static import static
from django.conf import settings
import os

from django import template
template.add_to_builtins('django.templatetags.future')
template.add_to_builtins('django.contrib.staticfiles.templatetags.staticfiles')

urlpatterns = patterns('',
                       url('', include('social.apps.django_app.urls', namespace='social')),
                       url(r'^', include('expdj.apps.main.urls')),
                       url(r'^', include('expdj.apps.experiments.urls')),
                       url(r'^', include('expdj.apps.turk.urls')),
                       url(r'^accounts/', include('expdj.apps.users.urls')))
if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^(?P<path>favicon\.ico)$', 'django.views.static.serve', {
            'document_root': os.path.join(settings.STATIC_ROOT,'images')}),
    )
