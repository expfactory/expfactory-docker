import datetime
import csv
import hashlib
import json
import numpy
import os
import pandas
import re
import shutil
import uuid

from expfactory.battery import get_load_static, get_experiment_run
from expfactory.survey import generate_survey
from expfactory.experiment import load_experiment
from expfactory.views import embed_experiment

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.http.response import (
    HttpResponseRedirect, HttpResponseForbidden, Http404
)
from django.shortcuts import (
    get_object_or_404, render_to_response, render, redirect
)
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect

from expdj.apps.main.views import google_auth_view
from expdj.apps.experiments.forms import (
    ExperimentForm, ExperimentTemplateForm, BatteryForm, BlacklistForm
)
from expdj.apps.experiments.models import (
    ExperimentTemplate, Experiment, Battery, ExperimentVariable, 
    CreditCondition
)
from expdj.apps.experiments.utils import (
    get_experiment_selection, install_experiments, update_credits, 
    make_results_df, get_battery_results, get_experiment_type, remove_keys, 
    complete_survey_result, select_experiments
)
from expdj.settings import BASE_DIR,STATIC_ROOT,MEDIA_ROOT,DOMAIN_NAME
import expdj.settings as settings
from expdj.apps.turk.models import (
    HIT, Result, Assignment, get_worker, Blacklist, Bonus
)
from expdj.apps.turk.tasks import (
    assign_experiment_credit, update_assignments, check_blacklist, 
    experiment_reward, check_battery_dependencies
)
from expdj.apps.turk.utils import get_worker_experiments
from expdj.apps.users.models import User


media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)

### AUTHENTICATION ####################################################

def check_experiment_edit_permission(request):
    if request.user.is_superuser:
        return True
    return False

def check_mturk_access(request):
    if request.user.is_superuser:
        return True

    user_roles = User.objects.filter(user=request.user)
    if len(user_roles) == 0:
        return False
    elif user_roles[0].role == "MTURK":
        return True
    return False

def check_battery_create_permission(request):
    if not request.user.is_anonymous():
        if request.user.is_superuser:
            return True

    user_roles = User.objects.filter(user=request.user)
    if len(user_roles) == 0:
        return False
    elif user_roles[0].role in ["MTURK","LOCAL"]:
        return True
    return False

def check_battery_delete_permission(request,battery):
    if not request.user.is_anonymous():
        if request.user == battery.owner:
            return True
        if request.user.is_superuser:
            return True
    return False

def check_battery_edit_permission(request,battery):
    if not request.user.is_anonymous():
        if request.user == battery.owner or request.user in battery.contributors.all():
            return True
        if request.user.is_superuser:
            return True
    return False


#### GETS #############################################################

# get experiment template
def get_experiment_template(eid,request,mode=None):
    keyargs = {'pk':eid}
    try:
        experiment = ExperimentTemplate.objects.get(**keyargs)
    except ExperimentTemplate.DoesNotExist:
        raise Http404
    else:
        return experiment

# get experiment
def get_experiment(eid,request,mode=None):
    keyargs = {'id':eid}
    try:
        experiment = Experiment.objects.get(**keyargs)
    except Experiment.DoesNotExist:
        raise Http404
    else:
        return experiment

# get battery with experiments
def get_battery(bid,request):
    keyargs = {'pk':bid}
    try:
        battery = Battery.objects.get(**keyargs)
    except Battery.DoesNotExist:
        raise Http404
    else:
        return battery


#### VIEWS #############################################################

# View a single experiment
@login_required
def update_experiment_template(request,eid):
    '''This will update static files, along with the config.json parameters'''
    context = {"experiments": ExperimentTemplate.objects.all()}
    if request.user.is_superuser:
        experiment = get_experiment_template(eid=eid,request=request)
        experiment_type = get_experiment_type(experiment)
        errored_experiments = install_experiments(experiment_tags=[experiment.exp_id],repo_type=experiment_type)
        if len(errored_experiments) > 0:
            message = "The experiments %s did not update successfully." %(",".join(errored_experiments))
        else:
            message = "Experiments updated successfully."
            experiments = ExperimentTemplate.objects.all()
            context = {"experiments":experiments,
                       "message":message}
    return render(request, "experiments/all_experiments.html", context)


