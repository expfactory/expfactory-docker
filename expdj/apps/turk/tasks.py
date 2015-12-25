from __future__ import absolute_import
from expdj.apps.experiments.models import ExperimentTemplate
from expdj.apps.turk.models import Result, Task, Assignment
from celery import shared_task, Celery
import numpy

@shared_task
def assign_experiment_credit(rid):
    '''Function to parse result from a task, assign credit or bonus if needed,
    and either flag result or mark as completed.
    '''
    result = Result.objects.filter(id=rid)[0]

    # Get all experiments
    battery_experiments = result.assignment.hit.battery.experiments.all()
    experiment_ids = get_unique_experiments([result])
    experiments = ExperimentTemplate.objects.filter(tag__in=experiment_ids)

    # Add that user completed experiment immediately
    worker = result.worker
    current_experiments = [e.experiment for e in worker.experiments.all()]
    new_experiments = [e for e in experiments if e not in current_experiments]
    for new_experiment in new_experiments:
        task = Task(battery=result.assignment.hit.battery,
                    experiment=new_experiment)
        task.save()
        worker.experiments.add(task)

    worker.save()

    # Get rejection criteria
    additional_dollars = 0.0
    rejection = False
    for template in experiments:
        experiment = [b for b in battery_experiments if b.template == template]
        # If an experiment is deleted from battery, we have no way to know to reject/bonus
        if len(experiment)>0:
            experiment = experiment[0]
            do_catch = True if template.rejection_variable != None and experiment.include_catch == True else False
            do_bonus = True if template.performance_variable != None and experiment.include_bonus == True else False
            for credit_condition in experiment.credit_conditions.all():
                variable_name = credit_condition.variable.name
                variables = get_variables(result.taskdata,template.tag,variable_name)
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

    # Update HIT assignments
    result.assignment.hit.update_assignments()
    assignment = Assignment.objects.filter(id=result.assignment.id)[0]

    # Allocate bonus, if any
    if not rejection:
        if additional_dollars != 0:
            assignment.bonus(value=additional_dollars)
        assignment.approve()
    # We currently don't reject off the bat - we show user in pending tab.
    #else:
        #assignment.reject()
    assignment.save()

# EXPERIMENT RESULT PARSING helper functions
def get_unique_experiments(results):
    experiments = []
    for result in results:
        for trial in result.taskdata:
            if "exp_id" in trial["trialdata"]:
                if trial["trialdata"]["exp_id"] not in experiments:
                    experiments.append(trial["trialdata"]["exp_id"])
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
        for trial in result.taskdata:
            new_variables = [x for x in trial.keys() if x not in variables and x!="trialdata"]
            variables = variables + new_variables
            if "trialdata" in trial.keys():
                new_variables = [x for x in trial["trialdata"].keys() if x not in variables]
                variables = variables + new_variables
    return numpy.unique(variables).tolist()
