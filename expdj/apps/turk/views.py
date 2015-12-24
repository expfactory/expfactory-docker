from expdj.apps.turk.utils import get_connection, get_worker_url, get_host, select_experiments_time
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from django.http.response import HttpResponseRedirect, HttpResponseForbidden, HttpResponse, Http404
from expdj.apps.turk.models import Worker, HIT, Assignment, Result, get_worker
from expdj.apps.experiments.views import check_battery_edit_permission
from expdj.settings import BASE_DIR,STATIC_ROOT,MEDIA_ROOT
from django.contrib.auth.decorators import login_required
from expfactory.battery import get_load_static, get_concat_js
from django.core.management.base import BaseCommand
from expdj.apps.experiments.models import Battery
from expdj.apps.turk.forms import HITForm
from optparse import make_option
from numpy.random import choice
import json
import os

media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)


#### GETS #############################################################

# get experiment
def get_hit(hid,request,mode=None):
    keyargs = {'pk':hid}
    try:
        hit = HIT.objects.get(**keyargs)
    except HIT.DoesNotExist:
        raise Http404
    else:
        return hit

#### VIEWS ############################################################


def serve_hit(request,hid):

    # No robots allowed!
    if request.user_agent.is_bot:
        return render_to_response("robot_sorry.html")

    if request.user_agent.is_pc:

        hit =  get_hit(hid,request)
        battery = hit.battery

        # This is the submit URL, either external or sandbox
        host = get_host()

        # An assignmentID means that the worker has accepted the task
        assignment_id = request.GET.get("assignmentId","")

        # worker has not accepted the task
        if assignment_id in ["ASSIGNMENT_ID_NOT_AVAILABLE",""]:
            template = "mturk_battery_preview.html"
            task_list = battery.experiments.all()
            context = {
                "experiments":task_list
            }

        # worker has accepted the task
        else:
            template = "mturk_battery.html"
            worker_id = request.GET.get("workerId","")
            hit_id = request.GET.get("hitId","")
            turk_submit_to = request.GET.get("turkSubmitTo","")

            if "" in [worker_id,hit_id]:
                return render_to_response("error_sorry.html")

            # Get Experiment Factory objects for each
            worker = get_worker(worker_id)
            hit = get_hit(hid,request)

            # Try to get some info about browser, language, etc.
            browser = "%s,%s" %(request.user_agent.browser.family,request.user_agent.browser.version_string)
            platform = "%s,%s" %(request.user_agent.os.family,request.user_agent.os.version_string)

            # Initialize Assignment object, obtained from Amazon, and Result
            assignment,_ = Assignment.objects.get_or_create(mturk_id=assignment_id,hit=hit,worker=worker)
            result,_ = Result.objects.update_or_create(worker=worker,         # worker, assignment, are unique
                                                       assignment=assignment, # assignment has record of HIT
                                                       defaults={"browser":browser,"platform":platform})

            result.save()

            # Get experiments the worker has not yet completed
            completed_experiments = [x.experiment for x in worker.experiments.all() if x.battery == battery]
            experiments = [x for x in battery.experiments.all() if x not in completed_experiments]

            # If the worker has completed all that we have available
            if len(experiments) == 0:
                return render_to_response("worker_sorry.html")

            # Random selection of subset of tasks that do not exceed maximum time allowed
            task_list = select_experiments_time(hit.assignment_duration_in_seconds,experiments)

            context = {
                "worker_id": worker_id,
                "assignment_id": assignment_id,
                "amazon_host": host,
                "hit_id": hit_id,
                "experiments":task_list,
                "uniqueId":result.id
            }

        # Get experiment folders
        experiment_folders = [os.path.join(media_dir,"experiments",x.template.tag) for x in task_list]
        loadjs = get_load_static(experiment_folders,url_prefix="/")
        concatjs = get_concat_js(experiment_folders)
        context["experiment_load"] = loadjs
        context["experiment_concat"] = concatjs

        response = render_to_response(template, context)
        # without this header, the iFrame will not render in Amazon
        response['x-frame-options'] = 'this_can_be_anything'
        return response

    else:
        return render_to_response("pc_sorry.html")


