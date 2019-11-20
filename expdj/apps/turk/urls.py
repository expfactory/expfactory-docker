from django.conf.urls import url
from django.views.generic.base import TemplateView

from expdj.apps.experiments.views import sync
from expdj.apps.turk.api_views import (BatteryResultAPIList, WorkerExperiments,
                                       WorkerExperimentsFull)
from expdj.apps.turk.views import (clone_hit, contact_worker, delete_hit,
                                   edit_hit, end_assignment, expire_hit,
                                   finished_view, hit_detail, manage_hit,
                                   multiple_new_hit, not_consent_view,
                                   preview_hit, serve_hit, survey_submit)

urlpatterns = [
    # HITS
    url(r'^hits/(?P<bid>\d+|[A-Z]{8})/new$', edit_hit, name='new_hit'),
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
    url(
        r'^hits/(?P<bid>\d+|[A-Z]{8})/(?P<hid>\d+|[A-Z]{8})/clone$',
        clone_hit,
        name='clone_hit'
    ),
    url(
        r'hits/(?P<hid>\d+|[A-Z]{8})/detail$',
        hit_detail,
        name='hit_detail'
    ),
    url(r'^hits/(?P<hid>\d+|[A-Z]{8})/delete$', delete_hit, name='delete_hit'),
    url(r'^hits/(?P<hid>\d+|[A-Z]{8})/expire$', expire_hit, name='expire_hit'),

    # Turk Deployments
    url(r'^accept/(?P<hid>\d+|[A-Z]{8})', serve_hit, name='serve_hit'),
    url(r'^turk/(?P<hid>\d+|[A-Z]{8})', preview_hit, name='preview_hit'),
    url(r'^turk/preview', not_consent_view, name='not_consent_view'),
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
    url(r'^sync/(?P<rid>\d+|[A-Z]{8})/$', sync, name='sync_data'),
    url(r'^sync/$', sync, name='sync_data'),
    url(r'^finished$', finished_view, name="finished_view"),
    url(r'^worker/contact/(?P<aid>\d+)', contact_worker, name='contact_worker'),

    # New API
    url(
        r'^new_api/results/(?P<bid>\d+)/$',
        BatteryResultAPIList.as_view(),
        name='battery_result_api_list'
    ),
    url(
        r'^new_api/worker_experiments/(?P<worker_id>[A-Za-z0-9]+)/(?P<hit_id>[A-Za-z0-9]+)/$',
        WorkerExperiments.as_view(),
        name='worker_experiments'
    ),
    url(
        r'^new_api/worker_experiments/full/(?P<worker_id>[A-Za-z0-9]+)/(?P<bid>\d+|[A-Z]{8})/$',
        WorkerExperimentsFull.as_view(),
        name='worker_experiments_full'
    ),

]