# View a single experiment
def view_experiment(request, eid, bid=None):

    # Determine permissions for edit and deletion
    context = dict()
    context["edit_permission"] = check_experiment_edit_permission(request)
    context["delete_permission"] = context["edit_permission"]

    # View an experiment associated with a battery
    if bid:
        experiment = get_experiment(eid,request)
        battery = get_battery(bid,request)
        context["edit_permission"] = check_battery_edit_permission(request,battery)
        context["delete_permission"] = context["edit_permission"] # same for now
        template = 'experiments/experiment_details.html'

    # An experiment template
    else:
        experiment = get_experiment_template(eid,request)
        template = 'experiments/experiment_template_details.html'
        context["experiment_type"] = get_experiment_type(experiment)
        battery = None

    context["battery"] = battery
    context["experiment"] = experiment

    return render_to_response(template, context)

# View a battery
@login_required
def view_battery(request, bid):
    battery = get_battery(bid,request)

    # Get associated HITS, update all
    hits = HIT.objects.filter(battery=battery)

    # Use task to update assignments
    for hit in hits:
        update_assignments.apply_async([hit.id])

    # Generate anonymous link
    anon_link = "%s/batteries/%s/%s/anon" %(DOMAIN_NAME,bid,hashlib.md5(battery.name).hexdigest())

    # Generate gmail auth link
    gmail_link = "%s/batteries/%s/%s/auth" %(DOMAIN_NAME,bid,hashlib.md5(battery.name).hexdigest())

    # Determine permissions for edit and deletion
    edit_permission = check_battery_edit_permission(request,battery)
    delete_permission = check_battery_edit_permission(request,battery)
    mturk_permission = check_mturk_access(request)

    # Render assignment details
    assignments = dict()
    assignments["accepted"] = [a for a in Assignment.objects.filter(hit__battery=battery) if a.status == "A"]
    assignments["none"] = [a for a in Assignment.objects.filter(hit__battery=battery) if a.status == None]
    assignments["submit"] = [a for a in Assignment.objects.filter(hit__battery=battery) if a.status == "S"]
    assignments["rejected"] = [a for a in Assignment.objects.filter(hit__battery=battery) if a.status == "R"]

    context = {'battery': battery,
               'edit_permission':edit_permission,
               'delete_permission':delete_permission,
               'mturk_permission':mturk_permission,
               'hits':hits,
               'anon_link':anon_link,
               'gmail_link':gmail_link,
               'assignments':assignments}

    return render(request,'experiments/battery_details.html', context)


# All experiments
def experiments_view(request):
    experiments = ExperimentTemplate.objects.all()
    delete_permission = check_experiment_edit_permission(request)
    context = {'experiments': experiments,
               'delete_permission':delete_permission}
    return render(request, 'experiments/all_experiments.html', context)


# All batteries
@login_required
def batteries_view(request,uid=None):
    if not uid:
        batteries = Battery.objects.all()
    else:
        batteries = Battery.objects.filter(owner_id=uid)
    generate_battery_permission = False
    context = {'batteries': batteries}
    return render(request, 'experiments/all_batteries.html', context)

# Errors and Messages ----------------------------------------------------------
def enable_cookie_view(request):
    '''enable_cookie_view alerts user cookies not enabled
    '''
    return render_to_response("experiments/cookie_sorry.html")

# Preview and Serving ----------------------------------------------------------
# Preview experiments - right now just for templates
def preview_experiment(request,eid):
    experiment = get_experiment_template(eid,request)
    experiment_type = get_experiment_type(experiment)
    experiment_folder = os.path.join(media_dir,experiment_type,experiment.exp_id)
    template = '%s/%s_preview.html' %(experiment_type,experiment_type[:-1])
    experiment_html = embed_experiment(experiment_folder,url_prefix="/")
    context = {"preview_html":experiment_html}
    return render_to_response(template, context)


@login_required
def generate_battery_user(request,bid):
    '''add a new user login url to take a battery'''

    battery = get_battery(bid,request)
    context = {"battery":battery,
              "domain":settings.DOMAIN_NAME}

    if check_battery_edit_permission(request,battery) == True:

            # Create a user result object
            userid = uuid.uuid4()
            worker = get_worker(userid)
            context["new_user"] = userid
            worker.save()

            return render_to_response('experiments/generate_battery_user.html', context)

    else:
            return HttpResponseRedirect(battery.get_absolute_url())

def get_battery_intro(battery,show_advertisement=True):

    instruction_forms = []

    # !Important: title for consent instructions must be "Consent" - see instructions_modal.html if you change
    if show_advertisement == True:
        if battery.advertisement != None: instruction_forms.append({"title":"Advertisement","html":battery.advertisement})
    if battery.consent != None: instruction_forms.append({"title":"Consent","html":battery.consent})
    if battery.instructions != None: instruction_forms.append({"title":"Instructions","html":battery.instructions})
    return instruction_forms


def serve_battery_anon(request,bid,keyid):
    '''serve an anonymous local battery, userid is generated upon going to link'''
    # Check if the keyid is correct
    battery = get_battery(bid,request)
    uid=hashlib.md5(battery.name).hexdigest()
    if uid==keyid:
        userid = uuid.uuid4()
        worker = get_worker(userid,create=True)
        return redirect("intro_battery",bid=bid,userid=userid)
    else:
        return render_to_response("turk/robot_sorry.html")

@csrf_protect
def serve_battery_gmail(request,bid):
    '''serves a battery, creating user with gmail'''
    # Check if the keyid is correct
    battery = get_battery(bid,request)
    uid = hashlib.md5(battery.name).hexdigest()
    if "keyid" in request.POST and "gmail" in request.POST:
        keyid = request.POST["keyid"]
        address = request.POST["gmail"]
        if uid==keyid:
            userid = hashlib.md5(address).hexdigest()
            worker = get_worker(userid,create=True)
            return redirect("intro_battery",bid=bid,userid=userid)
        else:
            return render_to_response("turk/robot_sorry.html")
    else:
        return render_to_response("turk/robot_sorry.html")


def preview_battery(request,bid):

    # No robots allowed!
    if request.user_agent.is_bot:
        return render_to_response("turk/robot_sorry.html")

    if request.user_agent.is_pc:

        battery = get_battery(bid,request)
        context = {"instruction_forms":get_battery_intro(battery),
                   "start_url":"/batteries/%s/dummy" %(bid),
                   "assignment_id":"assenav tahcos"}

        return render(request, "turk/serve_battery_intro.html", context)


def intro_battery(request,bid,userid=None):

    # No robots allowed!
    if request.user_agent.is_bot:
        return render_to_response("turk/robot_sorry.html")

    if request.user_agent.is_pc:

        battery = get_battery(bid,request)
        context = {"instruction_forms":get_battery_intro(battery),
                   "start_url":"/batteries/%s/%s/accept" %(bid,userid),
                   "assignment_id":"assenav tahcos"}

        return render(request, "turk/serve_battery_intro.html", context)

@login_required
def dummy_battery(request,bid):
    '''dummy_battery lets the user run a faux battery (preview)'''

    battery = get_battery(bid,request)
    deployment = "docker-local"

    # Does the worker have experiments remaining?
    task_list = select_experiments(battery,uncompleted_experiments=battery.experiments.all())
    experimentTemplate = ExperimentTemplate.objects.filter(exp_id=task_list[0].template.exp_id)[0]
    experiment_type = get_experiment_type(experimentTemplate)
    task_list = battery.experiments.filter(template=experimentTemplate)
    result = None
    context = {"worker_id": "Dummy Worker"}
    if experiment_type in ["games","surveys"]:
        template = "%s/serve_battery_preview.html" %(experiment_type)
    else:
        template = "%s/serve_battery.html" %(experiment_type)

    return deploy_battery(deployment="docker-preview",
                          battery=battery,
                          experiment_type=experiment_type,
                          context=context,
                          task_list=task_list,
                          template=template,
                          result=result)


@ensure_csrf_cookie
def serve_battery(request,bid,userid=None):
    '''prepare for local serve of battery'''

    next_page = None
    battery = get_battery(bid,request)

    # No robots allowed!
    if request.user_agent.is_bot:
        return render_to_response("turk/robot_sorry.html")

    # Is userid not defined, redirect them to preview
    if userid == None:
        return preview_battery(request,bid)

    worker = get_worker(userid,create=False)
    if isinstance(worker,list): # no id means returning []
        return render_to_response("turk/invalid_id_sorry.html")

    missing_batteries, blocking_batteries = check_battery_dependencies(battery, userid)
    if missing_batteries or blocking_batteries:
        return render_to_response(
            "turk/battery_requirements_not_met.html",
            context={'missing_batteries': missing_batteries,
                     'blocking_batteries': blocking_batteries}
        )


    # Try to get some info about browser, language, etc.
    browser = "%s,%s" %(request.user_agent.browser.family,request.user_agent.browser.version_string)
    platform = "%s,%s" %(request.user_agent.os.family,request.user_agent.os.version_string)
    deployment = "docker-local"

    # Does the worker have experiments remaining?
    uncompleted_experiments = get_worker_experiments(worker,battery)
    experiments_left = len(uncompleted_experiments)
    if  experiments_left == 0:
        # Thank you for your participation - no more experiments!
        return render_to_response("turk/worker_sorry.html")

    task_list = select_experiments(battery,uncompleted_experiments)
    experimentTemplate = ExperimentTemplate.objects.filter(exp_id=task_list[0].template.exp_id)[0]
    experiment_type = get_experiment_type(experimentTemplate)
    task_list = battery.experiments.filter(template=experimentTemplate)

    # Generate a new results object for the worker, assignment, experiment
    result,_ = Result.objects.update_or_create(worker=worker,
                                               experiment=experimentTemplate,
                                               battery=battery,
                                               defaults={"browser":browser,"platform":platform})
    result.save()

    context = {"worker_id": worker.id,
               "uniqueId":result.id}

    # If this is the last experiment, the finish button will link to a thank you page.
    if experiments_left == 1:
        next_page = "/finished"

    # Determine template name based on template_type
    template = "%s/serve_battery.html" %(experiment_type)

    return deploy_battery(
        deployment="docker-local",
        battery=battery,
        experiment_type=experiment_type,
        context=context,
        task_list=task_list,
        template=template,
        next_page=next_page,
        result=result,
        experiments_left=experiments_left-1
    )

def deploy_battery(deployment, battery, experiment_type, context, task_list, 
                   template, result, next_page=None, last_experiment=False, 
                   experiments_left=None):
    '''deploy_battery is a general function for returning the final view to deploy a battery, either local or MTurk
    :param deployment: either "docker-mturk" or "docker-local"
    :param battery: models.Battery object
    :param experiment_type: experiments,games,or surveys
    :param context: context, which should already include next_page,
    :param next_page: the next page to navigate to [optional] default is to reload the page to go to the next experiment
    :param task_list: list of models.Experiment instances
    :param template: html template to render
    :param result: the result object, turk.models.Result
    :param last_experiment: boolean if true will redirect the user to a page to submit the result (for surveys)
    :param experiments_left: integer indicating how many experiments are left in battery.
    '''
    if next_page == None:
        next_page = "javascript:window.location.reload();"
    context["next_page"] = next_page

    # Check the user blacklist status
    try:
        blacklist = Blacklist.objects.get(worker=result.worker,battery=battery)
        if blacklist.active == True:
            return render_to_response("experiments/blacklist.html")
    except:
        pass

    # Get experiment folders
    experiment_folders = [os.path.join(media_dir,experiment_type,x.template.exp_id) for x in task_list]
    context["experiment_load"] = get_load_static(experiment_folders,url_prefix="/")

    # Get code to run the experiment (not in external file)
    runcode = ""

    # Experiments templates
    if experiment_type in ["experiments"]:
        runcode = get_experiment_run(experiment_folders,deployment=deployment)[task_list[0].template.exp_id]
        if result != None:
            runcode = runcode.replace("{{result.id}}",str(result.id))
        runcode = runcode.replace("{{next_page}}",next_page)
        if experiments_left:
            total_experiments = battery.number_of_experiments
            expleft_msg = "</p><p>Experiments left in battery {0:d} out of {1:d}</p>"
            expleft_msg = expleft_msg.format(experiments_left, total_experiments)
            runcode = runcode.replace("</p>", expleft_msg)
    elif experiment_type in ["games"]:
        experiment = load_experiment(experiment_folders[0])
        runcode = experiment[0]["deployment_variables"]["run"]
    elif experiment_type in ["surveys"]:
        experiment = load_experiment(experiment_folders[0])
        resultid = ""
        if result != None:
            resultid = result.id
        runcode,validation = generate_survey(experiment,experiment_folders[0],
                                             form_action="/local/%s/" %resultid,
                                             csrf_token=True)

        # Field will be filled in by browser cookie, and hidden fields are added for data
        csrf_field = '<input type="hidden" name="csrfmiddlewaretoken" value="hello">'
        csrf_field = '%s\n<input type="hidden" name="djstatus" value="FINISHED">' %(csrf_field)
        csrf_field = '%s\n<input type="hidden" name="url" value="chickenfingers">' %(csrf_field)

        runcode = runcode.replace("{% csrf_token %}",csrf_field)
        context["validation"] = validation

        if last_experiment == True:
            context["last_experiment"] = last_experiment

    context["run"] = runcode
    response = render_to_response(template, context)

    # without this header, the iFrame will not render in Amazon
    response['x-frame-options'] = 'this_can_be_anything'
    return response

# These views are to work with backbone.js
@ensure_csrf_cookie
def sync(request,rid=None):
    '''localsync
    view/method for running experiments to get data from the server
    :param rid: the result object ID, obtained before user sees page
    '''

    if request.method == "POST":

        if rid != None:
        # Update the result, already has worker and assignment ID stored
            result,_ = Result.objects.get_or_create(id=rid)
            battery = result.battery
            experiment_template = get_experiment_type(result.experiment)
            if experiment_template == "experiments":
                data = json.loads(request.body)
                result.taskdata = data["taskdata"]["data"]
                result.current_trial = data["taskdata"]["currenttrial"]
                djstatus = data["djstatus"]
            elif experiment_template == "games":
                data = json.loads(request.body)
                redirect_url = data["redirect_url"]
                result.taskdata = data["taskdata"]
                djstatus = data["djstatus"]
            elif experiment_template == "surveys":
                data = request.POST
                redirect_url = data["url"]
                djstatus = data["djstatus"]
                # Remove keys we don't want
                data = remove_keys(data,["process","csrfmiddlewaretoken","url","djstatus"])
                result.taskdata = complete_survey_result(result.experiment.exp_id,data)

            result.save()

            # if the worker finished the current experiment
            if djstatus == "FINISHED":

                # Mark experiment as completed
                result.completed = True
                result.finishtime = timezone.now()
                result.version = result.experiment.version
                result.save()

                # Fire a task to check blacklist status, add bonus
                check_blacklist.apply_async([result.id])
                experiment_reward.apply_async([result.id])

                data = dict()
                data["finished_battery"] = "NOTFINISHED"
                data["djstatus"] = djstatus
                completed_experiments = get_worker_experiments(result.worker,battery,completed=True)
                completed_experiments = numpy.unique([x.template.exp_id for x in completed_experiments]).tolist()
                if len(completed_experiments) == battery.experiments.count():
                    assign_experiment_credit.apply_async([result.worker.id],countdown=60)
                    data["finished_battery"] = "FINISHED"

                # Refresh the page if we've completed a survey or game
                if experiment_template in ["surveys"]:
                    return redirect(redirect_url)

            data = json.dumps(data)

    else:
        data = json.dumps({"message":"received!"})

    return HttpResponse(data, content_type='application/json')


#### EDIT/ADD/DELETE ###################################################

# General install functions -----------------------------------------------------
@login_required
def add_new_template(request,template_type):
    '''add_new_template
    View for installing new survey, game, or experiment
    '''
    new_selection = get_experiment_selection(template_type)
    template = "%s/add_%s_template.html" %(template_type,template_type[:-1])
    current_experiments = ExperimentTemplate.objects.all()
    tags = [e.exp_id for e in current_experiments]
    newselection = [e for e in new_selection if e["exp_id"] not in tags]
    context = {"newtemplates": newselection,
               "experiments": current_experiments}
    return render(request, template, context)

@login_required
def save_new_template(request,template_type):
    '''save_new_template
    view for actually adding new surveys, experiments, or games (files, etc) to application and database
    '''
    newtemplates = request.POST.keys()
    new_selection = get_experiment_selection(template_type)
    selected_experiments = [e["exp_id"] for e in new_selection if e["exp_id"] in newtemplates]
    errored = install_experiments(experiment_tags=selected_experiments,repo_type=template_type)
    if len(errored) > 0:
        message = "The %s %s did not install successfully." %(template_type,",".join(errored))
    else:
        message = "%s installed successfully." %(template_type)
    experiments = ExperimentTemplate.objects.all()
    context = {"experiments":experiments,
               "message":message}
    return render(request, "experiments/all_experiments.html", context)

# Install Templates ----------------------------------------------------------

@login_required
def add_experiment_template(request):
    return add_new_template(request,"experiments")

@login_required
def add_survey_template(request):
    return add_new_template(request,"surveys")

@login_required
def add_game_template(request):
    return add_new_template(request,"games")

@login_required
def save_experiment_template(request):
    return save_new_template(request,"experiments")

@login_required
def save_survey_template(request):
    return save_new_template(request,"surveys")

@login_required
def save_game_template(request):
    return save_new_template(request,"games")

@login_required
def edit_experiment_template(request,eid=None):
    '''edit_experiment_template
    view for editing a single experiment. Likely only will be useful to change publication status
    '''
    # Editing an existing experiment
    if eid:
        experiment = get_experiment_template(eid,request)
    else:
        return HttpResponseRedirect("add_experiment_template")

    if request.method == "POST":
        form = ExperimentTemplateForm(request.POST, instance=experiment)

        if form.is_valid():
            experiment = form.save(commit=False)
            experiment.save()

            context = {
                'experiment': experiment.name,
            }
            return HttpResponseRedirect(experiment.get_absolute_url())
    else:
        form = ExperimentTemplateForm(instance=experiment)

    context = {"form": form,
               "experiment":experiment}
    return render(request, "experiments/edit_experiment_template.html", context)

# Delete an experiment
@login_required
def delete_experiment_template(request, eid, do_redirect=True):
    experiment = get_experiment_template(eid,request)
    experiment_instances = Experiment.objects.filter(template=experiment)
    experiment_type = get_experiment_type(experiment)
    if check_experiment_edit_permission(request):
        # Static Files
        [e.delete() for e in experiment_instances]
        static_files_dir = os.path.join(media_dir,experiment_type,experiment.exp_id)
        if os.path.exists(static_files_dir):
            shutil.rmtree(static_files_dir)
        # delete associated results
        results = Result.objects.filter(experiment=experiment)
        [r.delete() for r in results]
        # Cognitive Atlas Task
        task = experiment.cognitive_atlas_task
        try:
            if experiment.cognitive_atlas_task.experiment_set.count() == 1:
                # We might want to delete concepts too? Ok for now.
                task.delete()
        except:
            pass
        experiment.delete()

    if do_redirect == True:
        return redirect('experiments')


# Experiments ----------------------------------------------------------

@login_required
def edit_experiment(request,bid,eid):
    '''edit_experiment
    view to edit experiment already added to battery
    '''
    battery = get_battery(bid,request)
    experiment = get_experiment(eid,request)

    if request.method == "POST":
        form = ExperimentForm(request.POST, instance=experiment)

        if form.is_valid():
            experiment = form.save(commit=False)
            experiment.save()
            for cc in experiment.credit_conditions.all():
                update_credits(experiment,cc.id)
            return HttpResponseRedirect(battery.get_absolute_url())
    else:
        form = ExperimentForm(instance=experiment)

    context = {"form": form,
               "experiment":experiment,
               "battery":battery}
    return render(request, "experiments/edit_experiment.html", context)

@login_required
def save_experiment(request,bid):
    '''save_experiment
    save experiment and custom details for battery
    '''
    if request.method == "POST":
        vars = request.POST.keys()
        battery = get_battery(bid,request)
        template = get_experiment_template(request.POST["experiment"],request)
        expression = re.compile("[0-9]+")
        experiment_vids = numpy.unique([expression.findall(x)[0] for x in vars if expression.search(x)]).tolist()

        # Create a credit condition for each experiment variable
        credit_conditions = []
        include_bonus = False
        include_catch = False

        for vid in experiment_vids:
            # Assume that adding the credit condition means the user wants them turned on
            if int(vid) == template.performance_variable.id:
                include_bonus = True
            if int(vid) == template.rejection_variable.id:
                include_catch = True
            experiment_variable = ExperimentVariable.objects.filter(id=vid)[0]
            variable_value = request.POST["val%s" %(vid)] if "val%s" %(vid) in vars else None
            variable_operator = request.POST["oper%s" %(vid)] if "oper%s" %(vid) in vars else None
            variable_amount = request.POST["amt%s" %(vid)] if "amt%s" %(vid) in vars else None
            credit_condition,_ = CreditCondition.objects.update_or_create(variable=experiment_variable,
                                                                          value=variable_value,
                                                                          operator=variable_operator,
                                                                          amount=variable_amount)
            credit_condition.save()
            credit_conditions.append(credit_condition)

        # Create the experiment to add to the battery
        experiment = Experiment.objects.create(template=template,
                                               include_bonus=include_bonus,
                                               include_catch=include_catch)
        experiment.save()
        experiment.credit_conditions=credit_conditions
        experiment.save()

        # Add to battery, will replace old version if it exists
        current_experiments = [e for e in battery.experiments.all() if e.template.exp_id not in template.exp_id]
        current_experiments.append(experiment)
        battery.experiments = current_experiments
        battery.save()

    return HttpResponseRedirect(battery.get_absolute_url())

@login_required
def prepare_change_experiment(request,battery,experiments,change_type="Edit"):
    '''prepare_change_experiment returns view of either new experiments
    (not in battery) or experiments in battery to edit (depending on calling
    function)
    :param battery: expdj.apps.experiments.models.Battery
    :param experiments: expdj.apps.experiments.models.ExperimentTemplate
    :param change_type: The string to display to the user to indicate how
    changing experiment, eg, "Edit" or "Add New" [Experiment]
    '''

    # Capture the performance and rejection variables appropriately
    experimentsbytag = dict()
    for exp in experiments:
        experimentjson = model_to_dict(exp)
        if exp.performance_variable:
            experimentjson["performance_variable"] = model_to_dict(exp.performance_variable)
        if exp.rejection_variable:
            experimentjson["rejection_variable"] = model_to_dict(exp.rejection_variable)
        experimentsbytag[experimentjson["exp_id"]] = experimentjson

    # Present in abc order, color by new/old experiments
    experiment_tags = [x.exp_id for x in experiments]

    experiment_tags.sort()
    experiments_sorted = []
    for experiment_tag in experiment_tags:
        experiments_sorted.append(experimentsbytag[experiment_tag])

    context = {"allexperiments": experiments_sorted,
               "allexperimentsjson":json.dumps(experimentsbytag),
               "bid":battery.id,
               "change_type":change_type}

    return render(request, "experiments/add_experiment.html", context)

