from expdj.apps.turk.tasks import get_unique_variables, get_unique_experiments
from expdj.apps.experiments.models import Experiment, ExperimentTemplate, \
  CognitiveAtlasTask, CognitiveAtlasConcept, ExperimentVariable, ExperimentNumericVariable, \
  ExperimentBooleanVariable, ExperimentStringVariable
from expfactory.vm import custom_battery_download
from expfactory.experiment import get_experiments
from expfactory.utils import copy_directory
from cognitiveatlas.api import get_task, get_concept
from expdj.settings import STATIC_ROOT,BASE_DIR,MEDIA_ROOT
from datetime import datetime
import tempfile
import shutil
import random
import pandas
import json
import os

media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)

# EXPERIMENT FACTORY PYTHON FUNCTIONS #####################################################

def get_experiment_selection():
    tmpdir = custom_battery_download(repos=["experiments"])
    experiments = get_experiments("%s/experiments" %tmpdir,load=True,warning=False)
    experiments = [x[0] for x in experiments]
    shutil.rmtree(tmpdir)
    return experiments


def parse_experiment_variable(variable):
    experiment_variable = None
    if isinstance(variable,dict):
        try:
            description = variable["description"] if "description" in variable.keys() else None
            if "name" in variable.keys():
                name = variable["name"]
                if "datatype" in variable.keys():
                    if variable["datatype"].lower() == "numeric":
                        variable_min = variable["range"][0] if "range" in variable.keys() else None
                        variable_max = variable["range"][1] if "range" in variable.keys() else None
                        experiment_variable,_ = ExperimentNumericVariable.objects.update_or_create(name=name,
                                                                                                   description=description,
                                                                                                   variable_min=variable_min,
                                                                                                   variable_max=variable_max)
                    elif variable["datatype"].lower() == "string":
                        experiment_variable,_ = ExperimentStringVariable.objects.update_or_create(name=name,
                                                                                                  description=description,
                                                                                                  variable_options=variable_options)
                    elif variable["datatype"].lower() == "boolean":
                        experiment_variable,new_flag = ExperimentBooleanVariable.objects.get_or_create(name=name,description=description)
                    experiment_variable.save()
        except:
            pass
    return experiment_variable


def install_experiments(experiment_tags=None):

    # We will return list of experiments that did not install successfully
    errored_experiments = []

    tmpdir = custom_battery_download(repos=["experiments","battery"])
    experiments = get_experiments("%s/experiments" %tmpdir,load=True,warning=False)
    if experiment_tags != None:
        experiments = [e for e in experiments if e[0]["exp_id"] in experiment_tags]

    for experiment in experiments:

        try:
            performance_variable = None
            rejection_variable = None
            if "experiment_variable" in experiment[0]:
                if isinstance(experiment[0]["experiment_variables"],list):
                    for var in experiment[0]["experiment_variables"]:
                        if var["type"].lower().strip() == "bonus":
                            performance_variable = parse_experiment_variable(var)
                        elif var["type"].lower().strip() == "credit":
                            rejection_variable = parse_experiment_variable(var)
                        else:
                            parse_experiment_variable(var) # adds to database
            cognitive_atlas_task = get_cognitiveatlas_task(experiment[0]["cognitive_atlas_task_id"])
            new_experiment = ExperimentTemplate(exp_id=experiment[0]["exp_id"],
                                                name=experiment[0]["name"],
                                                cognitive_atlas_task=cognitive_atlas_task,
                                                publish=bool(experiment[0]["publish"]),
                                                time=experiment[0]["time"],
                                                reference=experiment[0]["reference"],
                                                performance_variable=performance_variable,
                                                rejection_variable=rejection_variable)
            new_experiment.save()
            experiment_folder = "%s/experiments/%s" %(tmpdir,experiment[0]["exp_id"])
            copy_directory(experiment_folder,"%s/experiments/%s" %(media_dir,experiment[0]["exp_id"]))
        except:
            errored_experiments.append(experiment[0]["exp_id"])

    shutil.rmtree(tmpdir)
    return errored_experiments

# EXPERIMENTS AND BATTERIES ###############################################################

