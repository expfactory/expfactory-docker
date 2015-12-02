from optparse import make_option
from numpy.random import choice
from django.core.management.base import BaseCommand
from boto.mturk.question import (AnswerSpecification, Overview, Question,
        QuestionContent, QuestionForm, FreeTextAnswer, FormattedContent)
from expdj.apps.turk.utils import get_connection, get_worker_url, get_worker_ids_past_tasks, get_host
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from expdj.apps.turk.models import Worker


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

    response = render_to_response("mturk_questions.html", context)
    # without this header, your iFrame will not render in Amazon
    response['x-frame-options'] = 'this_can_be_anything'
    return response
