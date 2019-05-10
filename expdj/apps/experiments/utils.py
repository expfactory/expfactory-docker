import json
import os
import random
import re
import shutil
import tempfile
from datetime import datetime

import pandas
from cognitiveatlas.api import get_concept, get_task
from django.db.models import Min
from expfactory.experiment import get_experiments
from expfactory.survey import export_questions
from expfactory.utils import copy_directory
from expfactory.vm import custom_battery_download
from git import Repo
from numpy.random import choice

from expdj.apps.experiments.models import (CognitiveAtlasConcept,
                                           CognitiveAtlasTask, Experiment,
                                           ExperimentBooleanVariable,
                                           ExperimentNumericVariable,
                                           ExperimentStringVariable,
                                           ExperimentTemplate,
                                           ExperimentVariable)
from expdj.apps.turk.models import Result
from expdj.settings import BASE_DIR, MEDIA_ROOT, STATIC_ROOT, EXP_REPO

media_dir = os.path.join(BASE_DIR, MEDIA_ROOT)

# EXPERIMENT FACTORY PYTHON FUNCTIONS ####################################


def get_experiment_selection(repo_type="experiments"):
    # tmpdir = custom_battery_download(repos=[repo_type])
    tmpdir = os.path.join(EXP_REPO, 'expfactory-{}'.format(repo_type))
    experiments = get_experiments(
        tmpdir,
        load=True,
        warning=False,
        repo_type=repo_type)
    experiments = [x[0] for x in experiments]
    # shutil.rmtree(tmpdir)
    return experiments


def get_experiment_type(experiment):
    '''get_experiment_type returns the installation folder (eg, games, surveys,
        experiments) based on the template specified in the config.json
    :param experiment: the ExperimentTemplate object
    '''
    if experiment.template in ["jspsych"]:
        return "experiments"
    elif experiment.template in ["survey"]:
        return "surveys"
    elif experiment.template in ["phaser"]:
        return "games"


def parse_experiment_variable(variable):
    experiment_variable = None
    if isinstance(variable, dict):
        try:
            description = variable["description"] if "description" in variable.keys(
            ) else None
            if "name" in variable.keys():
                name = variable["name"]
                if "datatype" in variable.keys():
                    if variable["datatype"].lower() == "numeric":
                        variable_min = variable["range"][0] if "range" in variable.keys(
                        ) else None
                        variable_max = variable["range"][1] if "range" in variable.keys(
                        ) else None
                        experiment_variable, _ = ExperimentNumericVariable.objects.update_or_create(
                            name=name, description=description, variable_min=variable_min, variable_max=variable_max)
                    elif variable["datatype"].lower() == "string":
                        experiment_variable, _ = ExperimentStringVariable.objects.update_or_create(
                            name=name, description=description, variable_options=variable_options)
                    elif variable["datatype"].lower() == "boolean":
                        experiment_variable, _ = ExperimentBooleanVariable.objects.update_or_create(
                            name=name, description=description)
                    experiment_variable.save()
        except BaseException:
            pass
    return experiment_variable


