from django.db.models import Q, DO_NOTHING
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import models


class CognitiveAtlasTask(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False)
    cog_atlas_id = models.CharField(primary_key=True, max_length=200, null=False, blank=False)
    
    def __str__(self):
        return self.name
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class CognitiveAtlasConcept(models.Model):
    name = models.CharField(max_length=1000, null=False, blank=False)
    cog_atlas_id = models.CharField(primary_key=True, max_length=200, null=False, blank=False)
    definition = models.CharField(max_length=5000, null=False, blank=False,default=None)
    
    def __str__(self):
        return self.name
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Experiment(models.Model):
    '''expfactory-experiments
    fields correspond with a subset in the config.json
    '''
    tag = models.CharField(primary_key=True, max_length=200, null=False, blank=False)
    name = models.CharField(max_length=500,help_text="name of the experiment",unique=True)
    cognitive_atlas_task = models.ForeignKey(CognitiveAtlasTask, help_text="Behavioral Paradigm representation in the Cognitive Atlas", verbose_name="Cognitive Atlas Task", null=True, blank=False,on_delete=DO_NOTHING)
    publish = models.BooleanField(choices=((False, 'Do not publish'),
                                           (True, 'Publish')),
                                           default=True,verbose_name="Publish")
    time = models.IntegerField()
    reference = models.CharField(max_length=500,help_text="reference or paper associated with the experiment",unique=False)

    def __str__(self):
        return self.tag    

    # Get the url for an experiment
    def get_absolute_url(self):
        return_cid = self.id
        return reverse('experiment_details', args=[str(return_cid)])
