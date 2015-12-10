from optparse import make_option
from numpy.random import choice
from expdj.apps.turk.models import HIT
from expdj.apps.turk.forms import HITForm
from expdj.apps.experiments.models import Battery
from django.core.management.base import BaseCommand
from django.contrib.auth.decorators import login_required
from expdj.apps.turk.utils import get_connection, get_worker_url, get_worker_ids_past_tasks, get_host
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

@login_required
def view_hit():
    '''view_hit
    a table to review a history of past hits
    '''
    print "WRITE ME"

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
    # TODO: check if user has permissions to delete HIT
    hit.delete()
    return redirect('batteries')


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
    # (<Worker: WORKER_ID: questions[0]>, True)    
    return Worker.objects.update_or_create(worker_id=worker_id)[0]    

def turk_questions(request,number_questions=10):

    host = get_host()

    
    #if request.GET.get("assignmentId") == "ASSIGNMENT_ID_NOT_AVAILABLE":
        # worker hasn't accepted the HIT (task) yet
    #    pass
    #else:
        # worked accepted the task
    #    pass
    # Under if worker accepted task:
    worker_id = "WORKER_ID"
    questions = get_flagged_questions()
    worker = get_worker(worker_id)
    assignment_id = "assignment_id"

    # Filter questions to those that the worker has not seen, and choose randomly
    questions = list(set(questions).difference(set(worker.questions.all())))
    questions = choice(questions,int(number_questions))

    # For each question, get all synsets
    synsets = [get_synsets(q.behavioral_trait.name) for q in questions]

    questions = zip(questions,synsets)
    #TODO: Some function here to select questions not seen?

    #worker_id = request.GET.get("workerId", "")
    #if worker_id in get_worker_ids_past_tasks():
        # you might want to guard against this case somehow
    #    pass

    # Get a random sample of questions

    context = {
        "worker_id": worker_id,#request.GET.get("workerId", ""),
        "assignment_id": assignment_id,#request.GET.get("assignmentId", ""),
        "amazon_host": host,
        "hit_id": "hitID",#request.GET.get("hitId", ""),
        "questions":questions
    }

    response = render_to_response("mturk_battery.html", context)
    # without this header, your iFrame will not render in Amazon
    response['x-frame-options'] = 'this_can_be_anything'
    return response
