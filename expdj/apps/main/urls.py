from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url
from .views import index_view

urlpatterns = patterns('',
    url(r'^$', index_view, name="index"),
)