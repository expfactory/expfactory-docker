#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import datetime

import boto
from boto.mturk.price import Price
from boto.mturk.qualification import (AdultRequirement, LocaleRequirement,
                                      NumberHitsApprovedRequirement,
                                      PercentAssignmentsApprovedRequirement,
                                      Qualifications, Requirement)
from boto.mturk.question import ExternalQuestion
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import DO_NOTHING, Q
from django.db.models.signals import pre_init
from django.utils import timezone
from jsonfield import JSONField

from expdj.apps.experiments.models import (Battery, Experiment,
                                           ExperimentTemplate)
from expdj.apps.turk.utils import (amazon_string_to_datetime, get_connection,
                                   get_credentials, get_time_difference,
                                   to_dict)
from expdj.settings import BASE_DIR, DOMAIN_NAME


def init_connection_callback(sender, **signal_args):
    """Mechanical Turk connection signal callback

    By using Django pre-init signals, class level connections can be
    made available to Django models that configure this pre-init
    signal.
    """
    sender.args = sender
    object_args = signal_args['kwargs']
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY_ID = get_credentials(
        battery=sender.battery)
    sender.connection = get_connection(
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY_ID, sender)


class DisposeException(Exception):
    """Unable to Dispose of HIT Exception"""

    def __init__(self, value):
        self.parameter = value

    def __unicode__(self):
        return repr(self.parameter)
    __str__ = __unicode__


class Worker(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=200,
        null=False,
        blank=False)
    session_count = models.PositiveIntegerField(default=0, help_text=(
        "The number of one hour sessions completed by the worker."))
    visit_count = models.PositiveIntegerField(
        default=0, help_text=("The total number of visits"))
    last_visit_time = models.DateTimeField(null=True, blank=True, help_text=(
        "The date and time, in UTC, the Worker last visited"))

    def __str__(self):
        return "%s" % (self.id)

    def __unicode__(self):
        return "%s" % (self.id)

    class Meta:
        ordering = ['id']


def get_worker(worker_id, create=True):
    '''get a worker
    :param create: update or create
    :param worker_id: the unique identifier for the worker
    '''
    # (<Worker: WORKER_ID: experiments[0]>, True)
    now = timezone.now()

    if create:
        worker, _ = Worker.objects.update_or_create(id=worker_id)
    else:
        worker = Worker.objects.filter(id=worker_id)[0]

    if worker.last_visit_time is not None:  # minutes
        time_difference = get_time_difference(worker.last_visit_time, now)
        # If more than an hour has passed, this is a new session
        if time_difference >= 60.0:
            worker.session_count += 1
    else:  # this is the first session
        worker.session_count = 1

    # Update the last visit time to be now
    worker.visit_count += 1
    worker.last_visit_time = now
    worker.save()
    return worker