def install_experiments(experiment_tags=None, repo_type="experiments"):

    # We will return list of experiments that did not install successfully
    errored_experiments = []

    # tmpdir = custom_battery_download(repos=[repo_type, "battery"])
    tmpdir = os.path.join(EXP_REPO, 'expfactory-{}'.format(repo_type))

    # could catch non existant repos with git.exc.InvalidGitRepositoryError
    # repo = Repo("%s/%s" % (tmpdir, repo_type))
    repo = Repo(tmpdir)

    # The git commit is saved with the experiment as the "version"
    commit = repo.commit('master').__str__()

    experiments = get_experiments(tmpdir, load=True, warning=False)
    if experiment_tags is not None:
        experiments = [e for e in experiments if e[0]
                       ["exp_id"] in experiment_tags]

    for experiment in experiments:
        try:
            performance_variable = None
            rejection_variable = None
            if "experiment_variables" in experiment[0]:
                if isinstance(experiment[0]["experiment_variables"], list):
                    for var in experiment[0]["experiment_variables"]:
                        if var["type"].lower().strip() == "bonus":
                            performance_variable = parse_experiment_variable(
                                var)
                        elif var["type"].lower().strip() == "credit":
                            rejection_variable = parse_experiment_variable(var)
                        else:
                            parse_experiment_variable(var)  # adds to database
            if isinstance(experiment[0]["reference"], list):
                reference = experiment[0]["reference"][0]
            else:
                reference = experiment[0]["reference"]
            cognitive_atlas_task = get_cognitiveatlas_task(
                experiment[0]["cognitive_atlas_task_id"])

            new_experiment, _ = ExperimentTemplate.objects.update_or_create(
                exp_id=experiment[0]["exp_id"],
                defaults={
                    "name": experiment[0]["name"],
                    "cognitive_atlas_task": cognitive_atlas_task,
                    "publish": bool(experiment[0]["publish"]),
                    "time": experiment[0]["time"],
                    "reference": reference,
                    "version": commit,
                    "template": experiment[0]["template"],
                    "performance_variable": performance_variable,
                    "rejection_variable": rejection_variable
                }
            )

            new_experiment.save()
            experiment_folder = "%s/%s" % (tmpdir, experiment[0]["exp_id"])
            output_folder = "%s/%s/%s" % (media_dir,
                                          repo_type, experiment[0]["exp_id"])
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)
            copy_directory(experiment_folder, output_folder)
        except BaseException:
            errored_experiments.append(experiment[0]["exp_id"])

    # shutil.rmtree(tmpdir)
    return errored_experiments

# EXPERIMENTS AND BATTERIES ##############################################


def make_experiment_lookup(tags, battery=None):
    '''Generate lookup based on exp_id'''
    experiment_lookup = dict()
    for tag in tags:
        experiment = None
        try:
            if battery is not None:
                # First try retrieving from battery
                experiment = battery.experiments.filter(
                    template__exp_id=tag)[0]
                if isinstance(experiment, Experiment):
                    tmp = {"include_bonus": experiment.include_bonus,
                           "include_catch": experiment.include_catch,
                           "experiment": experiment.template}
                else:
                    experiment = None
            if experiment is None:
                experiment = ExperimentTemplate.objects.filter(exp_id=tag)[0]
                tmp = {"include_bonus": "Unknown",
                       "include_catch": "Unknown",
                       "experiment": experiment}
            experiment_lookup[tag] = tmp
        except BaseException:
            pass
    return experiment_lookup


def get_battery_results(battery, exp_id=None, clean=False):
    '''get_battery_results filters down to a battery, and optionally, an experiment of interest
    :param battery: expdj.models.Battery
    :param expid: an ExperimentTemplate.tag variable, eg "test_task"
    :param clean: remove battery info, subject info, and identifying information
    '''
    args = {"battery": battery}
    if exp_id is not None:
        args["experiment__exp_id"] = exp_id
    results = Result.objects.filter(**args)
    df = make_results_df(battery, results)
    if clean:
        columns_to_remove = [
            x for x in df.columns.tolist() if re.search(
                "worker_|^battery_", x)]
        columns_to_remove = columns_to_remove + [
            "experiment_include_bonus",
            "experiment_include_catch",
            "result_id",
            "result_view_history",
            "result_time_elapsed",
            "result_timing_post_trial",
            "result_stim_duration",
            "result_internal_node_id",
            "result_trial_index",
            "result_trial_type",
            "result_stimulus",
            "experiment_reference",
            "experiment_cognitive_atlas_task_id",
            "result_dateTime",
            "result_exp_id",
            "result_page_num"]
        df.drop(columns_to_remove, axis=1, inplace=True, errors="ignore")
        df.columns = [x.replace("result_", "") for x in df.columns.tolist()]
    df.index = range(0, df.shape[0])
    return df