@login_required
def multiple_new_hit(request, bid):
    battery = Battery.objects.get(pk=bid)
    if not request.user.has_perm('battery.edit_battery', battery):
        return HttpResponseForbidden()

    is_owner = battery.owner == request.user

    if request.method == "POST":
        # A hit is generated for each batch
        for x in range(int(request.POST["id_number_batches"])):
            hit = HIT(owner=request.user,battery=battery)
            form = HITForm(request.POST,instance=hit)
            if form.is_valid():
                hit = form.save(commit=False)
                hit.title = "%s #%s" %(hit.title,x)
                hit.save()
        return HttpResponseRedirect(battery.get_absolute_url())
    else:

        context = {"is_owner": is_owner,
                  "header_text":battery.name,
                  "battery":battery}

    return render(request, "multiple_new_hit.html", context)


@login_required
def edit_hit(request, bid, hid=None):
    battery = Battery.objects.get(pk=bid)
    header_text = "%s HIT" %(battery.name)
    if not request.user.has_perm('battery.edit_battery', battery):
        return HttpResponseForbidden()

    if hid:
        hit = get_hit(hid,request)
        is_owner = battery.owner == request.user
        header_text = hit.title
    else:
        is_owner = True
        hit = HIT(owner=request.user,battery=battery)
    if request.method == "POST":
        if is_owner:
            form = HITForm(request.POST,instance=hit)
        if form.is_valid():
            hit = form.save(commit=False)
            hit.save()
            return HttpResponseRedirect(battery.get_absolute_url())
    else:
        if is_owner:
            form = HITForm(instance=hit)
        else:
            form = HITForm(instance=hit)

    context = {"form": form,
               "is_owner": is_owner,
               "header_text":header_text}

    return render(request, "new_hit.html", context)

# Expire a hit
@login_required
def expire_hit(request, hid):
    hit = get_hit(hid,request)
    if check_battery_edit_permission(request,hit.battery):
        hit.expire()
    return redirect(hit.battery.get_absolute_url())

# Delete a hit
@login_required
def delete_hit(request, hid):
    hit = get_hit(hid,request)
    if check_battery_edit_permission(request,hit.battery):
        hit.expire()
        hit.delete()
    return redirect(hit.battery.get_absolute_url())

def get_flagged_questions(number=None):
    """get_flagged_questions
    return questions that are flagged for curation
    Parameters
    ==========
    number: int
       the number of questions to return. If None, will return all
    """
    questions = QuestionModel.objects.filter(flagged_for_curation=True)
    if number == None:
        return questions
    return choice(questions,int(number))


#### DATA #############################################################

# These views are to work with backbone.js
def sync(request,rid=None):
    '''sync
    view/method for running experiments to get data from the server
    :param rid: the result object ID, obtained before user sees page
    '''

    if request.method == "POST":

        data = json.loads(request.body)

        if rid != None:
        # Update the result, already has worker and assignment ID stored
            result,_ = Result.objects.get_or_create(id=data["taskdata"]["uniqueId"])
            result.taskdata = data["taskdata"]["data"]
            result.current_trial = data["taskdata"]["currenttrial"]
            result.completed = True
            result.save()

            if data["djstatus"] == "FINISHED":
                # Update the assignmentID object, obtained from Amazon
                assignment = Assignment.objects.update(id=result.assignment_id)
                assignment.save()
                # Add the experiments to the worker's log - tasks associated with batteries change
                worker = assignment.worker
                new_experiments = [e for e in assignment.hit.battery.experiments.all() if e not in worker.experiments.all()]
                [worker.experiments.add(x) for x in new_experiments]
                worker.save()
    else:
        data = json.dumps({"message":"received!"})
    return HttpResponse(data, content_type='application/json')