class HIT(models.Model):
    """An Amazon Mechanical Turk Human Intelligence Task as a Django Model"""

    def __str__(self):
        return "%s: %s" % (self.title, self.battery)

    def __unicode__(self):
        return "%s: %s" % (self.title, self.battery)

    (ASSIGNABLE, UNASSIGNABLE, REVIEWABLE, REVIEWING, DISPOSED) = (
        'A', 'U', 'R', 'G', 'D')

    (_ASSIGNABLE, _UNASSIGNABLE, _REVIEWABLE, _REVIEWING, _DISPOSED) = (
        "Assignable", "Unassignable", "Reviewable", "Reviewing", "Disposed")

    (NOT_REVIEWED, MARKED_FOR_REVIEW, REVIEWED_APPROPRIATE,
     REVIEWED_INAPPROPRIATE) = ("N", "M", "R", "I")

    (_NOT_REVIEWED, _MARKED_FOR_REVIEW, _REVIEWED_APPROPRIATE,
     _REVIEWED_INAPPROPRIATE) = ("NotReviewed", "MarkedForReview",
                                 "ReviewedAppropriate", "ReviewedInappropriate")

    STATUS_CHOICES = (
        (ASSIGNABLE, _ASSIGNABLE),
        (UNASSIGNABLE, _UNASSIGNABLE),
        (REVIEWABLE, _REVIEWABLE),
        (REVIEWING, _REVIEWING),
        (DISPOSED, _DISPOSED),
    )
    REVIEW_CHOICES = (
        (NOT_REVIEWED, _NOT_REVIEWED),
        (MARKED_FOR_REVIEW, _MARKED_FOR_REVIEW),
        (REVIEWED_APPROPRIATE, _REVIEWED_APPROPRIATE),
        (REVIEWED_INAPPROPRIATE, _REVIEWED_INAPPROPRIATE)
    )

    LOCALE_CHOICES = (('US', 'USA'),
                      ('None', 'No Restriction'),
                      ('CA', 'Canada'),
                      ('IN', 'India'))

    OPERATOR_CHOICES = (
        ("LessThan", "Less Than"),
        ("LessThanOrEqualTo", "Less Than Or Equal To"),
        ("GreaterThan", "Greater Than"),
        ("GreaterThanOrEqualTo", "Greater Than Or Equal To"),
        ("EqualTo", "Equal To"),
        ("NotEqualTo", "Not Equal To"),
        ("Exists", "Exists"),
        ("DoesNotExist", "Does Not Exist")
    )

    # Convenience lookup dictionaries for the above lists
    reverse_status_lookup = dict((v, k) for k, v in STATUS_CHOICES)
    reverse_review_lookup = dict((v, k) for k, v in REVIEW_CHOICES)

    # A HIT must be associated with a battery
    battery = models.ForeignKey(
        Battery,
        help_text="Battery of Experiments deployed by the HIT.",
        verbose_name="Experiment Battery",
        null=False,
        blank=False,
        on_delete=DO_NOTHING)
    owner = models.ForeignKey(User, on_delete=DO_NOTHING)
    mturk_id = models.CharField(
        "HIT ID",
        max_length=255,
        unique=True,
        null=True,
        help_text="A unique identifier for the HIT")
    hit_type_id = models.CharField(
        "HIT Type ID",
        max_length=255,
        null=True,
        blank=True,
        help_text="The ID of the HIT type of this HIT")
    creation_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The UTC date and time the HIT was created")
    title = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        help_text="The title of the HIT")
    description = models.TextField(
        null=False,
        blank=False,
        help_text="A general description of the HIT")
    keywords = models.TextField("Keywords", null=True, blank=True, help_text=(
        "One or more words or phrases that describe the HIT, separated by commas."))
    status = models.CharField(
        "HIT Status",
        max_length=1,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
        help_text="The status of the HIT and its assignments")
    reward = models.DecimalField(max_digits=5, decimal_places=3, null=False, blank=False, help_text=(
        "The amount of money the requester will pay a worker for successfully completing the HIT"))
    lifetime_in_hours = models.FloatField(null=True, blank=True, help_text=(
        "The amount of time, in hours, after which the HIT is no longer available for users to accept."))
    assignment_duration_in_hours = models.FloatField(
        null=False,
        blank=False,
        help_text=("The length of time, in hours, that a worker has to complete the HIT after accepting it."),
        validators=[
            MinValueValidator(0.0)])
    max_assignments = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=1,
        help_text=("The number of times the HIT can be accepted and  completed before the HIT becomes unavailable."),
        validators=[
            MinValueValidator(0.0)])
    auto_approval_delay_in_seconds = models.PositiveIntegerField(null=True, blank=True, help_text=(
        "The amount of time, in seconds after the worker submits an assignment for the HIT that the results are automatically approved by the requester."))
    requester_annotation = models.TextField(null=True, blank=True, help_text=(
        "An arbitrary data field the Requester who created the HIT can use. This field is visible only to the creator of the HIT."))
    number_of_similar_hits = models.PositiveIntegerField(null=True, blank=True, help_text=(
        "The number of HITs with fields identical to this HIT, other than the Question field."))
    review_status = models.CharField(
        "HIT Review Status",
        max_length=1,
        choices=REVIEW_CHOICES,
        null=True,
        blank=True,
        help_text="Indicates the review status of the HIT.")
    number_of_assignments_pending = models.PositiveIntegerField(null=True, blank=True, help_text=(
        "The number of assignments for this HIT that have been accepted by Workers, but have not yet been submitted, returned, abandoned."))
    number_of_assignments_available = models.PositiveIntegerField(null=True, blank=True, help_text=(
        "The number of assignments for this HIT that are available for Workers to accept"))
    number_of_assignments_completed = models.PositiveIntegerField(null=True, blank=True, help_text=(
        "The number of assignments for this HIT that have been approved or rejected."))

    # Worker Qualification Variables
    qualification_number_hits_approved = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=("Worker Qualification: number of hits approved."),
        verbose_name="worker hits approved")
    qualification_percent_assignments_approved = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=("Worker Qualification: percent assignments approved."),
        verbose_name="worker percent assignments approved",
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)])
    qualification_adult = models.BooleanField(
        choices=(
            (False,
             'Not Adult'),
            (True,
             'Adult')),
        default=True,
        help_text="Worker Qualification: Adult or Under 18",
        verbose_name="worker qualification adult")
    qualification_locale = models.CharField(
        max_length=255,
        choices=LOCALE_CHOICES,
        default='None',
        help_text="Worker Qualification: location requirement",
        verbose_name="worker qualification locale")

    qualification_custom_operator = models.CharField(
        "operator to compare variable to value",
        max_length=200,
        choices=OPERATOR_CHOICES,
        null=True,
        blank=True
    )
    qualification_custom_value = models.IntegerField(null=True, blank=True)
    qualification_custom = models.CharField(
        max_length=255,
        default=None,
        help_text="Worker Qualification: custom qualification ID",
        verbose_name="worker qualification custom",
        null=True,
        blank=True
    )

    # Deployment specification
    sandbox = models.BooleanField(
        choices=(
            (False,
             'Amazon Mechanical Turk'),
            (True,
             'Amazon Mechanical Turk Sandbox')),
        default=True,
        verbose_name="Deployment to Amazon Mechanical Turk, or Test on Sandbox")

    def disable(self):
        """Disable/Destroy HIT that is no longer needed
        """
        # Check for new results and cache a copy in Django model
        self.update(do_update_assignments=True)
        self.connection.dispose_hit(self.mturk_id)

    def dispose(self):
        """Dispose of a HIT that is no longer needed.

        Only HITs in the "Reviewable" state, with all submitted
        assignments approved or rejected, can be disposed. This removes
        the data from Amazon Mechanical Turk, but not from the local
        Django database (i.e., a local cache copy is kept).

        This is a wrapper around the Boto API. Also see:
        http://boto.cloudhackers.com/en/latest/ref/mturk.html
        """

        # Don't waste time or resources if already marked as DISPOSED
        if self.status == self.DISPOSED:
            return

        # Check for new results and cache a copy in Django model
        self.update(do_update_assignments=True)

        # Verify HIT is reviewable
        if self.status != self.REVIEWABLE:
            raise DisposeException(
                "Can't dispose of HIT (%s) that is still in %s status." % (
                    self.mturk_id,
                    dict(self.STATUS_CHOICES)[self.status]))

        # Verify Assignments are either APPROVED or REJECTED
        for assignment in self.assignments.all():
            if assignment.status not in [Assignment.APPROVED,
                                         Assignment.REJECTED]:
                raise DisposeException(
                    "Can't dispose of HIT (%s) because Assignment "
                    "(%s) is not approved or rejected." % (
                        self.mturk_id, assignment.mturk_id))

        # Checks pass. Dispose of HIT and update status
        self.connection.dispose_hit(self.mturk_id)
        self.update()

    def expire(self):
        """Expire a HIT that is no longer needed as Mechanical Turk service"""
        if not self.has_connection():
            self.generate_connection()
        self.connection.expire_hit(self.mturk_id)
        self.update()

    def extend(self, assignments_increment=None, expiration_increment=None):
        """Increase the maximum assignments or extend the expiration date"""
        if not self.has_connection():
            self.generate_connection()
        self.connection.extend_hit(self.mturk_id,
                                   assignments_increment=assignments_increment,
                                   expiration_increment=expiration_increment)
        self.update()

    def set_reviewing(self, revert=None):
        """Toggle HIT status between Reviewable and Reviewing"""
        if not self.has_connection():
            self.generate_connection()
        self.connection.set_reviewing(self.mturk_id, revert=revert)
        self.update()

    def generate_connection(self):
        # Get the aws access id from the credentials file
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY_ID = get_credentials(
            battery=self.battery)
        self.connection = get_connection(
            AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY_ID, hit=self)

    def has_connection(self):
        if "turk.HIT.connection" in [x.__str__() for x in self._meta.fields]:
            return True
        return False

    def send_hit(self):

        # First check for qualifications
        qualifications = Qualifications()
        if self.qualification_adult:
            qualifications.add(AdultRequirement("EqualTo", 1))
        else:
            qualifications.add(AdultRequirement("EqualTo", 0))
        if self.qualification_custom not in [None, ""]:
            qualifications.add(
                Requirement(
                    self.qualification_custom,
                    self.qualification_custom_operator,
                    self.qualification_custom_value,
                    required_to_preview=True))
        if self.qualification_number_hits_approved is not None:
            qual_number_hits = NumberHitsApprovedRequirement(
                "GreaterThan", self.qualification_number_hits_approved)
            qualifications.add(qual_number_hits)
        if self.qualification_percent_assignments_approved is not None:
            qual_perc_approved = PercentAssignmentsApprovedRequirement(
                "GreaterThan", self.qualification_percent_assignments_approved)
            qualifications.add(qual_perc_approved)
        if self.qualification_locale != 'None':
            qualifications.add(
                LocaleRequirement(
                    "EqualTo",
                    self.qualification_locale))

        # Domain name must be https
        url = "%s/turk/%s" % (DOMAIN_NAME, self.id)
        frame_height = 900
        questionform = ExternalQuestion(url, frame_height)

        if len(qualifications.requirements) > 0:
            result = self.connection.create_hit(
                title=self.title,
                description=self.description,
                keywords=self.keywords,
                duration=datetime.timedelta(
                    self.assignment_duration_in_hours / 24.0),
                lifetime=datetime.timedelta(
                    self.lifetime_in_hours / 24.0),
                max_assignments=self.max_assignments,
                question=questionform,
                qualifications=qualifications,
                reward=Price(
                    amount=self.reward),
                response_groups=(
                    'Minimal',
                    'HITDetail'))[0]

        else:
            result = self.connection.create_hit(
                title=self.title,
                description=self.description,
                keywords=self.keywords,
                duration=datetime.timedelta(
                    self.assignment_duration_in_hours / 24.0),
                lifetime=datetime.timedelta(
                    self.lifetime_in_hours / 24.0),
                max_assignments=self.max_assignments,
                question=questionform,
                reward=Price(
                    amount=self.reward),
                response_groups=(
                    'Minimal',
                    'HITDetail'))[0]

        # Update our hit object with the aws HIT
        self.mturk_id = result.HITId

        # When we generate the hit, we won't have any assignments to update
        self.update(mturk_hit=result)

    def save(self, *args, **kwargs):
        '''save will generate a connection and get
        the mturk_id for hits that have not been saved yet
        '''
        is_new_hit = False
        send_to_mturk = False
        if not self.pk:
            is_new_hit = True
        if not self.mturk_id:
            send_to_mturk = True
        super(HIT, self).save(*args, **kwargs)
        if is_new_hit:
            self.generate_connection()
        if send_to_mturk:
            self.send_hit()

    def update(self, mturk_hit=None, do_update_assignments=False):
        """Update self with Mechanical Turk API data

        If mturk_hit is given to this function, it should be a Boto
        hit object that represents a Mechanical Turk HIT instance.
        Otherwise, Amazon Mechanical Turk is contacted to get additional
        information.

        This instance's attributes are updated.
        """
        self.generate_connection()
        if mturk_hit is None or not hasattr(mturk_hit, "HITStatus"):
            hit = self.connection.get_hit(self.mturk_id)[0]
        else:
            assert isinstance(mturk_hit, boto.mturk.connection.HIT)
            hit = mturk_hit

        self.status = HIT.reverse_status_lookup[hit.HITStatus]
        self.reward = hit.Amount
        self.assignment_duration_in_seconds = hit.AssignmentDurationInSeconds
        self.auto_approval_delay_in_seconds = hit.AutoApprovalDelayInSeconds
        self.max_assignments = hit.MaxAssignments
        self.creation_time = amazon_string_to_datetime(hit.CreationTime)
        self.description = hit.Description
        self.title = hit.Title
        self.hit_type_id = hit.HITTypeId
        self.keywords = hit.Keywords
        if hasattr(self, 'NumberOfAssignmentsCompleted'):
            self.number_of_assignments_completed = hit.NumberOfAssignmentsCompleted
        if hasattr(self, 'NumberOfAssignmentsAvailable'):
            self.number_of_assignments_available = hit.NumberOfAssignmentsAvailable
        if hasattr(self, 'NumberOfAssignmentsPending'):
            self.number_of_assignments_pending = hit.NumberOfAssignmentsPending
        # 'CurrencyCode', 'Reward', 'Expiration', 'expired']

        self.save()

        if do_update_assignments:
            self.update_assignments()

    def update_assignments(self, page_number=1, page_size=10, update_all=True):
        self.generate_connection()
        assignments = self.connection.get_assignments(self.mturk_id,
                                                      page_size=page_size,
                                                      page_number=page_number)
        for mturk_assignment in assignments:
            assert mturk_assignment.HITId == self.mturk_id
            djurk_assignment = Assignment.objects.get_or_create(
                mturk_id=mturk_assignment.AssignmentId, hit=self)[0]
            djurk_assignment.update(mturk_assignment, hit=self)
        if update_all and int(assignments.PageNumber) *\
                page_size < int(assignments.TotalNumResults):
            self.update_assignments(page_number + 1, page_size, update_all)

    class Meta:
        verbose_name = "HIT"
        verbose_name_plural = "HITs"

    def __unicode__(self):
        return u"HIT: %s" % self.mturk_id


