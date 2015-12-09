from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from expdj.apps.experiments.models import Experiment
from expdj.apps.experiments.forms import ExperimentForm
from expdj.apps.experiments.utils import get_experiment_selection, install_experiments
from expdj.settings import BASE_DIR,STATIC_ROOT,MEDIA_ROOT
from expfactory.views import embed_experiment
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import shutil
import uuid
import json
import csv
import os

media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)

### AUTHENTICATION ####################################################

def owner_or_contrib(request,assessment):
    if not request.user.is_anonymous():
        if owner_or_super(request,assessment) or request.user in assessment.contributors.all():
            return True
    return False

def owner_or_super(request,assessment):
    if not request.user.is_anonymous():
        if assessment.owner == request.user or request.user.is_superuser:
            return True
    return False

def check_experiment_edit_permission(request):
    if not request.user.is_anonymous():
        return True
    return False

def check_behavior_edit_permission(request):
    if not request.user.is_anonymous():
        if request.user.is_superuser:
            return True
    return False

def is_question_editor(request):
    if not request.user.is_anonymous():   
        if request.user.is_superuser:
            return True
    return False           

def is_behavior_editor(request):
    if request.user.is_superuser:
        return True
    return False           


#### GETS #############################################################

# get assessment
def get_experiment(eid,request,mode=None):
    keyargs = {'pk':eid}
    try:
        experiment = Experiment.objects.get(**keyargs)
    except Experiment.DoesNotExist:
        raise Http404
    else:
        return experiment


#### VIEWS #############################################################

# View a single experiment
@login_required
def view_experiment(request, eid):
    experiment = get_experiment(eid,request)
    
    # Determine permissions for edit and deletion
    edit_permission = check_experiment_edit_permission(request)
    delete_permission = check_experiment_edit_permission(request)

    context = {'experiment': experiment,
               'edit_permission':edit_permission,
               'delete_permission':delete_permission}

    return render_to_response('experiment_details.html', context)

# All experiments
@login_required
def preview_experiment(request,eid):
    experiment = get_experiment(eid,request)
    experiment_folder = os.path.join(media_dir,"experiments",experiment.tag)    
    experiment_html = embed_experiment(experiment_folder,url_prefix="/")
    return render_to_response('experiment_preview.html', {"preview_html":experiment_html})


# All experiments
@login_required
def experiments_view(request):
    experiments = Experiment.objects.all()
    delete_permission = check_experiment_edit_permission(request)
    context = {'experiments': experiments,
               'delete_permission':delete_permission}
    return render(request, 'all_experiments.html', context)


#### EDIT/ADD/DELETE #############################################################
@login_required
def add_experiment(request):
    '''add_experiment
    View for presenting available experiments to user (from expfactory-experiements repo)
    '''
    experiment_selection = get_experiment_selection()
    current_experiments = [x.tag for x in Experiment.objects.all()]
    experiments = [e for e in experiment_selection if e["tag"] not in current_experiments]
    context = {"newexperiments": experiments,
               "experiments": current_experiments}
    return render(request, "add_experiment.html", context)


@login_required
def add_experiments(request):
    '''add_experiments
    view for actually adding new experiments (files, etc) to application and database
    '''
    newexperiments = request.POST.keys()
    experiment_selection = get_experiment_selection()
    selected_experiments = [e["tag"] for e in experiment_selection if e["tag"] in newexperiments]
    errored_experiments = install_experiments(experiment_tags=selected_experiments)
    if len(errored_experiments) > 0:
        message = "The experiments %s did not install successfully." %(",".join(errored_experiments))
    else:
        message = "Experiments installed successfully."
    experiments = Experiment.objects.all()
    context = {"experiments":experiments,
               "message":message}
    return render(request, "all_experiments.html", context)

@login_required
def edit_experiment(request,eid=None):
    '''edit_experiment
    view for editing a single experiment. Likely only will be useful to change publication status
    '''

    # Editing an existing experiment
    if eid:
        experiment = get_experiment(eid,request)
    else:
        return HttpResponseRedirect("add_experiment")

    if request.method == "POST":
        form = ExperimentForm(request.POST, instance=experiment)

        if form.is_valid():
            experiment = form.save(commit=False)
            experiment.save()

            context = {
                'experiment': experiment.name,
            }
            return HttpResponseRedirect(experiment.get_absolute_url())
    else:
        form = ExperimentForm(instance=experiment)

    context = {"form": form,
               "experiment":experiment}
    return render(request, "edit_experiment.html", context)


# Delete an experiment
@login_required
def delete_experiment(request, eid):
    experiment = get_experiment(eid,request)
    # Static Files
    static_files_dir = os.path.join(static_dir,experiment[0]["tag"])
    shutil.rmtree(static_files_dir)
    # Cognitive Atlas Task
    task = exp.cognitive_atlas_task
    if exp.cognitive_atlas_task.experiment_set.count() == 1:
       # We might want to delete concepts too? Ok for now.
       task.delete() 
    experiment.delete()
    return redirect('experiments')


#### EXPORT #############################################################

# Export specific experiment data
@login_required
def export_experiment(request,eid):
    experiment = get_experiment(eid,request)
    output_name = "%s.tsv" %(experiment.tag)
    return export_experiments([experiment],output_name)
   
# General function to export some number of experiments
@login_required
def export_experiments(experiments,output_name):

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' %(output_name)
    writer = csv.writer(response,delimiter='\t')

    #TODO: update this for exports
    # Write header 
    writer.writerow(['experiment_name',
                     'experiment_tag',
                     'experiment_cognitive_atlas_task',
                     'experiment_cognitive_atlas_task_id',
                     'experiment_reference'])

    for experiment in experiments:
        try:
            writer.writerow([experiment.name,
                             experiment.tag,
                             experiment.cognitive_atlas_task,
                             experiment.cognitive_atlas_task_id,
                             experiment.reference])
        except:
            pass

    return response
