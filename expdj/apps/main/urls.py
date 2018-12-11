from django.conf.urls import url
from django.views.generic.base import TemplateView

from .views import (about_view, get_token, google_auth_view, index_view,
                    search_view, signup_view)

urlpatterns = [
    url(r'^$', index_view, name="index"),
    url(r'^signup$', signup_view, name="signup"),
    url(r'^search$', search_view, name="search"),
    url(r'^token$', get_token, name="get_token"),
    url(
        r'^batteries/(?P<bid>\d+|[A-Z]{8})/(?P<keyid>\d+|[A-Za-z0-9-]{32})/auth$',
        google_auth_view,
        name='google_auth_view'),
    # use google for auth
    url(r'^about$', about_view, name="about")
]
