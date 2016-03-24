from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Count
from rest_framework.authtoken.models import Token
from django.shortcuts import render

def index_view(request):
    context = {'active':'home'}
    return render(request, 'main/index.html', context)

def signup_view(request):
    context = {'active':'home'}
    return render(request, 'main/signup.html', context)

def about_view(request):
    context = {'active':'home'}
    return render(request, 'main/about.html', context)

@login_required
def get_token(request):
    context = {'active':'home'}
    if request.user.is_authenticated:
        token,created = Token.objects.get_or_create(user=request.user)
        context["token"] = token.key
    return render(request, 'main/token.html', context)
