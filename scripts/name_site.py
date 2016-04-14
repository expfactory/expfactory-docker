from django.contrib.sites.models import Site
mysite = Site.objects.get_current()
mysite.domain = 'expfactory.org'
mysite.name = 'The Experiment Factory'
mysite.save()
