from __future__ import absolute_import
from expdj.apps.turk.models import Result, Assignment, get_worker, HIT, Blacklist
from expdj.apps.experiments.utils import get_experiment_type
from expdj.apps.experiments.models import ExperimentTemplate
from celery import shared_task, Celery
from django.utils import timezone
from django.conf import settings
from expdj.settings import TURK
import numpy
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expdj.settings')
app = Celery('expdj')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@shared_task
def update_assignments(hit_id):
    '''update_assignments updates all assignment (status, etc) from Amazon given a hit_id
    :param hit_id: HIT id from turk.models
    '''
    try:
        hit = HIT.objects.get(id=hit_id)
        hit.update_assignments()
    except:
        pass

@shared_task
def assign_experiment_credit(worker_id):
    '''Function to parse all results for a worker, assign credit or bonus if needed,
    and either flag result or mark as completed. Should be fired if:
      1) worker completes full battery and expfactory.djstatus variable is finished
      2) worker does not accept Consent ("Disagree") and ends battery
      3) worker is deemed to have poorly completed some N experiments in a row
      4) worker does not complete experiments, HIT time runs out
    '''
    # Look up all result objects for worker
    worker = get_worker(worker_id)
    results = Result.objects.filter(worker=worker)
    if len(results)>0:
        if results[0].assignment != None:
            results[0].assignment.hit.generate_connection()
            results[0].assignment.update()
            if results[0].assignment.status == "S":
                results[0].assignment.approve()
                results[0].assignment.completed = True
                results[0].assignment.save()

@shared_task
def check_blacklist(result_id):
    '''check_blacklist compares a result (associated with an experiment) against
    the rejection criteria, and adds a flag to the user/battery blacklist object
    in the case of a violation. When the user/battery blacklist flag count
    exceeds the battery.blacklist_threshold, the user is blacklisted.
    :param result: a turk.models.Result object
    '''

    result = Result.objects.get(id=result_id)
    worker = result.worker
    battery = result.battery
    experiment_template = result.experiment
    experiment = [b for b in battery.experiments.all() if b.template == experiment_template][0]

    # rejection criteria
    do_catch = True if experiment_template.rejection_variable != None and experiment.include_catch == True else False
    do_blacklist = battery.blacklist_active
    found_violation = False

    if result.completed == True and do_catch == True and do_blacklist == True:

        # A credit condition can be for reward or rejection
        for credit_condition in experiment.credit_conditions.all():
            variable_name = credit_condition.variable.name
            variables = get_variables(result,variable_name)
            func = [x[1] for x in credit_condition.OPERATOR_CHOICES if x[0] == credit_condition.operator][0]
            func_description = [x[0] for x in credit_condition.OPERATOR_CHOICES if x[0] == credit_condition.operator][0]

            # Look through variables and determine if in violation of condition
            for variable in variables:
                comparator = credit_condition.value
                if isinstance(variable,bool):
                    comparator = bool(comparator)
                elif isinstance(variable,float) or isinstance(variable,int):
                    variable = float(variable)
                if not isinstance(comparator,bool) and (isinstance(comparator,float) or isinstance(comparator,int)):
                    comparator = float(comparator)

                # If the variable passes criteria and it's a rejection variable
                if func(comparator,variable):
                    if credit_condition.variable == experiment_template.rejection_variable and found_violation == False:
                        found_violation = True
                        description = "%s %s %s %s" %(variable_name,variable,func_description,comparator)
                        blacklist,_ = Blacklist.objects.get_or_create(worker=worker,battery=battery)
                        add_blacklist(blacklist,experiment,description)


def add_blacklist(blacklist,experiment,description):
    '''add_blacklist will add an entry to the blacklist flagged (json) list, and
    check if the new number exceeds the allowed threshold. If yes, the user
    is blacklisted and not allowed to continue the battery.
    :param blacklist: turk.models.Blacklist object
    :param experiment: experiments.models.Experiment
    '''
    new_flag = {"experiment_id":experiment.id,
                "description":description}
    if blacklist.flags == None:
        flags = dict()
        flags[experiment.template.exp_id] = new_flag
        blacklist.flags = flags
    else:
        blacklist.flags[experiment.template.exp_id] = new_flag

    # If the blacklist count is greater than acceptable count, user is blacklisted
    if len(blacklist.flags) > blacklist.battery.blacklist_threshold:
        blacklist.active = True
        blacklist.blacklist_time = timezone.now()
    blacklist.save()

