from django.shortcuts import render
from django.db.models.aggregates import Count

def index_view(request):
    appname = "Cognitive Atlas Phenotype"
    context = {'appname': appname,
               'active':'home'}
    return render(request, 'main/index.html', context)

def signup_view(request):
    appname = "Cognitive Atlas Phenotype"
    context = {'appname': appname,
               'active':'home'}
    return render(request, 'main/signup.html', context)

def about_view(request):
    appname = "Cognitive Atlas Phenotype"
    context = {'appname': appname,
               'active':'home'}
    return render(request, 'main/about.html', context)
