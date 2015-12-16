from expdj.apps.experiments.views import experiments_view, edit_experiment_template, \
 delete_experiment_template, add_experiments_template, save_experiments_template, \
 view_experiment, export_experiment, preview_experiment, batteries_view, add_battery, \
 edit_battery, view_battery, delete_battery, export_battery, remove_experiment, \
 add_experiment, edit_experiment
from expdj import settings
from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url

urlpatterns = patterns('',

    # TODO Admin Views here

    # Experiment Templates
    url(r'^experiments$', experiments_view, name="experiments"),
    url(r'^experiments/save$',save_experiments_template,name='save_experiments_template'),
    url(r'^experiments/add$',add_experiments_template,name='add_experiments_template'),
    url(r'^experiments/(?P<eid>.+?)/edit$',edit_experiment_template,name='edit_experiment'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/(?P<eid>.+?)/$',view_experiment, name='experiment_details'),
    url(r'^experiments/(?P<eid>.+?)/delete$',delete_experiment_template,name='delete_experiment'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/(?P<eid>.+?)/remove$',remove_experiment,name='remove_experiment'),
    url(r'^experiments/(?P<eid>.+?)/preview$',preview_experiment,name='preview_experiment'),
    url(r'^experiments/(?P<eid>.+?)/export$',export_experiment,name='export_experiment'),
    # Experiments in Batteries
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/add$',add_experiment,name='add_experiment'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/(?P<eid>.+?)/edit$',edit_experiment,name='edit_experiment'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/(?P<eid>.+?)/$',view_experiment, name='experiment_details'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/(?P<eid>.+?)/remove$',remove_experiment,name='remove_experiment'),

    # Batteries
    url(r'^batteries/(?P<uid>\d+|[A-Z]{8})/$', batteries_view, name="batteries"),
    url(r'^batteries/new$',edit_battery,name='new_battery'),
    url(r'^batteries/add$',add_battery,name='add_battery'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/edit$',edit_battery,name='edit_battery'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/$',view_battery, name='battery_details'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/delete$',delete_battery,name='delete_battery'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/export$',export_battery,name='export_battery'))

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )
