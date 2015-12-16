from guardian.shortcuts import assign_perm, get_users_with_perms, remove_perm
from django.db.models.signals import m2m_changed
from django.db.models import Q, DO_NOTHING
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import models

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
        app_label = 'experiments'

class CognitiveAtlasTask(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False)
    cog_atlas_id = models.CharField(primary_key=True, max_length=200, null=False, blank=False)
    concepts = models.ManyToManyField(CognitiveAtlasConcept,related_name="concepts",related_query_name="concepts", blank=True,help_text="These are concepts associated with the task.",verbose_name="cognitive atlas associated concepts")

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class ExperimentTemplate(models.Model):
    '''expfactory-experiments, to be chosen and customized by researchers into Experiments, and deployed in batteries
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
        return_cid = self.tag
        return reverse('experiment_template_details', args=[str(return_cid)])

class Experiment(models.Model):
    template = models.ForeignKey(ExperimentTemplate, help_text="Experiment template to be customized by the researcher", verbose_name="Experiment Factory Experiment", null=True, blank=False,on_delete=DO_NOTHING)
    #catch_variable = models.CharField(max_length=250, unique = False, null=True, verbose_name="catch variable",help_text="the variable")
    #catch_function = models.CharField(max_length=250, unique = False, null=True, verbose_name="catch function",help_text="")
    #catch_threshold = models.FloatField(null=True, blank=True)
    include_bonus = models.BooleanField(choices=((False, 'does not include bonus'),
                                                (True, 'includes bonus')),
                                                default=False,verbose_name="does not include bonus")
    include_catch = models.BooleanField(choices=((False, 'does not include catch'),
                                            (True, 'includes catch')),
                                            default=False,verbose_name="does not include catch")
    def __str__(self):
        return self.template.name

    # Get the url for an experiment
    def get_absolute_url(self):
        return_cid = self.pk
        return reverse('experiment_details', args=[str(return_cid)])


class Battery(models.Model):
    '''A battery is a collection of experiment templates'''
    name = models.CharField(max_length=200, unique = True, null=False, verbose_name="Name of battery")
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User)
    aws_access_key_id = models.CharField(max_length=250, unique = False, null=False, verbose_name="AWS Access Key ID",help_text="Will only be accessible to the battery owner.")
    aws_secret_access_key_id = models.CharField(max_length=250, unique = False, null=False, verbose_name="AWS Secret Access Key",help_text="Will only be accessible to the battery owner.")
    contributors = models.ManyToManyField(User,related_name="battery_contributors",related_query_name="contributor", blank=True,help_text="Select other Experiment Factory users to add as contributes to the battery.  Contributors can view results, deploy HITS, and edit the battery itself.",verbose_name="Contributors")
    experiments = models.ManyToManyField(Experiment,related_name="battery_experiments",related_query_name="battery_experiments", blank=True,help_text="Select the Experiments to include in the battery. Experiments will be selected randomly from this set to fit within the maximum allowed time per HIT, and only include those experiments that a MTurk user has not completed.",verbose_name="Experimental paradigms")
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    maximum_time = models.IntegerField(help_text="Maximum number of minutes for the battery to endure.", null=False, verbose_name="Maxiumum time", blank=False)
    number_of_experiments = models.IntegerField(help_text="Maximum number of experiments to select per HIT.", null=False, verbose_name="Number of experiments per HIT", blank=False)
    active = models.BooleanField(choices=((False, 'Inactive'),
                                          (True, 'Active')),
                                           default=True,verbose_name="Active")
    def get_absolute_url(self):
        return_cid = self.id
        return reverse('battery_details', args=[str(return_cid)])

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Battery, self).save(*args, **kwargs)
        assign_perm('del_battery', self.owner, self)
        assign_perm('edit_battery', self.owner, self)

    class Meta:
        app_label = 'experiments'
        permissions = (
            ('del_battery', 'Delete battery'),
            ('edit_battery', 'Edit battery')
        )

def contributors_changed(sender, instance, action, **kwargs):
    if action in ["post_remove", "post_add", "post_clear"]:
        current_contributors = set([user.pk for user in get_users_with_perms(instance)])
        new_contributors = set([user.pk for user in [instance.owner, ] + list(instance.contributors.all())])

        for contributor in list(new_contributors - current_contributors):
            contributor = User.objects.get(pk=contributor)
            assign_perm('edit_battery', contributor, instance)

        for contributor in (current_contributors - new_contributors):
            contributor = User.objects.get(pk=contributor)
            remove_perm('edit_battery', contributor, instance)

m2m_changed.connect(contributors_changed, sender=Battery.contributors.through)
