from .views import experiments_view, edit_experiment, delete_experiment, add_experiment, view_experiments
from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # Experiments
    url(r'^experiments$', experiments_view, name="experiments"),
    url(r'^experiment/add$',add_experiment,name='add_experiment'),
    url(r'^experiments/(?P<eid>\d+|[A-Z]{8})/edit$',edit_experiment,name='edit_experiment'),
    url(r'^experiments/(?P<eid>\d+|[A-Z]{8})/$',view_experiment, name='experiment_details'),
    url(r'^experiments/(?P<eid>\d+|[A-Z]{8})/delete$',delete_experiment,name='delete_experiment'),
    url(r'^experiments/(?P<eid>\d+|[A-Z]{8})/export$',export_experiment,name='export_experiment')
)
