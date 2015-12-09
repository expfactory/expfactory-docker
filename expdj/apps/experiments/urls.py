from .views import experiments_view, edit_experiment, delete_experiment, add_experiments, add_experiment, view_experiment, export_experiment, preview_experiment
from expdj import settings
from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # Experiments
    url(r'^experiments$', experiments_view, name="experiments"),
    url(r'^experiment/add$',add_experiment,name='add_experiment'),
    url(r'^experiments/add$',add_experiments,name='add_experiments'),
    url(r'^experiments/(?P<eid>.+?)/edit$',edit_experiment,name='edit_experiment'),
    url(r'^experiments/(?P<eid>.+?)/$',view_experiment, name='experiment_details'),
    url(r'^experiments/(?P<eid>.+?)/delete$',delete_experiment,name='delete_experiment'),
    url(r'^experiments/(?P<eid>.+?)/preview$',preview_experiment,name='preview_experiment'),
    url(r'^experiments/(?P<eid>.+?)/export$',export_experiment,name='export_experiment'))

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )
