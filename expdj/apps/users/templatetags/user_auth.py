from django import template
from django.contrib.auth.models import User
from ..forms import UserCreateForm

register = template.Library()


@register.inclusion_tag('registration/_signup.html')
def signup_form():
    return {'form': UserCreateForm(instance=User())}