@login_required
def modify_experiment(request,bid):
    '''modify_experiment
    View for presenting already installed experiments (to modify) in a battery
    '''
    battery = get_battery(bid,request)
    current_experiments = [x.template.exp_id for x in battery.experiments.all()]
    oldexperiments = [x for x in ExperimentTemplate.objects.all() if x.exp_id in current_experiments]
    return prepare_change_experiment(request,battery,oldexperiments)


@login_required
def add_experiment(request,bid):
    '''add_experiment
    View for presenting available experiments to user to install to battery
    '''
    battery = get_battery(bid,request)
    current_experiments = [x.template.exp_id for x in battery.experiments.all()]
    newexperiments = [x for x in ExperimentTemplate.objects.all() if x.exp_id not in current_experiments]
    return prepare_change_experiment(request,battery,newexperiments,"Add New")


@login_required
def change_experiment_order(request,bid,eid):
    '''change_experiment_order changes the ordering of experiment presentation.
    Any integer value is allowed, and duplicate values means that experiments will
    the equivalent number will be selected from randomly.
    :param bid: the battery id
    :param eid: the experiment id
    '''
    experiment = get_experiment(eid,request)
    battery = get_battery(bid,request)
    can_edit = check_experiment_edit_permission(request)
    if request.method == "POST":
        if can_edit:
            if "order" in request.POST:
                new_order = request.POST["order"]
                if new_order != "":
                    experiment.order = int(new_order)
                    experiment.save()

    return HttpResponseRedirect(battery.get_absolute_url())


@login_required
def remove_experiment(request,bid,eid):
   '''remove_experiment
   removes an experiment from a battery
   '''
   battery = get_battery(bid,request)
   experiment = get_experiment(eid,request)
   if check_battery_edit_permission(request,battery):
       battery.experiments = [x for x in battery.experiments.all() if x.id != experiment.id]
   battery.save()

   # If experiment is not linked to other batteries, delete it
   if len(Battery.objects.filter(experiments__id=experiment.id)) == 0:
       experiment.delete()
   return HttpResponseRedirect(battery.get_absolute_url())

# Conditions -----------------------------------------------------------

@login_required
def remove_condition(request,bid,eid,cid):
    '''remove_condition: removes a condition from being associated with a battery
    '''
    battery = get_battery(bid,request)
    experiment = get_experiment(eid,request)
    credit_condition = CreditCondition.objects.filter(id=cid)[0]
    experiment.credit_conditions = [c for c in experiment.credit_conditions.all() if c != credit_condition]

    # Delete credit condition if not attached to experiments
    if len(Experiment.objects.filter(credit_conditions__id=cid)) == 0:
        credit_condition.delete()

    # Deletes condition from experiments, if not used from database, turns bonus/rejection on/off
    update_credits(experiment,cid)

    form = ExperimentForm(instance=experiment)

    context = {"form": form,
               "experiment":experiment,
               "battery":battery}
    return render(request, "experiments/edit_experiment.html", context)


# Battery --------------------------------------------------------------

@login_required
def add_battery(request):
    '''add_battery
    Function for adding new battery to database
    '''
    return redirect('batteries')

@login_required
def edit_battery(request, bid=None):

    # Does the user have mturk permission?
    mturk_permission = check_mturk_access(request)
    battery_permission = check_battery_create_permission(request)

    if battery_permission == True:
        header_text = "Add new battery"
        if bid:
            battery = get_battery(bid,request)
            is_owner = battery.owner == request.user
            header_text = battery.name
            battery_edit_permission = check_battery_edit_permission(request,battery)
            if battery_edit_permission == False:
                return HttpResponseForbidden()
        else:
            is_owner = True
            battery = Battery(owner=request.user)
            battery_edit_permission = True
        if request.method == "POST":
            if is_owner:
                form = BatteryForm(request.POST,instance=battery)
            if form.is_valid():
                previous_contribs = set()
                if form.instance.pk is not None:
                    previous_contribs = set(form.instance.contributors.all())
                battery = form.save(commit=False)
                battery.save()

                if is_owner:
                    form.save_m2m()  # save contributors
                    current_contribs = set(battery.contributors.all())
                    new_contribs = list(current_contribs.difference(previous_contribs))

                return HttpResponseRedirect(battery.get_absolute_url())
        else:
            if is_owner:
                form = BatteryForm(instance=battery)
            else:
                form = BatteryForm(instance=battery)

        context = {"form": form,
                   "is_owner": is_owner,
                   "header_text":header_text,
                   "mturk_permission":mturk_permission,
                   "battery_edit_permission":battery_edit_permission}

        return render(request, "experiments/edit_battery.html", context)
    else:
        return redirect("batteries")