class Assignment(models.Model):
    '''An Amazon Mechanical Turk Assignment'''

    (_SUBMITTED, _APPROVED, _REJECTED) = ("Submitted", "Approved", "Rejected")
    (SUBMITTED, APPROVED, REJECTED) = ("S", "A", "R")

    STATUS_CHOICES = (
        (SUBMITTED, _SUBMITTED),
        (APPROVED, _APPROVED),
        (REJECTED, _REJECTED),
    )
    # Convenience lookup dictionaries for the above lists
    reverse_status_lookup = dict((v, k) for k, v in STATUS_CHOICES)

    mturk_id = models.CharField(
        "Assignment ID",
        max_length=255,
        blank=True,
        null=True,
        help_text="A unique identifier for the assignment")
    worker = models.ForeignKey(
        Worker,
        null=True,
        blank=True,
        help_text="The ID of the Worker who accepted the HIT",
        on_delete=DO_NOTHING)
    hit = models.ForeignKey(HIT, null=True, blank=True,
                            related_name='assignments',
                            on_delete=DO_NOTHING)
    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
        help_text="The status of the assignment")
    auto_approval_time = models.DateTimeField(null=True, blank=True, help_text=(
        "If results have been submitted, this is the date and time, in UTC,  the results of the assignment are considered approved automatically if they have not already been explicitly approved or rejected by the requester"))
    accept_time = models.DateTimeField(null=True, blank=True, help_text=(
        "The date and time, in UTC, the Worker accepted the assignment"))
    submit_time = models.DateTimeField(null=True, blank=True, help_text=(
        "If the Worker has submitted results, this is the date and time, in UTC, the assignment was submitted"))
    approval_time = models.DateTimeField(null=True, blank=True, help_text=(
        "If requester has approved the results, this is the date and time, in UTC, the results were approved"))
    rejection_time = models.DateTimeField(null=True, blank=True, help_text=(
        "If requester has rejected the results, this is the date and time, in UTC, the results were rejected"))
    deadline = models.DateTimeField(null=True, blank=True, help_text=(
        "The date and time, in UTC, of the deadline for the assignment"))
    requester_feedback = models.TextField(null=True, blank=True, help_text=(
        "The optional text included with the call to either approve or reject the assignment."))
    completed = models.BooleanField(
        choices=(
            (False,
             'Not completed'),
            (True,
             'Completed')),
        default=False,
        verbose_name="participant completed the entire assignment")

    def create(self):
        init_connection_callback(sender=self.hit)

    def approve(self, feedback=None):
        """Thin wrapper around Boto approve function."""
        self.hit.generate_connection()
        self.hit.connection.approve_assignment(
            self.mturk_id, feedback=feedback)
        self.update()

    def reject(self, feedback=None):
        """Thin wrapper around Boto reject function."""
        self.hit.generate_connection()
        self.hit.connection.reject_assignment(self.mturk_id, feedback=feedback)
        self.update()

    def bonus(self, value=0.0, feedback=None):
        """Thin wrapper around Boto bonus function."""
        self.hit.generate_connection()

        self.hit.connection.grant_bonus(
            self.worker_id,
            self.mturk_id,
            bonus_price=boto.mturk.price.Price(amount=value),
            reason=feedback)
        self.update()

    def update(self, mturk_assignment=None, hit=None):
        """Update self with Mechanical Turk API data

        If mturk_assignment is given to this function, it should be
        a Boto assignment object that represents a Mechanical Turk
        Assignment instance.  Otherwise, Amazon Mechanical Turk is
        contacted.

        This instance's attributes are updated.
        """
        self.hit.generate_connection()
        assignment = None

        if mturk_assignment is None:
            hit = self.hit.connection.get_hit(self.hit.mturk_id)[0]
            for a in self.hit.connection.get_assignments(hit.HITId):
                # While we have the query, we may as well update
                if a.AssignmentId == self.mturk_id:
                    # That's this record. Hold onto so we can update below
                    assignment = a
                else:
                    other_assignments = Assignment.objects.filter(
                        mturk_id=a.AssignmentId)
                    # Amazon can reuse Assignment ids, so there is an
                    # occasional duplicate
                    for other_assignment in other_assignments:
                        if other_assignment.worker_id == a.WorkerId:
                            other_assignment.update(a)
        else:
            assert isinstance(
                mturk_assignment,
                boto.mturk.connection.Assignment)
            assignment = mturk_assignment

        if assignment is not None:
            self.status = self.reverse_status_lookup[assignment.AssignmentStatus]
            self.worker_id = get_worker(assignment.WorkerId)
            self.submit_time = amazon_string_to_datetime(assignment.SubmitTime)
            self.accept_time = amazon_string_to_datetime(assignment.AcceptTime)
            self.auto_approval_time = amazon_string_to_datetime(
                assignment.AutoApprovalTime)
            self.submit_time = amazon_string_to_datetime(assignment.SubmitTime)

            # Different response groups for query
            if hasattr(assignment, 'RejectionTime'):
                self.rejection_time = amazon_string_to_datetime(
                    assignment.RejectionTime)
            if hasattr(assignment, 'ApprovalTime'):
                self.approval_time = amazon_string_to_datetime(
                    assignment.ApprovalTime)

        self.save()

    def __unicode__(self):
        return self.mturk_id

    def __repr__(self):
        return u"Assignment: %s" % self.mturk_id
    __str__ = __unicode__


