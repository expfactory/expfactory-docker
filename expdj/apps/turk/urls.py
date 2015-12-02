from .views import turk_questions
from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # Assessments
    url(r'^mturk$', turk_questions, name="turk_questions"),
)
