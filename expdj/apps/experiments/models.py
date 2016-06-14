import collections
import operator

from guardian.shortcuts import assign_perm, get_users_with_perms, remove_perm
from jsonfield import JSONField
from polymorphic.models import PolymorphicModel

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, DO_NOTHING
from django.db.models.signals import m2m_changed

#  trying to import Result object directly from models was giving an import 
#  error here, even though the import matched views.py exactly.
from expdj.apps import turk

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

class ExperimentVariable(PolymorphicModel):
    '''an experiment variable is either a performance_variable or a rejection_variable that is specified in the config.json as a dictionary,
    and determines the bonus (performance) or criteria for rejecting the HIT (rejection)
    '''
    name = models.CharField(max_length=500,help_text="name of the variable")
    description = models.CharField(max_length=500,help_text="description of the variable",unique=False)

    def __str__(self):
        return self.name

    def __meta__(self):
        unique_together = (("name","description"))

    def __unicode__(self):
        return self.name

class ExperimentNumericVariable(ExperimentVariable):
    variable_min = models.FloatField(null=True, verbose_name="minimum of the variable, if exists", blank=True)
    variable_max = models.FloatField(null=True, verbose_name="maximum of the variable, if exists", blank=True)

class ExperimentStringVariable(ExperimentVariable):
    variable_options = JSONField(null=True,blank=True,load_kwargs={'object_pairs_hook': collections.OrderedDict})

class ExperimentBooleanVariable(ExperimentVariable):
    variable_options = models.BooleanField(choices=((False, 'False'),
                                                    (True, 'True')), default=False,
                                                     verbose_name="boolean options")

class ExperimentTemplate(models.Model):
    '''expfactory-experiments, to be chosen and customized by researchers into Experiments, and deployed in batteries
    fields correspond with a subset in the config.json
    '''
    exp_id = models.CharField(primary_key=True, max_length=200, null=False, blank=False)
    name = models.CharField(max_length=500,help_text="name of the experiment",unique=True)
    cognitive_atlas_task = models.ForeignKey(CognitiveAtlasTask, help_text="Behavioral Paradigm representation in the Cognitive Atlas", verbose_name="Cognitive Atlas Task", null=True, blank=False,on_delete=DO_NOTHING)
    performance_variable = models.ForeignKey(ExperimentVariable, related_name="performance_variable",null=True,blank=True,verbose_name="performance variable",help_text="the javascript variable, if specified, in the browser that is designated to assess task performance.")
    rejection_variable = models.ForeignKey(ExperimentVariable,  related_name="rejection_variable", null=True,blank=True,verbose_name="rejection variable",help_text="the javascript variable, if specified for the experiment, in the browser that is designated to assess the degree of credit a user deserves for the task.")
    publish = models.BooleanField(choices=((False, 'Do not publish'),
                                           (True, 'Publish')),
                                           default=True,verbose_name="Publish")
    time = models.IntegerField()
    reference = models.CharField(max_length=500,help_text="reference or paper associated with the experiment",unique=False)
    template = models.CharField(max_length=100,null=True,blank=False)
    version = models.CharField(max_length=100,null=True,blank=False)

    def __meta__(self):
        ordering = ["name"]

    def __str__(self):
        return self.exp_id

    # Get the url for an experiment
    def get_absolute_url(self):
        return_cid = self.exp_id
        return reverse('experiment_details', args=[str(return_cid)])

class CreditCondition(models.Model):
    '''CreditCondition
    A model to represent a particular ExperimentVariable tied to an Experiment, and conditions selected by the user
    for determining to allocate reward or give credit for the experiment.
    '''
    OPERATOR_CHOICES = (
        ("EQUALS", operator.eq),
        ("LESSTHAN", operator.lt),
        ("GREATERTHAN", operator.gt),
        ("GREATERTHANEQUALTO", operator.ge),
        ("LESSTHANEQUALTO", operator.le),
        ("NOTEQUALTO", operator.ne),
    )
    variable = models.ForeignKey(ExperimentVariable,null=False,blank=False)
    value = models.CharField("user selected value",max_length=200,null=False,blank=False,help_text="user selected value to compare the variable with the operator")
    operator = models.CharField("operator to compare variable to value",max_length=200,choices=OPERATOR_CHOICES,null=True,blank=True,help_text="Whether the credit condition is for reward (bonus) or rejection variables.")
    amount = models.FloatField(null=True, verbose_name="amount, in dollars, to allocate/subtract", blank=True)

    def __meta__(self):
        unique_together = (("variable","value","operator"))


class Experiment(models.Model):
    template = models.ForeignKey(ExperimentTemplate, help_text="Experiment template to be customized by the researcher", verbose_name="Experiment Factory Experiment", null=True, blank=False,on_delete=DO_NOTHING)
    credit_conditions = models.ManyToManyField(CreditCondition,related_name="conditions",help_text="functions over performance and rejection variables to allocate payments and credit.",blank=True)
    order = models.IntegerField(help_text="Order for experiment presentation. Smaller numbers will be selected first, and equivalent numbers will be chosen from randomly.", null=False, default=1,verbose_name="Experiment order", blank=False)
    include_bonus = models.BooleanField(choices=((False, 'does not include bonus'),
                                                (True, 'includes bonus')),
                                                default=False,verbose_name="Bonus")
    include_catch = models.BooleanField(choices=((False, 'does not include catch'),
                                            (True, 'includes catch')),
                                            default=False,verbose_name="Catch")
    def __str__(self):
        return self.template.name


