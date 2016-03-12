from expdj.apps.experiments.views import check_battery_edit_permission, check_mturk_access, \
get_battery_intro, deploy_battery
from expdj.apps.turk.utils import get_connection, get_worker_url, get_host, get_worker_experiments, \
select_random_n
from django.http.response import HttpResponseRedirect, HttpResponseForbidden, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from expdj.apps.turk.tasks import assign_experiment_credit, get_unique_experiments
from expdj.apps.turk.models import Worker, HIT, Assignment, Result, get_worker
from expdj.apps.experiments.models import Battery, ExperimentTemplate
from expfactory.battery import get_load_static, get_experiment_run
from expdj.settings import BASE_DIR,STATIC_ROOT,MEDIA_ROOT
from django.contrib.auth.decorators import login_required
from django.core.management.base import BaseCommand
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

def get_amazon_variables(request):
    '''get_amazon_variables gets the "GET" variables from the URL,
       returned in a context that can be used across different experiment
       serving functions (local or mturk)
    '''

    # An assignmentID means that the worker has accepted the task
    assignment_id = request.GET.get("assignmentId","")
    worker_id = request.GET.get("workerId","")
    hit_id = request.GET.get("hitId","")
    turk_submit_to = request.GET.get("turkSubmitTo","")

    # worker has not accepted the task
    if assignment_id in ["ASSIGNMENT_ID_NOT_AVAILABLE",""]:
        assignment_id = None

    return {"worker_id": worker_id,
            "assignment_id": assignment_id,
            "hit_id": hit_id,
            "turk_submit_to":turk_submit_to}


def serve_hit(request,hid):
    '''serve_hit runs the experiment after accepting a hit
    :param hid: the hit id
    :param wid: the worker id
    :param aid: the assignment id
    '''

    # No robots allowed!
    if request.user_agent.is_bot:
        return render_to_response("turk/robot_sorry.html")

    # Not allowed on tablet or phone
    if request.user_agent.is_pc:

        hit =  get_hit(hid,request)
        battery = hit.battery
        aws = get_amazon_variables(request)

        if "" in [aws["worker_id"],aws["hit_id"]]:
            return render_to_response("turk/error_sorry.html")

        # Get Experiment Factory objects for each
        worker = get_worker(aws["worker_id"])

        # This is the submit URL, either external or sandbox
        host = get_host()

        # Try to get some info about browser, language, etc.
        browser = "%s,%s" %(request.user_agent.browser.family,request.user_agent.browser.version_string)
        platform = "%s,%s" %(request.user_agent.os.family,request.user_agent.os.version_string)

        # Initialize Assignment object, obtained from Amazon, and Result
        assignment,already_created = Assignment.objects.get_or_create(mturk_id=aws["assignment_id"],
                                                                      worker=worker,
                                                                      hit=hit)

        # if the assignment is new, we need to set up a task to run when the worker time runs out to allocate credit
        if already_created == False:
            assign_experiment_credit.apply_async(countdown=hit.assignment_duration_in_seconds)
        assignment.save()

        # Does the worker have experiments remaining for the hit?
        uncompleted_experiments = get_worker_experiments(worker,hit.battery)
        if len(uncompleted_experiments) == 0:
            # Thank you for your participation - no more experiments!
            return render_to_response("turk/worker_sorry.html")

        task_list = select_random_n(uncompleted_experiments,1)
        experimentTemplate = ExperimentTemplate.objects.filter(exp_id=task_list[0])[0]
        task_list = battery.experiments.filter(template=experimentTemplate)

        # Generate a new results object for the worker, assignment, experiment
        result,_ = Result.objects.update_or_create(worker=worker,
                                                   experiment=experimentTemplate,
                                                   assignment=assignment, # assignment has record of HIT
                                                   battery=hit.battery,
                                                   defaults={"browser":browser,"platform":platform})
        result.save()

        # Add variables to the context
        aws["amazon_host"] = host
        aws["uniqueId"] = result.id

        # If this is the last experiment, the finish button will link to a thank you page.
        if len(uncompleted_experiments) == 1:
            next_page = "/finished"

        return deploy_battery(deployment="docker-mturk",
                              battery=battery,
                              context=aws,
                              task_list=task_list,
                              template="turk/mturk_battery.html",
                              uncompleted_experiments=uncompleted_experiments,
                              next_page=None,
                              result=result)

    else:
        return render_to_response("turk/robot_sorry.html")

def preview_hit(request,hid):
    '''preview_hit is the view for when a worker has not accepted the task'''

    # No robots allowed!
    if request.user_agent.is_bot:
        return render_to_response("turk/robot_sorry.html")

    if request.user_agent.is_pc:

        hit =  get_hit(hid,request)
        battery = hit.battery
        context = get_amazon_variables(request)
        context["instruction_forms"] = get_battery_intro(battery)
        context["hit_uid"] = hid
        context["start_url"] = "/accept/%s/?assignmentId=%s&workerId=%s&turkSubmitTo=%s&hitId=%s" %(hid,
                                                                                                    context["assignment_id"],
                                                                                                    context["worker_id"],
                                                                                                    context["turk_submit_to"],
                                                                                                    context["hit_id"])

        response = render_to_response("turk/serve_battery_intro.html", context)

        # without this header, the iFrame will not render in Amazon
        response['x-frame-options'] = 'nobody_ever_goes_in_nobody_ever_goes_out'
        return response


def finished_view(request):
    '''finished_view thanks worker for participation, and gives submit button
    '''
    return render_to_response("turk/worker_sorry.html")


def not_consent_view(request):
    '''The worker has previewed the experiment, clicked Start Experiment, but not consented'''
    return render_to_response("turk/mturk_battery_preview.html")

def end_assignment(request,rid):
    '''end_assignment will change completed variable to True, preventing
    the worker from doing new experiments (if there are any remaining)
    and triggering function to allocate credit for what is completed
    '''
    result = Result.objects.filter(id=rid)[0]
    if assignment != None:
        assignment = result.assignment
        assignment.completed = True
        assignment.save()
        assign_experiment_credit(result.worker.id)
    return render_to_response("turk/worker_sorry.html")

@login_required
def multiple_new_hit(request, bid):

    mturk_permission = check_mturk_access(request)

    if mturk_permission == True:
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
                      "battery":battery,
                      "mturk_permission":mturk_permission}

        return render(request, "turk/multiple_new_hit.html", context)
    else:
        return HttpResponseForbidden()


@login_required
def edit_hit(request, bid, hid=None):

    mturk_permission = check_mturk_access(request)

    if mturk_permission == True:
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

        return render(request, "turk/new_hit.html", context)
    else:
        return HttpResponseForbidden()

# Expire a hit
@login_required
def expire_hit(request, hid):

    mturk_permission = check_mturk_access(request)
    if mturk_permission == True:

        hit = get_hit(hid,request)
        battery = hit.battery
        if check_battery_edit_permission(request,hit.battery):
            # Remove expired/deleted hits from interface
            try:
                hit.expire()
            except:
                hit.delete()
        return redirect(battery.get_absolute_url())
    else:
        return HttpResponseForbidden()

# Delete a hit
@login_required
def delete_hit(request, hid):
    mturk_permission = check_mturk_access(request)
    if mturk_permission == True:
        hit = get_hit(hid,request)
        if check_battery_edit_permission(request,hit.battery):
            # A hit deleted in Amazon cannot be expired
            try:
                hit.expire()
            except:
                pass
            hit.delete()
        return redirect(hit.battery.get_absolute_url())
    else:
        return HttpResponseForbidden()

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
            battery = result.battery
            result.taskdata = data["taskdata"]["data"]
            result.current_trial = data["taskdata"]["currenttrial"]
            result.save()

            # if the worker finished the current experiment
            if data["djstatus"] == "FINISHED":
                # Mark experiment as completed
                result.completed = True
                result.save()

                # if the worker has completed all tasks, give final credit
                completed_experiments = get_worker_experiments(result.worker,battery,completed=True)
                if len(completed_experiments) == battery.experiments.count():
                    assignment = Assignment.objects.filter(id=result.assignment_id)[0]
                    assignment.update()
                    assign_experiment_credit.apply_async(args=[result.worker.id])

            data = json.dumps(data)

    else:
        data = json.dumps({"message":"received!"})
    return HttpResponse(data, content_type='application/json')

