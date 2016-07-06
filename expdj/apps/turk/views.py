from datetime import timedelta, datetime
import json
import os
import requests

from expfactory.battery import get_load_static, get_experiment_run
from numpy.random import choice
from optparse import make_option

from django.contrib.auth.decorators import login_required
from django.core.management.base import BaseCommand
from django.http.response import HttpResponseRedirect, HttpResponseForbidden, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from expdj.apps.experiments.models import Battery, ExperimentTemplate
from expdj.apps.experiments.views import check_battery_edit_permission, check_mturk_access, \
get_battery_intro, deploy_battery
from expdj.apps.experiments.utils import get_experiment_type, select_experiments
from expdj.apps.turk.forms import HITForm
from expdj.apps.turk.models import Worker, HIT, Assignment, Result, get_worker
from expdj.apps.turk.tasks import (assign_experiment_credit,
    check_battery_dependencies, get_unique_experiments)
from expdj.apps.turk.utils import (get_connection, get_host, get_worker_url,
    get_worker_experiments)
from expdj.settings import BASE_DIR,STATIC_ROOT,MEDIA_ROOT

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

@login_required
def manage_hit(request,bid,hid):
    '''manage_hit shows details about workers that have completed / not completed a HIT
    :param hid: the hit id
    '''
    hit =  get_hit(hid,request)
    hit.update()
    battery = hit.battery

    # Get different groups of assignments
    context = dict()
    context["assignments_approved"] = Assignment.objects.filter(status="A",hit=hit)
    context["assignments_rejected"] = Assignment.objects.filter(status="R",hit=hit)
    context["assignments_submit"] = Assignment.objects.filter(status="S",hit=hit)
    context["hit"] = hit
    assignments_remaining = Assignment.objects.filter(status=None,hit=hit)

    # Which of the HITS have time run out, but not submit?
    assignments_attention = []
    assignments_inprogress = []
    for assignment in assignments_remaining:
        needs_attention = False
        if assignment.accept_time != None:
            time_difference = timezone.now() - (assignment.accept_time + timedelta(hours=hit.assignment_duration_in_hours))
            # If the workers ending time has passed:
            if (assignment.accept_time + timedelta(hours=hit.assignment_duration_in_hours)) < timezone.now():
                assignments_attention.append(assignment)
                needs_attention = True

        if needs_attention == False:
            assignments_inprogress.append(assignment)

    context["assignments_inprogress"] = assignments_inprogress
    context["assignments_attention"] = assignments_attention

    return render(request, "turk/manage_hit.html", context)


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

        # Update the hit, only allow to continue if HIT is valid
        hit.update()
        if hit.status in ["D"]:
            return render_to_response("turk/hit_expired.html")

        battery = hit.battery
        aws = get_amazon_variables(request)

        if "" in [aws["worker_id"],aws["hit_id"]]:
            return render_to_response("turk/error_sorry.html")

        # Get Experiment Factory objects for each
        worker = get_worker(aws["worker_id"])

        check_battery_response = check_battery_view(battery, aws["worker_id"])
        if (check_battery_response):
            return check_battery_response

        # This is the submit URL, either external or sandbox
        host = get_host(hit)

        # Only supporting chrome
        if request.user_agent.browser.family != "Chrome":
            return render_to_response("turk/browser_sorry.html")

        # Try to get some info about browser, language, etc.
        browser = "%s,%s" %(request.user_agent.browser.family,request.user_agent.browser.version_string)
        platform = "%s,%s" %(request.user_agent.os.family,request.user_agent.os.version_string)

        # Initialize Assignment object, obtained from Amazon, and Result
        assignment,already_created = Assignment.objects.get_or_create(mturk_id=aws["assignment_id"],
                                                                      worker=worker,
                                                                      hit=hit)

        # if the assignment is new, we need to set up a task to run when the worker time runs out to allocate credit
        if already_created == False:
            assignment.accept_time = datetime.now()
            if hit.assignment_duration_in_hours != None:
                assign_experiment_credit.apply_async([worker.id],countdown=360*(hit.assignment_duration_in_hours))
            assignment.save()

        # Does the worker have experiments remaining for the hit?
        uncompleted_experiments = get_worker_experiments(worker,hit.battery)
        if len(uncompleted_experiments) == 0:
            # Thank you for your participation - no more experiments!
            return render_to_response("turk/worker_sorry.html")

        # if it's the last experiment, we will submit the result to amazon (only for surveys)
        last_experiment = False
        if len(uncompleted_experiments) == 1:
            last_experiment = True

        task_list = select_experiments(battery,uncompleted_experiments)
        experimentTemplate = ExperimentTemplate.objects.filter(exp_id=task_list[0].template.exp_id)[0]
        experiment_type = get_experiment_type(experimentTemplate)
        task_list = battery.experiments.filter(template=experimentTemplate)
        template = "%s/mturk_battery.html" %(experiment_type)

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
                              experiment_type=experiment_type,
                              context=aws,
                              task_list=task_list,
                              template=template,
                              next_page=None,
                              result=result,
                              last_experiment=last_experiment)

    else:
        return render_to_response("turk/error_sorry.html")

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


def survey_submit(request,rid,hid):
    '''survey_submit redirects user to a page to submit a result to amazon'''
    result = Result.objects.filter(id=rid)[0]
    amazon_host = get_host(result.assignment.hit)
    context = {"assignment_id":result.assignment.mturk_id,
               "worker_id":result.worker.id,
               "hit_id":hid,
               "amazon_host":amazon_host}
    return render(request, "surveys/worker_finished.html", context)

def not_consent_view(request):
    '''The worker has previewed the experiment, clicked Start Experiment, but not consented'''
    return render_to_response("turk/mturk_battery_preview.html")

def end_assignment(request,rid):
    '''end_assignment will change completed variable to True, preventing
    the worker from doing new experiments (if there are any remaining)
    and triggering function to allocate credit for what is completed
    '''
    result = Result.objects.filter(id=rid)[0]
    if result.assignment != None:
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
                hit.dispose()
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

def check_battery_view(battery, worker_id):
    missing_batteries, blocking_batteries = check_battery_dependencies(battery, worker_id)
    if missing_batteries or blocking_batteries:
        return render_to_response(
            "experiments/battery_requirements_not_met.html",
            context={'missing_batteries': missing_batteries,
                     'blocking_batteries': blocking_batteries}
        )
    else:
        return None
