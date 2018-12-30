import hashlib

from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Count
from django.shortcuts import render
from django.template import RequestContext
from django.views.decorators.csrf import requires_csrf_token
from rest_framework.authtoken.models import Token

from expdj.apps.experiments.models import Battery


def index_view(request):
    context = {'active': 'home'}
    return render(request, 'main/index.html', context)


def signup_view(request):
    context = {'active': 'home'}
    return render(request, 'main/signup.html', context)


def about_view(request):
    context = {'active': 'home'}
    return render(request, 'main/about.html', context)


def search_view(request):
    return render(request, 'main/search.html')


@requires_csrf_token
def google_auth_view(request, bid, keyid):
    '''google_auth_view generates a UID based on a gmail authentication
    :param bid: the battery id
    :param keyid: the keyid to validate the link
    '''
    battery = Battery.objects.get(id=bid)
    uid = hashlib.md5(battery.name).hexdigest()
    if uid == keyid:
        context = {"keyid": keyid,
                   "bid": bid}
        return render(
            request,
            "main/google_auth.html",
            context)
    else:
        return render(request, "turk/robot_sorry.html", {})


@login_required
def get_token(request):
    context = {'active': 'home'}
    if request.user.is_authenticated:
        token, created = Token.objects.get_or_create(user=request.user)
        context["token"] = token.key
    return render(request, 'main/token.html', context)


# Error Pages ############################################################

def handler404(request):
    response = render(request, 'main/404.html', {})
    response.status_code = 404
    return response


def handler500(request):
    response = render(request, 'main/500.html', {})
    response.status_code = 500
    return response
