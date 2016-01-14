from expdj.apps.turk.views import edit_hit, delete_hit, expire_hit, serve_hit, \
  multiple_new_hit, sync, end_assignment, finished_view
from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # HITS
    url(r'^hits/(?P<bid>\d+|[A-Z]{8})/new$',edit_hit,name='new_hit'),
    url(r'^hits/(?P<bid>\d+|[A-Z]{8})/multiple$',multiple_new_hit,name='multiple_new_hit'),
    url(r'^hits/(?P<bid>\d+|[A-Z]{8})/(?P<hid>\d+|[A-Z]{8})/edit$',edit_hit,name='edit_hit'),
    url(r'^hits/(?P<hid>\d+|[A-Z]{8})/delete$',delete_hit,name='delete_hit'),
    url(r'^hits/(?P<hid>\d+|[A-Z]{8})/expire$',expire_hit,name='expire_hit'),

    # Turk Deployments
    url(r'^turk/(?P<hid>\d+|[A-Z]{8})',serve_hit,name='serve_hit'),
    url(r'^turk/end/(?P<rid>\d+|[A-Z]{8})',end_assignment,name='end_assignment'),
    url(r'^sync/(?P<rid>\d+|[A-Z]{8})/$',sync,name='sync_data'),
    url(r'^sync/$',sync,name='sync_data'),
    url(r'^finished$', finished_view, name="finished_view")
)
