from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from rest_framework import routers, serializers, viewsets
from django.conf.urls import include, url, patterns
from django.http import Http404, HttpResponse
from django.conf.urls.static import static
from expdj.apps.turk.models import Result
from expdj.apps.main import urls as main_urls
from expdj.apps.turk import urls as turk_urls
from expdj.apps.users import urls as users_urls
from expdj.apps.experiments import urls as experiment_urls
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
import os

# Serializers define the API representation.
class ResultSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Result
        fields = ('taskdata', 'experiment', 'battery', 'worker','language','browser','platform','completed','datetime')

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
