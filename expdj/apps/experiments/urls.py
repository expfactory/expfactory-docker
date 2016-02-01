from expdj.apps.experiments.views import experiments_view, edit_experiment_template, \
delete_experiment_template, add_experiment_template, save_experiment_template, \
view_experiment, export_experiment, preview_experiment, batteries_view, add_battery, \
edit_battery, view_battery, delete_battery, export_battery, remove_experiment, \
add_experiment, edit_experiment, save_experiment, update_experiment_templates, \
remove_condition, serve_battery, generate_battery_user, localsync
from expdj import settings
from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url

urlpatterns = patterns('',

    # Experiment Templates
    url(r'^experiments$', experiments_view, name="experiments"),
    url(r'^experiments/save$',save_experiment_template,name='save_experiment_template'),
    url(r'^experiments/add$',add_experiment_template,name='add_experiment_template'),
    url(r'^experiments/update$',update_experiment_templates,name='update_experiment_templates'),
    url(r'^experiments/(?P<eid>.+?)/edit$',edit_experiment_template,name='edit_experiment_template'),
    url(r'^experiments/(?P<eid>.+?)/$',view_experiment, name='experiment_details'),
    url(r'^experiments/(?P<eid>.+?)/delete$',delete_experiment_template,name='delete_experiment'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/(?P<eid>.+?)/remove$',remove_experiment,name='remove_experiment'),
    url(r'^experiments/(?P<eid>.+?)/preview$',preview_experiment,name='preview_experiment'),
    url(r'^experiments/(?P<eid>.+?)/export$',export_experiment,name='export_experiment'),

    # Experiments in Batteries
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/add$',add_experiment,name='add_experiment'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/save$',save_experiment,name='save_experiment'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/(?P<eid>\d+|[A-Z]{8})/customize$',edit_experiment,name='edit_experiment'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/(?P<eid>\d+|[A-Z]{8})/view$',view_experiment, name='experiment_details'),
    url(r'^experiments/(?P<bid>\d+|[A-Z]{8})/(?P<eid>\d+|[A-Z]{8})/remove$',remove_experiment,name='remove_experiment'),
    url(r'^conditions/(?P<bid>\d+|[A-Z]{8})/(?P<eid>\d+|[A-Z]{8})/(?P<cid>\d+|[A-Z]{8})/remove$',remove_condition,name='remove_condition'),

    # Batteries
    url(r'^batteries/$', batteries_view, name="batteries"),
    url(r'^my-batteries/(?P<uid>\d+|[A-Z]{8})/$', batteries_view, name="batteries"),
    url(r'^batteries/new$',edit_battery,name='new_battery'),
    url(r'^batteries/add$',add_battery,name='add_battery'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/edit$',edit_battery,name='edit_battery'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/user$',generate_battery_user,name='generate_battery_user'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/serve$',serve_battery,name='serve_battery'), # preview
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/(?P<userid>\d+|[A-Za-z0-9-]{36})/serve$',serve_battery,name='serve_battery'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/$',view_battery, name='battery_details'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/delete$',delete_battery,name='delete_battery'),
    url(r'^batteries/(?P<bid>\d+|[A-Z]{8})/export$',export_battery,name='export_battery'),
    url(r'^local/(?P<rid>\d+|[A-Z]{8})/$',localsync,name='local'),
    url(r'^local/$',localsync,name='local')) # local sync of data

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )
