from expfactory.vm import custom_battery_download, prepare_vm, specify_experiments
from expfactory.interface import get_field
from expfactory.experiment import validate, load_experiment, get_experiments, make_lookup
from expfactory.utils import copy_directory, get_installdir, sub_template
from expfactory.battery import generate, generate_config
from expdj.settings import STATIC_ROOT,BASE_DIR
from expdj.models import Experiment
import tempfile
import shutil
import random
import os

static_dir = os.path.join(BASE_DIR,STATIC_ROOT)

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

    #TODO: we need these assigned to cognitive atlas tasks, and the concept should NOT be represented
    for experiment in experiments:

        try: #eww eww eww
            try:
                cognitive_atlas_task = CognitiveAtlasTask.objects.filter(id=experiment[0]["cognitive_atlas_task_id"])
            except:
                cognitive_atlas_task = None
            new_experiment = Experiment(tag=experiment[0]["tag"],
                                    name=experiment[0]["name"],
                                    cognitive_atlas_task=cognitive_atlas_task,
                                    publish=bool(experiment[0]["publish"]),
                                    time=,
                                    reference=experiment[0]["reference"])
            new_experiment.save()
            experiment_folder = "%s/experiments/%s" %(tmpdir,experiment[0]["tag"])        
            copy_directory(experiment_folder,"%s/experiments/%s" %(static_dir,experiment[0]["tag"]))
        except:
            errored_experiments.append(experiment[0]["tag"])

    shutil.rmtree(tmpdir)
    return errored_experiments
