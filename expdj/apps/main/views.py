from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Count
from django.template import RequestContext
from rest_framework.authtoken.models import Token
from django.shortcuts import render, render_to_response

def index_view(request):
    context = {'active':'home'}
    return render(request, 'main/index.html', context)

def signup_view(request):
    context = {'active':'home'}
    return render(request, 'main/signup.html', context)

def about_view(request):
    context = {'active':'home'}
    return render(request, 'main/about.html', context)

def search_view(request):
    return render(request, 'main/search.html')


@login_required
def get_token(request):
    context = {'active':'home'}
    if request.user.is_authenticated:
        token,created = Token.objects.get_or_create(user=request.user)
        context["token"] = token.key
    return render(request, 'main/token.html', context)


# Error Pages ##################################################################

def handler404(request):
    response = render_to_response('main/404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response

def handler500(request):
    response = render_to_response('main/500.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 500
    return response
