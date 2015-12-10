from expdj.apps.turk.views import turk_questions, edit_hit, view_hit, delete_hit
from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # HITS
    url(r'^hits/(?P<bid>\d+|[A-Z]{8})/new$',edit_hit,name='new_hit'),
    url(r'^hits/(?P<bid>\d+|[A-Z]{8})/(?P<hid>\d+|[A-Z]{8})/edit$',edit_hit,name='edit_hit'),
    url(r'^hits/(?P<hid>\d+|[A-Z]{8})/$',view_hit, name='hit_details'),
    url(r'^hits/(?P<hid>\d+|[A-Z]{8})/delete$',delete_hit,name='delete_hit'),

    # Turk Deployments
    url(r'^mturk$', turk_questions, name="turk_questions")
)
