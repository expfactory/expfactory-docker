from optparse import make_option
from numpy.random import choice
from expdj.apps.turk.models import HIT
from expdj.apps.turk.forms import HITForm
from expdj.apps.experiments.models import Battery
from expdj.apps.experiments.views import check_battery_edit_permission
from django.core.management.base import BaseCommand
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from expdj.apps.turk.utils import get_connection, get_worker_url, get_host, experiment_selection_time
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from expdj.apps.turk.models import Worker

#### GETS #############################################################

# get experiment
@login_required
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
    hit =  get_hit(hid,request)
    battery = hit.battery
     
    # This is the submit URL, either external or sandbox
    host = get_host()

    # worker has not accepted the task   
    if request.GET.get("assignmentId") == "ASSIGNMENT_ID_NOT_AVAILABLE":
        template = "mturk_battery_preview.html"
        task_list = hit.battery.experiments
        context = {
            "experiments":task_list
        }

    # worker has accepted the task
    else:
        template = "mturk_battery.html"
        worker_id = request.GET.get("workerId","")
        hit_id = request.GET.get("hitId","")
        turk_submit_to = request.GET.get("turkSubmitTo","")
        worker = get_worker(worker_id)
        assignment_id = request.GET.get("assignmentId","")

        # Get experiments the worker has not yet completed
        experiments = [x for x in battery.experiments.all() if x not in worker.experiments.all()]

        # If the worker has completed all that we have available
        if len(experiments) == 0:
            return render_to_response("worker_sorry.html")

        # Random selection of subset of tasks that do not exceed maximum time allowed
        task_list = experiment_selection_time(maximum_time_allower=hit.assignment_duration_in_seconds,
                                              experiments=experiments)

        context = {
            "worker_id": worker_id,
            "assignment_id": assignment_id,
            "amazon_host": host,
            "hit_id": hit_id,
            "experiments":task_list
        }

    response = render_to_response(template, context)
    # without this header, the iFrame will not render in Amazon
    response['x-frame-options'] = 'this_can_be_anything'
    return response


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


# Delete a hit
@login_required
def delete_hit(request, hid):
    hit = get_hit(hid,request)
    if check_battery_edit_permission(request,hit.battery):
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


def get_worker(worker_id):
    # (<Worker: WORKER_ID: experiments[0]>, True)    
    return Worker.objects.update_or_create(worker_id=worker_id)[0]