class Result(models.Model):
    '''A result holds a battery id and an experiment template, to keep track of the battery/experiment combinations that a worker has completed'''
    taskdata = JSONField(
        null=True, blank=True, load_kwargs={
            'object_pairs_hook': collections.OrderedDict})
    version = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Experiment version (github commit) at completion time of result")
    worker = models.ForeignKey(
        Worker,
        null=False,
        blank=False,
        related_name='result_worker',
        on_delete=DO_NOTHING)
    experiment = models.ForeignKey(
        ExperimentTemplate,
        help_text="The Experiment Template completed by the worker in the battery",
        null=False,
        blank=False,
        on_delete=DO_NOTHING)
    battery = models.ForeignKey(
        Battery,
        help_text="Battery of Experiments deployed by the HIT.",
        verbose_name="Experiment Battery",
        null=False,
        blank=False,
        on_delete=DO_NOTHING)
    assignment = models.ForeignKey(
        Assignment,
        null=True,
        blank=True,
        related_name='assignment',
        on_delete=DO_NOTHING)
    finishtime = models.DateTimeField(null=True, blank=True, help_text=(
        "The date and time, in UTC, the Worker finished the result"))
    current_trial = models.PositiveIntegerField(null=True, blank=True, help_text=(
        "The last (current) trial recorded as complete represented in the results."))
    language = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="language of the browser associated with the result")
    browser = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="browser of the result")
    platform = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="platform of the result")
    completed = models.BooleanField(
        choices=(
            (False,
             'Not completed'),
            (True,
             'Completed')),
        default=False,
        verbose_name="participant completed the experiment")
    credit_granted = models.BooleanField(
        choices=(
            (False,
             'Not granted'),
            (True,
             'Granted')),
        default=False,
        verbose_name="the function assign_experiment_credit has been run to allocate credit for this result")

    class Meta:
        verbose_name = "Result"
        verbose_name_plural = "Results"
        unique_together = ("worker", "assignment", "battery", "experiment")

    def __repr__(self):
        return u"Result: id[%s],worker[%s],battery[%s],experiment[%s]" % (
            self.id, self.worker, self.battery, self.experiment)

    def __unicode__(self):
        return u"Result: id[%s],worker[%s],battery[%s],experiment[%s]" % (
            self.id, self.worker, self.battery, self.experiment)

    def get_taskdata(self):
        return to_dict(self.taskdata)


