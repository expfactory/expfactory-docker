from expdj.apps.experiments.models import Experiment, ExperimentTemplate, CognitiveAtlasTask, CognitiveAtlasConcept
from expfactory.vm import custom_battery_download, prepare_vm, specify_experiments
from expfactory.experiment import validate, load_experiment, get_experiments, make_lookup
from expfactory.utils import copy_directory, get_installdir, sub_template
from expfactory.battery import generate, generate_config
from cognitiveatlas.api import get_task, get_concept
from expdj.settings import STATIC_ROOT,BASE_DIR,MEDIA_ROOT
from expfactory.interface import get_field
from datetime import datetime
import tempfile
import shutil
import random
import pandas
import json
import os

media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)

# EXPERIMENT FACTORY PYTHON FUNCTIONS #####################################################

def update_battery_static(tmpdir=None):
    '''update_battery_static
    Downloads experiment battery folder, cross checks scripts (jspsych, etc)
    '''
    if tmpdir == None:
        tmpdir = custom_battery_download(repos=["battery"])
    # Get experiment "other" static files, move to our static
    # run collect static
    # Done.


def get_experiment_selection():
    tmpdir = custom_battery_download(repos=["experiments"])
    experiments = get_experiments("%s/experiments" %tmpdir,load=True,warning=False)
    experiments = [x[0] for x in experiments]
    shutil.rmtree(tmpdir)
    return experiments


def install_experiments(experiment_tags=None):

    # We will return list of experiments that did not install successfully
    errored_experiments = []

    tmpdir = custom_battery_download(repos=["experiments","battery"])
    experiments = get_experiments("%s/experiments" %tmpdir,load=True,warning=False)
    if experiment_tags != None:
        experiments = [e for e in experiments if e[0]["tag"] in experiment_tags]

    for experiment in experiments:

        try:
            cognitive_atlas_task = get_cognitiveatlas_task(experiment[0]["cognitive_atlas_task_id"])
            new_experiment = ExperimentTemplate(tag=experiment[0]["tag"],
                                                name=experiment[0]["name"],
                                                cognitive_atlas_task=cognitive_atlas_task,
                                                publish=bool(experiment[0]["publish"]),
                                                time=experiment[0]["time"],
                                                reference=experiment[0]["reference"])
            new_experiment.save()
            experiment_folder = "%s/experiments/%s" %(tmpdir,experiment[0]["tag"])
            copy_directory(experiment_folder,"%s/experiments/%s" %(media_dir,experiment[0]["tag"]))
        except:
            errored_experiments.append(experiment[0]["tag"])

    shutil.rmtree(tmpdir)
    return errored_experiments


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
