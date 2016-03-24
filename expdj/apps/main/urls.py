from django.views.generic.base import TemplateView
from django.conf.urls import patterns, url
from .views import index_view, signup_view, about_view, get_token

urlpatterns = patterns('',
    url(r'^$', index_view, name="index"),
    url(r'^signup$', signup_view, name="signup"),
    url(r'^token$', get_token, name="get_token"),
    url(r'^about$', about_view, name="about")
)
