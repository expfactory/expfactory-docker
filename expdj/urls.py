import os

from django.conf import settings
# Custom error views
from django.conf.urls import handler404, handler500, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.sitemaps.views import index, sitemap
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import Http404, HttpResponse
from rest_framework import routers, serializers, viewsets

# Sitemaps
from expdj.api.sitemap import (ExperimentTemplateSitemap, GameTemplateSitemap,
                               SurveyTemplateSitemap)
from expdj.apps.experiments import urls as experiment_urls
from expdj.apps.experiments.models import (Battery, CognitiveAtlasTask,
                                           ExperimentTemplate)
from expdj.apps.main import urls as main_urls
from expdj.apps.turk import urls as turk_urls
from expdj.apps.turk.models import Result, Worker
from expdj.apps.turk.utils import to_dict
from expdj.apps.users import urls as users_urls

sitemaps = {"experiments": ExperimentTemplateSitemap,
            "surveys": SurveyTemplateSitemap,
            "games": GameTemplateSitemap}

# Configure custom error pages
handler404 = 'expdj.apps.main.views.handler404'
handler500 = 'expdj.apps.main.views.handler500'

# Seriailizers define the API representation


class BatterySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Battery
        fields = ('name', 'description')


class CognitiveAtlasTaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CognitiveAtlasTask
        fields = ('name', 'cog_atlas_id')


class ExperimentTemplateSerializer(serializers.HyperlinkedModelSerializer):
    cognitive_atlas_task = CognitiveAtlasTaskSerializer()

    class Meta:
        model = ExperimentTemplate
        fields = (
            'exp_id',
            'name',
            'cognitive_atlas_task',
            'reference',
            'version',
            'template')


class WorkerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Worker
        fields = ["id"]


class ResultSerializer(serializers.HyperlinkedModelSerializer):
    experiment = ExperimentTemplateSerializer()
    battery = BatterySerializer()
    worker = WorkerSerializer()
    data = serializers.SerializerMethodField('get_taskdata')

    def get_taskdata(self, result):
        return to_dict(result.taskdata)

    class Meta:
        model = Result
        fields = (
            'data',
            'experiment',
            'battery',
            'worker',
            'language',
            'browser',
            'platform',
            'completed',
            'finishtime')


# ViewSets define the view behavior.
class ResultViewSet(viewsets.ModelViewSet):
    serializer_class = ResultSerializer
    def get_queryset(self):
        return Result.objects.filter(battery__owner=self.request.user.pk)


# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'api/results', ResultViewSet, base_name='all-results')

admin.autodiscover()

urlpatterns = [url(r'^', include(main_urls)),
               url(r'^', include(turk_urls)),
               url(r'^', include(experiment_urls)),
               url(r'^accounts/', include(users_urls)),
               url(r'^', include(router.urls)),
               url(r'^sitemap\.xml$', index, {'sitemaps': sitemaps}),
               url(r'^sitemap-(?P<section>.+)\.xml$', sitemap, {'sitemaps': sitemaps}),
               url(r'^api/', include('rest_framework.urls', namespace='rest_framework')),
               url(r'^admin/', admin.site.urls),
               ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    '''
    urlpatterns += [
        url(r'^(?P<path>favicon\.ico)$', 'django.views.static.serve', {
            'document_root': settings.STATIC_ROOT}),
    ]
    '''
    urlpatterns += staticfiles_urlpatterns()
