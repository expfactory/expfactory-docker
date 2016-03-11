from django.contrib.auth.models import User
User.objects.create_superuser(username='expfactory', password='expfactory', email='')
