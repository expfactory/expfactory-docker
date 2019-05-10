from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from .views import create_user, edit_user, view_profile

admin.autodiscover()

urlpatterns = [
    url(r'^login/$', auth_views.LoginView.as_view(),
        name="login"),
    url(r'^logout/$', auth_views.LogoutView.as_view(),
        {'template_name': 'registration/logout.html', 'next_page': '/'}, name="logout"),
    # url(r'^create/$',
    #    create_user,
    #    name="create_user"),
    url(r'^profile/password/$',
        auth_views.PasswordChangeView.as_view(),
        name='password_change'),
    url(r'^password/change/done/$',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done'),
    url(r'^password/reset/$',
        auth_views.PasswordResetView.as_view(),
        name='password_reset'),
    url(r'^password/reset/done/$',
        auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done'),
    url(r'^password/reset/complete/$',
        auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete'),
    url(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'),
    url(r'^profile/edit$',
        edit_user,
        name="edit_user"),
    url(r'^profile/.*$',
        view_profile,
        name="my_profile"),
    url(r'^(?P<username>[A-Za-z0-9@/./+/-/_]+)/$',
        view_profile,
        name="profile")
]
