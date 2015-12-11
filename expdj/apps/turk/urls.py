from expdj.apps.turk.views import edit_hit, delete_hit, serve_hit
from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # HITS
    url(r'^hits/(?P<bid>\d+|[A-Z]{8})/new$',edit_hit,name='new_hit'),
    url(r'^hits/(?P<bid>\d+|[A-Z]{8})/(?P<hid>\d+|[A-Z]{8})/edit$',edit_hit,name='edit_hit'),
    url(r'^hits/(?P<hid>\d+|[A-Z]{8})/delete$',delete_hit,name='delete_hit'),

    # Turk Deployments
    url(r'^turk/(?P<hid>\d+|[A-Z]{8})',serve_hit,name='serve_hit'),
)