def make_results_df(battery, results):

    variables = get_unique_variables(results)
    tags = get_unique_experiments(results)
    lookup = make_experiment_lookup(tags, battery)
    header = ['worker_id',
              'worker_platform',
              'worker_browser',
              'battery_name',
              'battery_owner',
              'battery_owner_email',
              'experiment_completed',
              'experiment_include_bonus',
              'experiment_include_catch',
              'experiment_exp_id',
              'experiment_name',
              'experiment_reference',
              'experiment_cognitive_atlas_task_id']
    column_names = header + variables
    df = pandas.DataFrame(columns=column_names)
    for result in results:
        try:
            if result.completed:
                worker_id = result.worker_id
                for t in range(len(result.taskdata)):
                    row_id = "%s_%s_%s" % (
                        result.experiment.exp_id, worker_id, t)
                    trial = result.taskdata[t]

                    # Add worker and battery information
                    df.loc[row_id,
                           ["worker_id",
                            "worker_platform",
                            "worker_browser",
                            "battery_name",
                            "battery_owner",
                            "battery_owner_email"]] = [worker_id,
                                                       result.platform,
                                                       result.browser,
                                                       battery.name,
                                                       battery.owner.username,
                                                       battery.owner.email]

                    # Look up the experiment
                    exp = lookup[result.experiment.exp_id]
                    df.loc[row_id,
                           ["experiment_completed",
                            "experiment_include_bonus",
                            "experiment_include_catch",
                            "experiment_exp_id",
                            "experiment_name",
                            "experiment_reference",
                            "experiment_cognitive_atlas_task_id"]] = [result.completed,
                                                                      exp["include_bonus"],
                                                                      exp["include_catch"],
                                                                      exp["experiment"].exp_id,
                                                                      exp["experiment"].name,
                                                                      exp["experiment"].reference,
                                                                      exp["experiment"].cognitive_atlas_task_id]

                    # Parse data
                    for key in trial.keys():
                        if key != "trialdata":
                            df.loc[row_id, key] = trial[key]
                    for key in trial["trialdata"].keys():
                        df.loc[row_id, key] = trial["trialdata"][key]
        except BaseException:
            pass

    # Change all names that don't start with experiment or worker or
    # experiment to be result
    result_variables = [x for x in column_names if x not in header]
    for result_variable in result_variables:
        df = df.rename(
            columns={
                result_variable: "result_%s" %
                result_variable})
        final_names = ["result_%s" % x for x in variables]

    # rename uniqueid to result id
    if "result_uniqueid" in df.columns:
        df = df.rename(columns={'result_uniqueid': 'result_id'})

    return df


# COGNITIVE ATLAS FUNCTIONS ##############################################

def get_cognitiveatlas_task(task_id):
    '''get_cognitiveatlas_task
    return the database entry for CognitiveAtlasTask if it exists, and update concepts for that task. If not, create it.
    :param task_id: the unique id for the cognitive atlas task
    '''
    try:
        task = get_task(id=task_id).json[0]
        cogatlas_task, _ = CognitiveAtlasTask.objects.update_or_create(
            cog_atlas_id=task["id"], defaults={"name": task["name"]})
        concept_list = []
        if "concepts" in task.keys():
            for concept in task["concepts"]:
                cogatlas_concept = get_concept(
                    id=concept["concept_id"]).json[0]
                cogatlas_concept, _ = CognitiveAtlasConcept.objects.update_or_create(
                    cog_atlas_id=cogatlas_concept["id"], defaults={
                        "name": cogatlas_concept["name"]}, definition=cogatlas_concept["definition_text"])
                cogatlas_concept.save()
                concept_list.append(cogatlas_concept)
        cogatlas_task.concepts = concept_list
        cogatlas_task.save()
        return cogatlas_task
    except BaseException:
        # Any error with API, etc, return None
        return None

# BONUS AND REJECTION CREDIT #############################################


