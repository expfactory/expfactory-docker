from django.contrib.auth.models import User
from expdj.apps.users.models import User
if len(User.objects.all())==0:
    User.objects.create_superuser(username='expfactory', password='expfactory', email='')