def assign_reward(result_id):
    '''assign_reward will grant bonus based on satisfying some criteria
    :result_id: the id of the result object, turk.models.Result
    '''

    # Look up all result objects for worker
    worker = get_worker(worker_id)
    results = Result.objects.filter(worker=worker)

    # rejection criteria
    additional_dollars = 0.0

    for result in results:
        if result.completed == True:
            # Get all experiments
            battery_experiments = result.assignment.hit.battery.experiments.all()
            experiment_ids = get_unique_experiments([result])
            experiments = ExperimentTemplate.objects.filter(exp_id__in=experiment_ids)
            for template in experiments:
                experiment = [b for b in battery_experiments if b.template == template]
                # If an experiment is deleted from battery, we have no way to know to reject/bonus
                if len(experiment)>0:
                    experiment = experiment[0]
                    do_catch = True if template.rejection_variable != None and experiment.include_catch == True else False
                    do_bonus = True if template.performance_variable != None and experiment.include_bonus == True else False
                    for credit_condition in experiment.credit_conditions.all():
                        variable_name = credit_condition.variable.name
                        variables = get_variables(result,variable_name)
                        func = [x[1] for x in credit_condition.OPERATOR_CHOICES if x[0] == credit_condition.operator][0]
                        # Needs to be tested for non numeric types
                        for variable in variables:
                            comparator = credit_condition.value
                            if isinstance(variable,float) or isinstance(variable,int):
                                variable = float(variable)
                                comparator = float(comparator)
                            if func(comparator,variable):
                                # For credit conditions, add to bonus!
                                if credit_condition.variable == template.performance_variable and do_bonus:
                                    additional_dollars = additional_dollars + credit_condition.amount
                                if credit_condition.variable == template.rejection_variable and do_catch:
                                    rejection = True
            # We remember granting credit on the level of results
            result.credit_granted = True
            result.save()

    if len(results) > 0:
        # Update HIT assignments - all results point to the same hit, so use the last one
        result.assignment.hit.update_assignments()
        assignment = Assignment.objects.filter(id=result.assignment.id)[0]


# EXPERIMENT RESULT PARSING helper functions
def get_unique_experiments(results):
    experiments = []
    for result in results:
        if result.completed == True:
           experiments.append(result.experiment.exp_id)
    return numpy.unique(experiments).tolist()


def get_variables(result,variable_name):
    # First try looking for variable as it is
    variables = find_variable(result,variable_name)
    summary_funcs = {"avg":numpy.mean,
                     "mean":numpy.mean,
                     "average":numpy.mean,
                     "med":numpy.median,
                     "median":numpy.median,
                     "sum":numpy.sum,
                     "total":numpy.sum,
                     "max":numpy.max,
                     "min":numpy.min}

    # Did the user specify a summary statistic?
    if len(variables) == 0:
        summary_func = variable_name.split("_")[0].lower()
        if summary_func in summary_funcs.keys():
            name = ["_".join(variable_name.split("_")[1:])][0]
            summary_func = summary_funcs[summary_func]
            variables = find_variable(result,name)
            variables = [summary_func(variables)]
    return variables

def find_variable(result,variable_name):

    # Surveys and games not yet implemented
    experiment_type = get_experiment_type(result.experiment)
    variables = []

    # For experiments
    if experiment_type == "experiments":
        taskdata = result.taskdata
        for trial in taskdata[0]["trialdata"]:
            if variable_name in trial.keys():
                variables.append(trial[variable_name])
    return variables

def get_unique_variables(results):
    variables = []
    for result in results:
        if result.completed == True:
            for trial in result.taskdata:
                new_variables = [x for x in trial.keys() if x not in variables and x!="trialdata"]
                variables = variables + new_variables
                if "trialdata" in trial.keys():
                    new_variables = [x for x in trial["trialdata"].keys() if x not in variables]
                    variables = variables + new_variables
    return numpy.unique(variables).tolist()