def update_credits(experiment, cid):

    # Turn off credit conditions if no variables exist
    is_bonus = True if experiment.template.performance_variable.id == cid else False
    is_rejection = True if experiment.template.rejection_variable.id == cid else False

    # This only works given each experiment has one bonus or rejection criteria
    if is_bonus and len(experiment.credit_conditions) == 0:
        experiment.include_bonus = False

    if is_rejection and len(experiment.credit_conditions) == 0:
        experiment.include_catch = False

    experiment.save()

# EXPERIMENT SELECTION ###################################################


def select_random_n(experiments, N):
    '''select_experiments_N
    a selection algorithm that selects a random N experiments from list
    :param experiments: list of experiment.Experiment objects, with time variable specified in minutes
    :param N: the number of experiments to select
    '''
    if N > len(experiments):
        N = len(experiments)
    return choice(experiments, N).tolist()


def select_ordered(experiments, selection_number=1):
    '''select_ordered will return a list of the next "selection_number"
    of experiments. Lower numbers are returned first, and if multiple numbers
    are specified for orders, these will be selected from randomly.
    :param experiments: the list of Experiment objects to select from
    :param selection_number: the number of experiments to choose (default 1)
    '''
    next_value = experiments.aggregate(Min('order'))["order__min"]
    experiment_choices = [e for e in experiments if e.order == next_value]
    return select_random_n(experiment_choices, selection_number)


def select_experiments(battery, uncompleted_experiments, selection_number=1):
    '''select_experiments selects experiments based on the presentation_order variable
    defined in the battery (random or specific)
    :param battery: the battery object
    :param uncompleted_experiments: a list of Experiment objects to select from
    :param selection_number: the number of experiments to select
    '''
    if battery.presentation_order == "random":
        task_list = select_random_n(uncompleted_experiments, selection_number)
    elif battery.presentation_order == "specified":
        task_list = select_ordered(
            uncompleted_experiments,
            selection_number=selection_number)
    return task_list


def select_experiments_time(maximum_time_allowed, experiments):
    '''select_experiments_time
    a selection algorithm that selects experiments from list based on not exceeding some max time
    this function is not implemented anywhere, as the battery length is determined by experiments
    added to battery.
    :param maximum_time_allowed: the maximum time allowed, in seconds
    :param experiments: list of experiment.Experiment objects, with time variable specified in minutes
    '''
    # Add tasks with random selection until we reach the time limit
    task_list = []
    total_time = 0
    exps = experiments[:]
    while (total_time < maximum_time_allowed) and len(exps) > 0:
        # Randomly select an experiment
        experiment = exps.pop(choice(range(len(exps))))
        if (total_time + experiment.template.time * 60.0) <= maximum_time_allowed:
            task_list.append(experiment)
    return task_list

# GENERAL UTILS ##########################################################


def remove_keys(dictionary, keys):
    '''remove_key deletes a key from a dictionary'''
    if isinstance(keys, str):
        keys = [keys]
    new_dict = dict(dictionary)  # in case Query dict
    for key in keys:
        if key in new_dict:
            del new_dict[key]
    return new_dict


def complete_survey_result(exp_id, taskdata):
    '''complete_survey_result parses the form names (question ids) and matches to a lookup table generated by expfactory-python survey module that has complete question / option information.
    :param experiment: the survey unique id, expected to be
    :param taskdata: the taskdata from the server, typically an ordered dict
    '''
    taskdata = dict(taskdata)
    experiment = [{"exp_id": exp_id}]
    experiment_folder = "%s/%s/%s" % (media_dir, "surveys", exp_id)
    question_lookup = export_questions(experiment, experiment_folder)
    final_data = {}
    for queskey, quesval in taskdata.items():
        if queskey in question_lookup:
            complete_question = question_lookup[queskey]
            complete_question["response"] = quesval[0]
        else:
            complete_question = {"response": quesval[0]}
        final_data[queskey] = complete_question
    return final_data
