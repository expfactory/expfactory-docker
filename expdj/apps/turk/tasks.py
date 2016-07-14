from __future__ import absolute_import

import numpy
import os

from boto.mturk.price import Price
from celery import shared_task, Celery

from django.conf import settings
from django.utils import timezone

from expdj.apps.experiments.models import ExperimentTemplate, Battery
from expdj.apps.experiments.utils import get_experiment_type
from expdj.apps.turk.models import Result, Assignment, get_worker, HIT, Blacklist, Bonus
from expdj.settings import TURK

#  trying to import Result object directly from models was giving an import
#  error here, even though the import matched views.py exactly.
from expdj.apps import turk

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
        result = results[0]
        if result.assignment != None:
            result.assignment.hit.generate_connection()
            result.assignment.update()
            if result.assignment.status == "S":
                # Approve and grant bonus
                result.assignment.approve()
                result.assignment.completed = True
                result.assignment.save()
                grant_bonus(result.id)


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
    experiment = [b for b in battery.experiments.all() if b.template == experiment_template]

    if len(experiment) > 0:
        experiment = experiment[0]

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
                    if func(variable,comparator):
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


def get_bonus_reason(bonus):
    '''get_bonus_reason parses through worker bonus amounts, and returns a message to the worker for the reason
    :param bonus: expdj.apps.turk.models.Bonus object
    '''
    amounts = dict(bonus.amounts)
    reason = ""
    for experiment_name,record in amounts.iteritems():
        new_reason = "%s: granted $%s because %s\n" %(experiment_name,record["amount"],record["description"])
        reason = "%s%s" %(reason,new_reason)
    return reason

def grant_bonus(result_id):
    '''grant_bonus will calculate and grant a total bonus for a worker
    :param result_id: the id the result to grant the bonus for
    '''
    result = Result.objects.get(id=result_id)
    worker = result.worker
    battery = result.battery
    result.assignment.hit.generate_connection()
    try:
        bonus = Bonus.objects.get(worker=worker,battery=battery)
        amount = bonus.calculate_bonus()
        price = Price(amount)
        reason = get_bonus_reason(bonus)
        result.assignment.hit.connection.grant_bonus(worker.id,result.assignment.mturk_id,price,reason)
        bonus.granted = True
        bonus.save()
    except Bonus.DoesNotExist:
        pass

@shared_task
def experiment_reward(result_id):
    '''experiment_reward will record bonus based on satisfying some criteria
    The final bonus will be allocated at the end of the battery, after
    a result is submit, with grant_bonus. This function currently has code
    similar to check_blacklist, and the two are separate as this is expected
    to change
    :result_id: the id of the result object, turk.models.Result
    '''

    # Look up all result objects for worker
    result = Result.objects.get(id=result_id)
    battery = result.battery
    worker = result.worker
    experiment_template = result.experiment
    experiment = [b for b in battery.experiments.all() if b.template == experiment_template]

    if len(experiment)>0:
        experiment=experiment[0]

        do_bonus = True if experiment_template.performance_variable != None and experiment.include_bonus == True else False
        bonus_active = battery.bonus_active

        if result.completed == True and do_bonus == True and bonus_active == True:
            for credit_condition in experiment.credit_conditions.all():
                variable_name = credit_condition.variable.name
                variables = get_variables(result,variable_name)
                func = [x[1] for x in credit_condition.OPERATOR_CHOICES if x[0] == credit_condition.operator][0]
                func_description = [x[0] for x in credit_condition.OPERATOR_CHOICES if x[0] == credit_condition.operator][0]

                # Look through variables and determine if passes condition
                for variable in variables:
                    comparator = credit_condition.value
                    if isinstance(variable,bool):
                        comparator = bool(comparator)
                    elif isinstance(variable,float) or isinstance(variable,int):
                        variable = float(variable)
                        comparator = float(comparator)

                    # If the variable passes criteria and it's a performance variable
                    if func(variable,comparator):
                        if credit_condition.variable == experiment_template.performance_variable:
                            description = "%s %s %s %s" %(variable_name,variable,func_description,comparator)
                            bonus,_ = Bonus.objects.get_or_create(worker=worker,battery=battery)
                            if credit_condition.amount != None:
                                add_bonus(bonus,experiment,description,credit_condition.amount)
                                result.credit_granted = True
                                result.save()


def add_bonus(bonus,experiment,description,amount):
    '''add_bonus will add an entry to the bonus (json) list
    :param bonus: turk.models.Bonus object
    :param experiment: experiments.models.Experiment
    :param description: eg 'performance_var 556.333333333 GREATERTHAN 400.0'
    :param amount: the amount, in dollars to be given to the worker
    '''
    new_bonus = {"experiment_id":experiment.id,
                 "description":description,
                 "amount":amount}

    if bonus.amounts == None:
        amounts = dict()
        amounts[experiment.template.exp_id] = new_bonus
        bonus.amounts = amounts
    else:
        bonus.amounts[experiment.template.exp_id] = new_bonus

    bonus.save()


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


def check_battery_dependencies(current_battery, worker_id):
    '''
    check_battery_dependencies looks up all of a workers completed 
    experiments in a result object and places them in a dictionary 

    organized by battery_id. Each of these buckets of results is
    iterated through to check that every experiment in that battery has
    been completed. In this way a list of batteries that a worker has 
    completed is built. This list is then compared to the lists of 
    required and restricted batteries to determine if the worker is 
    eligible to attempt the current battery.
    '''
    worker_results = turk.models.Result.objects.filter(
        worker_id = worker_id,
        completed=True
    )
    
    worker_result_batteries = {}
    for result in worker_results:
        if worker_result_batteries.get(result.battery.id):
            worker_result_batteries[result.battery.id].append(result)
        else:
            worker_result_batteries[result.battery.id] = []
            worker_result_batteries[result.battery.id].append(result)

    worker_completed_batteries = []
    for battery_id in worker_result_batteries:
        result = worker_result_batteries[battery_id]
        all_experiments_complete = True
        result_experiment_list = [x.experiment_id for x in result]
        try:
            battery_experiments = Battery.objects.get(id=battery_id).experiments.all()
        except ObjectDoesNotExist:
            #  battery may have been removed.
            continue
        for experiment in battery_experiments:
            if experiment.template_id not in result_experiment_list:
                all_experiments_complete = False
                break
        if all_experiments_complete:
            worker_completed_batteries.append(battery_id)
            continue

    missing_batteries = []
    for required_battery in current_battery.required_batteries.all():
        if required_battery.id not in worker_completed_batteries:
            missing_batteries.append(required_battery)

    blocking_batteries = []
    for restricted_battery in current_battery.restricted_batteries.all():
        if restricted_battery.id in worker_completed_batteries:
            blocking_batteries.append(restricted_battery)

    return missing_batteries, blocking_batteries
