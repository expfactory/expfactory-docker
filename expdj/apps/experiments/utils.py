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
        # move experiments to static folder
        # 
    shutil.rmtree(tmpdir)

    


# STEP 2: User must select experiments
@app.route('/battery/select',methods=['POST'])
def select():
    if request.method == 'POST':
        fields = dict()
        for field,value in request.form.iteritems():
            if field == "deploychoice":
                deploychoice = value
            else:
                fields[field] = value

        # Retrieve experiment folders 
        valid_experiments = app.experiments
        experiments =  [x[0]["tag"] for x in valid_experiments]
        selected_experiments = [x for x in fields.values() if x in experiments]
        experiment_folders = ["%s/experiments/%s" %(app.tmpdir,x) for x in selected_experiments]

        # Option 1: A folder on the local machine
        if deploychoice == "folder":

            # Add to the battery
            generate(battery_dest="%s/expfactory-battery"%app.tmpdir,
                     battery_repo="%s/battery"%app.tmpdir,
                     experiment_repo="%s/experiments"%app.tmpdir,
                     experiments=experiment_folders,
                     make_config=False,
                     warning=False)

            battery_dest = "%s/expfactory-battery" %(app.tmpdir)

        # Option 2 or 3: Virtual machine (vagrant) or cloud (aws)
        else:
            specify_experiments(battery_dest=tmpdir,experiments=selected_experiments)
            battery_dest = tmpdir 

        # Clean up
        clean_up("%s/experiments"%(app.tmpdir))
        clean_up("%s/battery"%(app.tmpdir))
        clean_up("%s/vm"%(app.tmpdir))        

        return render_template('complete.html',battery_dest=battery_dest)

def clean_up(dirpath):
    if os.path.exists(dirpath):
        shutil.rmtree(dirpath)
    
# This is how the command line version will run
def start(port=8088):
    if port==None:
        port=8088
    print "Nobody ever comes in... nobody ever comes out..."
    webbrowser.open("http://localhost:%s" %(port))
    app.run(host="0.0.0.0",debug=True,port=port)
    
if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
