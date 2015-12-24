from __future__ import absolute_import
from expdj.apps.turk.models import Result
from celery import shared_task, Celery
import numpy

@shared_task
def assign_experiment_credit(rid):
    '''Function to parse result from a task, assign credit or bonus if needed,
    and either flag result or mark as completed.
    '''
    result = Result.objects.filter(id=rid)
    
    # Get all experiments
    battery_experiments = result.assignment.hit.battery.experiments.all()
    experiment_ids = get_unique_experiments(result.taskdata)
    experiments = ExperimentTemplate.objects.filter(tag__in=experiment_ids)

    # Add that user completed experiment immediately
    worker = result.worker
    new_experiments = [e for e in experiments if e not in worker.experiments.all()]
    [worker.experiments.add(e) for e in new_experiments]        
    worker.save()

    # Get rejection criteria
    additional_credit = 0
    rejection = False
    for template in experiments:
        experiment = [b for b in battery_experiments if b.template == template]
        # If an experiment is deleted from battery, we have no way to know to reject/bonus
        if len(experiment)>0:
            experiment = experiment[0]
            do_catch = True if template.rejection_variable != None and experiment.include_catch == True else False
            do_bonus = True if template.performance_variable != None and experiment.include_bonus == True else False
            for credit_condition in experiment.credit_conditions.all():
                # Is is the credit criteria or the bonus criteria?
                if credit_condition.variable == template.rejection_variable and do_catch:    
                    variable_name = credit_condition.variable.name
                    variables = get_variables(taskdata,template.tag,variable_name)
                    for variable in variables:
                        # TODO: need to add bonus variable to databnase, AND check for variable type 
                    #if credit_condition.operator(float(credit_condition.value) 
                if credit_condition.variable == template.performance_variable and do_bonus:
                    extra_bonus = 0
                    #TODO: need to add bonus to credit_condition... user defined
            
    # Update bonus in HIT

    # Change status of hit/assignment to completed  
              
    # If flagged, add to queue somewhere...


# EXPERIMENT RESULT PARSING helper functions
def get_unique_experiments(taskdata):
    experiments = []
    for trial in taskdata:
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