class Battery(models.Model):
    '''A battery is a collection of experiment templates'''

    ORDER_CHOICES = (
        ("random", "random"),
        ("specified", "specified"),
    )

    # Name must be unique because anonymous link is generated from hash
    name = models.CharField(max_length=200, unique = True, null=False, verbose_name="Name of battery")
    description = models.TextField(blank=True, null=True)
    credentials = models.CharField(max_length=200, unique = False, null=False, verbose_name="mturk credentials")
    consent = models.TextField(blank=True, null=True,help_text="Use HTML syntax to give your consent formatting.")
    advertisement = models.TextField(blank=True, null=True,help_text="Use HTML syntax to give your mturk advertisement formatting.")
    instructions = models.TextField(blank=True, null=True,help_text="Use HTML syntax to give your instructions formatting.")
    owner = models.ForeignKey(User)
    contributors = models.ManyToManyField(User,related_name="battery_contributors",related_query_name="contributor", blank=True,help_text="Select other Experiment Factory users to add as contributes to the battery.  Contributors can view results, deploy HITS, and edit the battery itself.",verbose_name="Contributors")
    experiments = models.ManyToManyField(Experiment,related_name="battery_experiments",related_query_name="battery_experiments", blank=True,help_text="Select the Experiments to include in the battery. Experiments will be selected randomly from this set to fit within the maximum allowed time per HIT, and only include those experiments that a MTurk user has not completed.",verbose_name="Experimental paradigms")
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    maximum_time = models.IntegerField(help_text="Maximum number of minutes for the battery to endure.", null=False, verbose_name="Maxiumum time", blank=False)
    number_of_experiments = models.IntegerField(help_text="Maximum number of experiments to select per deployment or HIT.", null=False, verbose_name="Number of experiments per deployment or HIT", blank=False)
    active = models.BooleanField(choices=((False, 'Inactive'),
                                          (True, 'Active')),
                                           default=True,verbose_name="Active")
    presentation_order = models.CharField("order function for presentation of experiments",max_length=200,choices=ORDER_CHOICES,default="random",help_text="Select experiments randomly, or in a custom specified order.")
    blacklist_active = models.BooleanField(
        choices=((False, 'Off'), (True, 'On')),
        default=False,
        verbose_name="Blacklist based on rejection criteria"
    )
    blacklist_threshold = models.PositiveIntegerField(null=True,blank=True,default=10,help_text="Number of experiments to fail reject condition to add participant to blacklist",validators = [MinValueValidator(0.0)])
    bonus_active = models.BooleanField(
        choices=((False, 'Off'), (True, 'On')),
        default=False,
        verbose_name="Bonus based on reward criteria"
    )
    required_batteries = models.ManyToManyField(
        "Battery",
        blank=True,
        related_name='required_batteries_mtm',
        help_text=("Batteries which must be completed for this battery to be "
                  "attempted")
    )
    restricted_batteries = models.ManyToManyField(
        "Battery",
        blank=True,
        related_name='restricted_batteries_mtm',
        help_text=("Batteries that must not be completed in order for "
                   "this battery to be attempted")
    )

    def get_absolute_url(self):
        return_cid = self.id
        return reverse('battery_details', args=[str(return_cid)])

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Battery, self).save(*args, **kwargs)
        assign_perm('del_battery', self.owner, self)
        assign_perm('edit_battery', self.owner, self)

    def check_battery_dependencies(self, worker_id):
        '''
        check_battery_dependencies looks up all of a workers completed 
        experiments in a result object and places them in a dictionary 
        organized by assignment_id. Each of these buckets of results is
        iterated through to check that every experiment in a battery has
        been completed. In this way a list of batteries that a worker has 
        completed is built. This list is then compared to the lists of 
        required and restricted batteries to determine if the worker is 
        eligible to attempt the current(self) battery.
        '''
        worker_results = turk.models.Result.objects.filter(
            worker_id = worker_id,
            completed=True
        )
        
        worker_result_assignments = {}
        for result in worker_results:
            if worker_result_assignments.get(result.assignment_id):
                worker_result_assignments[result.assignment_id].append(result)
            else:
                worker_result_assignments[result.assignment_id] = []
                worker_result_assignments[result.assignment_id].append(result)

        worker_completed_batteries = []
        for assignment_id in worker_result_assignments:
            result = worker_result_assignments[assignment_id]
            all_experiments_complete = True
            result_experiment_list = [x.experiment_id for x in result]
            try:
                battery = result[0].battery_id
                battery_experiments = Battery.objects.get(id=result[0].battery_id).experiments.all()
            except ObjectDoesNotExist:
                #  battery may have been removed.
                continue
            for experiment in battery_experiments:
                if experiment.template_id not in result_experiment_list:
                    all_experiments_complete = False
                    break
            if all_experiments_complete:
                worker_completed_batteries.append(battery)
                continue

        missing_batteries = []
        for required_battery in self.required_batteries.all():
            if required_battery.id not in worker_completed_batteries:
                missing_batteries.append(required_battery)

        blocking_batteries = []
        for restricted_battery in self.restricted_batteries.all():
            if restricted_battery.id in worker_completed_batteries:
                blocking_battery.append(required_battery)

        return missing_batteries, blocking_batteries

    class Meta:
        ordering = ["name"]
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