class Bonus(models.Model):
    '''A bonus object keeps track of a users bonuses for a battery'''
    worker = models.ForeignKey(
        Worker,
        null=False,
        blank=False,
        help_text="The ID of the Worker who is receiving bonus",
        on_delete=DO_NOTHING)
    battery = models.ForeignKey(
        Battery,
        help_text="Battery reciving bonuses for",
        verbose_name="Battery of experiments for bonus",
        null=False,
        blank=False,
        on_delete=DO_NOTHING)
    amounts = JSONField(
        null=True,
        blank=True,
        help_text="dictionary of experiments with bonus amounts",
        load_kwargs={
            'object_pairs_hook': collections.OrderedDict})
    # {u'test_task': {'description': u'performance_var True EQUALS True', 'experiment_id': 113, 'amount': 3.0} # amount in dollars/cents
    granted = models.BooleanField(
        choices=(
            (False,
             'Not bonused'),
            (True,
             'Bonus granted')),
        default=False,
        help_text="Participant bonus status",
        verbose_name="bonus status")

    def __unicode__(self):
        return "<%s_%s>" % (self.battery, self.worker)

    def calculate_bonus(self):
        if self.amounts is not None:
            amounts = dict(self.amounts)
            total = 0
            for experiment_id, record in amounts.items():
                if "amount" in record:
                    total = total + record["amount"]
            return total
        return 0

    class Meta:
        verbose_name = "Bonus"
        verbose_name_plural = "Bonuses"
        unique_together = ("worker", "battery")


