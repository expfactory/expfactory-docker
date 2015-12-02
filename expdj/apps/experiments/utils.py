from expfactory.vm import custom_battery_download, prepare_vm, specify_experiments
from expfactory.interface import get_field
from expfactory.experiment import validate, load_experiment, get_experiments, make_lookup
from expfactory.utils import copy_directory, get_installdir, sub_template
from expfactory.battery import generate, generate_config
import tempfile
import shutil
import random
import os


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
    shutil.rmtree(tmpdir)
    return experiments


def install_experiments(experiment_tags=None):

    tmpdir = custom_battery_download(repos=["experiments","battery"])
    update_battery_static(tmpdir)
    experiments = get_experiments("%s/experiments" %tmpdir,load=True,warning=False)
    if experiment_tags != None:
        experiments = [e for e in experiments if e[0].tag in experiment_tags]
    
    for experiment in experiments:
        print "move!"
        # move experiments to static folder
        # 
    shutil.rmtree(tmpdir)