# Delete a battery
@login_required
def delete_battery(request, bid):
    battery = get_battery(bid,request)
    delete_permission = check_battery_delete_permission(request,battery)
    if delete_permission==True:
        hits = HIT.objects.filter(battery=battery)
        [h.delete() for h in hits]
        results = Result.objects.filter(battery=battery)
        [r.delete() for r in results]
        battery.delete()
    return redirect('batteries')


@login_required
def subject_management(request,bid):
    '''subject_management includes blacklist criteria, etc.
    :param bid: the battery id
    '''
    battery = get_battery(bid,request)
    blacklists = Blacklist.objects.filter(battery=battery)
    bonuses = Bonus.objects.filter(battery=battery)

    if request.method == "POST":
        form = BlacklistForm(request.POST, instance=battery)

        if form.is_valid():
            battery = form.save()
            return HttpResponseRedirect(battery.get_absolute_url())
    else:
        form = BlacklistForm(instance=battery)

    context = {"form": form,
               "battery":battery,
               "blacklists":blacklists,
               "bonuses":bonuses}

    return render(request, "experiments/subject_management.html", context)

#### EXPORT #############################################################

# Export specific experiment data
@login_required
def export_battery(request,bid):
    battery = get_battery(bid,request)
    output_name = "expfactory_battery_%s.tsv" %(battery.id)
    return export_experiments(battery,output_name)

# Export specific experiment data
@login_required
def export_experiment(request,eid):
    battery = Battery.objects.filter(experiments__id=eid)[0]
    experiment = get_experiment(eid,request)
    output_name = "expfactory_experiment_%s.tsv" %(experiment.template.exp_id)
    return export_experiments(battery,output_name,[experiment.template.exp_id])

# General function to export some number of experiments
def export_experiments(battery,output_name,experiment_tags=None):

    # Get all results associated with Battery
    results = Result.objects.filter(battery=battery)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' %(output_name)
    writer = csv.writer(response,delimiter='\t')

    # Make a results pandas dataframe
    df = make_results_df(battery,results)

    # Specifying individual experiments removes between trial stufs
    if experiment_tags != None:
        if isinstance(experiment_tags,str):
            experiment_tags = [experiment_tags]
        df = df[df.experiment_exp_id.isin(experiment_tags)]

    # The program reading in values should fill in appropriate nan value
    df[df.isnull()]=""

    # Write header
    writer.writerow(df.columns.tolist())

    for row in df.iterrows():
        try:
            values = row[1].tolist()
            writer.writerow(values)
        except:
            pass

    return response

#### RESULTS VISUALIZATION #####################################################
@login_required
def battery_results_dashboard(request,bid):
    '''battery_results_dashboard will show the user a dashboard to select an experiment
    to view results for
    '''
    context = battery_results_context(request,bid)
    return render(request, "experiments/results_dashboard_battery.html", context)

@login_required
def battery_results_context(request,bid):
    '''battery_result_context is a general function used by experiment and battery
    results dashboard to return context with experiments completed for a battery
    '''
    battery = get_battery(bid,request)

    # Check if battery has results
    results = Result.objects.filter(battery=battery,completed=True)
    completed_experiments = numpy.unique([r.experiment.exp_id for r in results]).tolist()
    experiments = ExperimentTemplate.objects.filter(exp_id__in=completed_experiments)
    context = {'battery': battery,
               'experiments':experiments,
               'bid':battery.id}
    return context

@login_required
def experiment_results_dashboard(request,bid):
    '''experiment_results_dashboard will show the user a result for a particular experiment
    '''
    if request.method == "POST":
        battery = get_battery(bid,request)
        template = get_experiment_template(request.POST["experiment"],request)
        results = get_battery_results(battery,exp_id=template.exp_id,clean=True)
        if len(results) == 0:
            context = battery_results_context(request,bid)
            context["message"] = "%s does not have any completed results." %template.name
            return render(request, "experiments/results_dashboard_battery.html", context)

        # If we have results, save updated file for shiny server
        shiny_input = os.path.abspath("expfactory-explorer/data/%s_data.tsv" %template.exp_id)
        results.to_csv(shiny_input,sep="\t",encoding="utf-8")

        return HttpResponseRedirect('%s:3838' %settings.DOMAIN_NAME_HTTP)
    else:
        context = battery_results_context(request,bid)
        return render(request, "experiments/results_dashboard_battery.html", context)
