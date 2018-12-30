from django.contrib.sitemaps import Sitemap

from expdj.apps.experiments.models import ExperimentTemplate
from expdj.apps.experiments.utils import get_experiment_type


class BaseSitemap(Sitemap):
    priority = 0.5

    # def lastmod(self, obj):
    #    return obj.modify_date

    def location(self, obj):
        return obj.get_absolute_url()


class ExperimentTemplateSitemap(BaseSitemap):
    changefreq = "weekly"

    def items(self):
        return [x for x in ExperimentTemplate.objects.all(
        ) if get_experiment_type(x) == "experiments"]


class SurveyTemplateSitemap(BaseSitemap):
    changefreq = "weekly"

    def items(self):
        return [x for x in ExperimentTemplate.objects.all(
        ) if get_experiment_type(x) == "surveys"]


class GameTemplateSitemap(BaseSitemap):
    changefreq = "weekly"

    def items(self):
        return [x for x in ExperimentTemplate.objects.all(
        ) if get_experiment_type(x) == "games"]
