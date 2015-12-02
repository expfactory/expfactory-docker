from functools import wraps

from django.http.response import (HttpResponseRedirect, JsonResponse)
from django.shortcuts import (render, get_object_or_404, render_to_response,
                              redirect)
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.contrib import auth
from .forms import UserEditForm, UserCreateForm
from django.contrib.auth.decorators import login_required
from django.template.context import RequestContext
from rest_framework import status


def to_json_response(response):
    status_code = response.status_code
    data = None

    if status.is_success(status_code):
        if hasattr(response, 'is_rendered') and not response.is_rendered:
            response.render()
        data = {'data': response.content}

    elif status.is_redirect(status_code):
        data = {'redirect': response.url}

    elif (status.is_client_error(status_code) or
          status.is_server_error(status_code)):
        data = {'errors': [{
            'status': status_code
        }]}

    return JsonResponse(data)


def accepts_ajax(ajax_template_name=None):
    """
    Decorator for views that checks if the request was made
    via an XMLHttpRequest. Calls the view function and
    converts the output to JsonResponse.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.is_ajax():
                kwargs['template_name'] = ajax_template_name
                response = view_func(request, *args, **kwargs)
                return to_json_response(response)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


@accepts_ajax(ajax_template_name='registration/_signup.html')
def create_user(request, template_name='registration/signup.html'):
    if request.method == "POST":
        form = UserCreateForm(request.POST, request.FILES, instance=User())
        if form.is_valid():
            form.save()
            new_user = auth.authenticate(username=request.POST['username'],
                                         password=request.POST['password1'])
            auth.login(request, new_user)
            # Do something. Should generally end with a redirect. For example:
            if request.POST['next']:
                return HttpResponseRedirect(request.POST['next'])
            else:
                return HttpResponseRedirect(reverse("my_profile"))
    else:
        form = UserCreateForm(instance=User())

    context = {"form": form,
               "request": request}
    return render(request, template_name, context)


def view_profile(request, username=None):
    if not username:
        if not request.user.is_authenticated():
            return redirect('%s?next=%s' % (reverse('login'), request.path))
        else:
            user = request.user
    else:
        user = get_object_or_404(User, username=username)
    return render(request, 'registration/profile.html', {'user': user})


@login_required
def edit_user(request):
    edit_form = UserEditForm(request.POST or None, instance=request.user)
    if request.method == "POST":
        if edit_form.is_valid():
            edit_form.save()
            return HttpResponseRedirect(reverse("my_profile"))
    return render_to_response("registration/edit_user.html",
                              {'form': edit_form},
                              context_instance=RequestContext(request))


# def login(request):
#     return render_to_response('home.html', {
#         'plus_id': getattr(settings, 'SOCIAL_AUTH_GOOGLE_PLUS_KEY', None)
#     }, RequestContext(request))
