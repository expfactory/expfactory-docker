from expdj.apps.turk.views import (edit_hit, delete_hit, expire_hit,
    preview_hit, serve_hit, multiple_new_hit, end_assignment, finished_view,
    not_consent_view, survey_submit, manage_hit, contact_worker)
from expdj.apps.experiments.views import sync
from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url
from django.views.generic.base import TemplateView

from expdj.apps.experiments.views import sync
from expdj.apps.turk.api_views import ResultAPIList, BatteryResultAPIList
from expdj.apps.turk.views import (
    edit_hit, delete_hit, expire_hit, preview_hit, serve_hit, multiple_new_hit,
    end_assignment, finished_view, not_consent_view, survey_submit, manage_hit,
    clone_hit
)


urlpatterns = patterns('',
    # HITS
    url(r'^hits/(?P<bid>\d+|[A-Z]{8})/new$',edit_hit,name='new_hit'),
    url(
        r'^hits/(?P<bid>\d+|[A-Z]{8})/(?P<hid>\d+|[A-Z]{8})/manage$',
        manage_hit,
        name='manage_hit'
    ),
    url(
        r'^hits/(?P<bid>\d+|[A-Z]{8})/multiple$',
        multiple_new_hit,
        name='multiple_new_hit'
    ),
    url(
        r'^hits/(?P<bid>\d+|[A-Z]{8})/(?P<hid>\d+|[A-Z]{8})/edit$',
        edit_hit,
        name='edit_hit'
    ),
    url(r'^hits/(?P<hid>\d+|[A-Z]{8})/delete$',delete_hit,name='delete_hit'),
    url(r'^hits/(?P<hid>\d+|[A-Z]{8})/expire$',expire_hit,name='expire_hit'),

    # Turk Deployments
    url(r'^accept/(?P<hid>\d+|[A-Z]{8})',serve_hit,name='serve_hit'),
    url(r'^turk/(?P<hid>\d+|[A-Z]{8})',preview_hit,name='preview_hit'),
    url(r'^turk/preview',not_consent_view,name='not_consent_view'),
    url(
        r'^turk/end/(?P<rid>\d+|[A-Z]{8})',
        end_assignment,
        name='end_assignment'
    ),
    url(
        r'^surveys/(?P<rid>\d+|[A-Z]{8})/(?P<hid>[A-Za-z0-9]{30})/submit$',
        survey_submit,
        name='survey_submit'
    ),
    url(r'^sync/(?P<rid>\d+|[A-Z]{8})/$',sync,name='sync_data'),
    url(r'^sync/$',sync,name='sync_data'),
    url(r'^finished$', finished_view, name="finished_view"),
    url(r'^worker/contact/(?P<aid>\d+)',contact_worker,name='contact_worker')

    #  API
    url(r'^api_/results/$', ResultAPIList.as_view(), name='result_api_list'),
    url(
        r'^api_/results/(?P<bid>\d+)/$',
        BatteryResultAPIList.as_view(),
        name='battery_result_api_list'
    )
)