def make_experiment_lookup(tags,battery=None):
    '''Generate lookup based on exp_id'''
    experiment_lookup = dict()
    for tag in tags:
        experiment = None
        if battery != None:
            # First try retrieving from battery
            experiment = battery.experiments.filter(template__exp_id=tag)[0]
            if isinstance(experiment,Experiment):
                tmp = {"include_bonus":experiment.include_bonus,
                       "include_catch":experiment.include_catch,
                       "experiment":experiment.template}
            else:
               experiment = None
        if experiment == None:
            experiment = ExperimentTemplate.objects.filter(exp_id=tag)[0]
            tmp = {"include_bonus":"Unknown",
                   "include_catch":"Unknown",
                   "experiment":experiment}
        experiment_lookup[tag] = tmp
    return experiment_lookup


def make_results_df(battery,results):

    variables = get_unique_variables(results)
    tags = get_unique_experiments(results)
    lookup = make_experiment_lookup(tags,battery)
    header = ['worker_id',
              'worker_platform',
              'worker_browser',
              'battery_name',
              'battery_owner',
              'battery_owner_email',
              'battery_completed',
              'experiment_include_bonus',
              'experiment_include_catch',
              'experiment_exp_id',
              'experiment_name',
              'experiment_reference',
              'experiment_cognitive_atlas_task_id']
    column_names = header + variables
    df = pandas.DataFrame(columns=column_names)
    for result in results:
        if result.completed == True:
            worker_id = result.worker_id
            for t in range(len(result.taskdata)):
                row_id = "%s_%s" %(worker_id,t)
                trial = result.taskdata[t]
                df.loc[row_id,["worker_id","worker_platform","worker_browser","battery_name","battery_owner","battery_owner_email","battery_completed"]] = [worker_id,result.platform,result.browser,battery.name,battery.owner.username,battery.owner.email,result.completed]
                for key in trial.keys():
                    if key != "trialdata":
                        df.loc[row_id,key] = trial[key]
                for key in trial["trialdata"].keys():
                    df.loc[row_id,key] = trial["trialdata"][key]
                    if key == "exp_id":
                        exp=lookup[trial["trialdata"][key]]
                        df.loc[row_id,["exp_id","experiment_include_bonus","experiment_include_catch","experiment_exp_id","experiment_name","experiment_reference","experiment_cognitive_atlas_task_id"]] = [trial["trialdata"][key],exp["include_bonus"],exp["include_catch"],exp["experiment"].exp_id,exp["experiment"].name,exp["experiment"].reference,exp["experiment"].cognitive_atlas_task_id]

    # Change all names that don't start with experiment or worker or experiment to be result
    result_variables = [x for x in column_names if x not in header]
    for result_variable in result_variables:
        df=df.rename(columns = {result_variable:"result_%s" %result_variable})
        final_names = ["result_%s" %x for x in variables]

    # rename uniqueid to result id
    if "result_uniqueid" in df.columns:
        df=df.rename(columns = {'result_uniqueid':'result_id'})

    return df


# COGNITIVE ATLAS FUNCTIONS ###############################################################

def get_cognitiveatlas_task(task_id):
    '''get_cognitiveatlas_task
    return the database entry for CognitiveAtlasTask if it exists, and update concepts for that task. If not, create it.
    :param task_id: the unique id for the cognitive atlas task
    '''
    try:
        task = get_task(id=task_id).json[0]
        cogatlas_task, _ = CognitiveAtlasTask.objects.update_or_create(cog_atlas_id=task["id"], defaults={"name":task["name"]})
        concept_list = []
        for concept in task["concepts"]:
            cogatlas_concept = get_concept(id=concept["concept_id"]).json[0]
            cogatlas_concept, _ = CognitiveAtlasConcept.objects.update_or_create(cog_atlas_id=cogatlas_concept["id"],
                                                        defaults={"name":cogatlas_concept["name"]},
                                                        definition=cogatlas_concept["definition_text"])
            cogatlas_concept.save()
            concept_list.append(cogatlas_concept)
        cogatlas_task.concepts = concept_list
        cogatlas_task.save()
        return cogatlas_task
    except:
        # Any error with API, etc, return None
        return None

# BONUS AND REJECTION CREDIT ##############################################################

def update_credits(experiment,cid):

    # Turn off credit conditions if no variables exist
    is_bonus = True if experiment.template.performance_variable.id == cid else False
    is_rejection = True if experiment.template.rejection_variable.id == cid else False

    # This only works given each experiment has one bonus or rejection criteria
    if is_bonus and len(experiment.credit_conditions)==0:
        experiment.include_bonus = False

    if is_rejection and len(experiment.credit_conditions)==0:
        experiment.include_catch = False

    experiment.save()