class Blacklist(models.Model):
    '''A blacklist prevents a user from continuing a battery'''
    worker = models.ForeignKey(
        Worker,
        null=False,
        blank=False,
        help_text="The ID of the Worker who is or is pending blacklising",
        on_delete=DO_NOTHING)
    blacklist_time = models.DateTimeField(
        null=True, blank=True, help_text=("Time of blacklist"))
    battery = models.ForeignKey(
        Battery,
        help_text="Battery blacklisted from",
        verbose_name="Battery of experiments",
        null=False,
        blank=False,
        on_delete=DO_NOTHING)
    flags = JSONField(
        null=True,
        blank=True,
        help_text="dictionary of experiments with violations",
        load_kwargs={
            'object_pairs_hook': collections.OrderedDict})
    # {u'test_task': {'description': u'credit_var True EQUALS True', 'experiment_id': 113}
    active = models.BooleanField(
        choices=(
            (False,
             'Not Blacklisted'),
            (True,
             'Blacklisted')),
        default=False,
        help_text="Participant blacklist status",
        verbose_name="blacklist status")

    def __unicode__(self):
        return "<%s_%s>" % (self.battery, self.worker)

    class Meta:
        verbose_name = "Blacklist"
        verbose_name_plural = "Blacklists"
        unique_together = ("worker", "battery")
