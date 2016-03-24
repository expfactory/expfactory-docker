from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from rest_framework import routers, serializers, viewsets
from django.conf.urls import include, url, patterns
from django.http import Http404, HttpResponse
from django.conf.urls.static import static
from expdj.apps.turk.models import Result, Worker
from expdj.apps.experiments.models import Battery, ExperimentTemplate, CognitiveAtlasTask
from expdj.apps.main import urls as main_urls
from expdj.apps.turk import urls as turk_urls
from expdj.apps.users import urls as users_urls
from expdj.apps.experiments import urls as experiment_urls
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from expdj.apps.turk.utils import to_dict
import os

# Seriailizers define the API representation
class BatterySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Battery
        fields = ('name', 'description')

class CognitiveAtlasTaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CognitiveAtlasTask
        fields = ('name','cog_atlas_id')

class ExperimentTemplateSerializer(serializers.HyperlinkedModelSerializer):
    cognitive_atlas_task = CognitiveAtlasTaskSerializer()
    class Meta:
        model = ExperimentTemplate
        fields = ('exp_id', 'name', 'cognitive_atlas_task', 'reference')

class WorkerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Worker
        fields = ["id"]   

class ResultSerializer(serializers.HyperlinkedModelSerializer):
    experiment = ExperimentTemplateSerializer()
    battery = BatterySerializer()
    worker = WorkerSerializer()
    data = serializers.SerializerMethodField('get_taskdata')

    def get_taskdata(self,result):
        return to_dict(result.taskdata)

    class Meta:
        model = Result
        fields = ('data', 'experiment', 'battery', 'worker','language','browser','platform','completed','datetime')


# ViewSets define the view behavior.
class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'api/results', ResultViewSet)

admin.autodiscover()

urlpatterns = [ url(r'^', include(main_urls)),
                url(r'^', include(turk_urls)),
                url(r'^', include(experiment_urls)),
                url(r'^accounts/', include(users_urls)),
                url(r'^', include(router.urls)),
                url(r'^api/', include('rest_framework.urls', namespace='rest_framework')),
                url(r'^admin/', include(admin.site.urls))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += patterns(
        '',
        url(r'^(?P<path>favicon\.ico)$', 'django.views.static.serve', {
            'document_root': settings.STATIC_ROOT}),
    )
