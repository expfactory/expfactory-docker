from __future__ import absolute_import
from expdj.apps.turk.models import Result, Assignment, get_worker
from expdj.apps.experiments.models import ExperimentTemplate
from celery import shared_task, Celery
from django.conf import settings
from expdj.settings import TURK
import numpy
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expdj.settings')
app = Celery('expdj')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

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
            results[0].assignment.approve()


def assign_reward(worker_id):

    # Look up all result objects for worker
    worker = get_worker(worker_id)
    results = Result.objects.filter(worker=worker)

    # rejection criteria
    additional_dollars = 0.0
    rejection = False

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
                        variables = get_variables(result.taskdata,template.exp_id,variable_name)
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


def get_variables(taskdata,exp_id,variable_name):
    # First try looking for variable as it is
    variables = find_variable(taskdata,exp_id,variable_name)
    summary_funcs = {"avg":numpy.mean,
                     "mean":numpy.mean,
                     "average":numpy.mean,
                     "med":numpy.median,
                     "median":numpy.median,
                     "sum":numpy.sum,
                     "total":numpy.sum,
                     "max":numpy.max,
                     "min":numpy.min}
    if len(variables) == 0:
        # Did the user specify a summary statistic?
        if variable_name.split("_")[0].lower() in summary_funcs.keys():
            name = ["_".join(variable_name.split("_")[1:])][0]
            summary_func = summary_funcs[variable_name.split("_")[0].lower()]
            variables = find_variable(taskdata,exp_id,name)
            variables = [summary_func(variables)]
    return variables

def find_variable(taskdata,exp_id,variable_name):
    variables = []
    for trial in taskdata:
        if "exp_id" in trial["trialdata"]:
            if trial["trialdata"]["exp_id"] == exp_id:
                if variable_name in trial["trialdata"].keys():
                    variables.append(trial["trialdata"][variable_name])
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
