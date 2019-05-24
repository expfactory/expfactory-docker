from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.http.response import HttpResponseForbidden
from rest_framework import exceptions, generics, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

from expdj.apps.experiments.models import Battery
from expdj.apps.turk.models import Assignment, Result, Worker, HIT
from expdj.apps.turk.serializers import ResultSerializer
from expdj.apps.turk.tasks import updated_assign_experiment_credit
from expdj.apps.turk.utils import get_worker_experiments, get_connection, get_credentials

class BatteryResultAPIList(generics.ListAPIView):
    serializer_class = ResultSerializer

    def get_queryset(self):
        battery_id = self.kwargs.get('bid')
        if (Battery.objects.get(pk=battery_id).owner is not self.request.user.pk):
            raise exceptions.PermissionDenied()
        return Result.objects.filter(battery__id=battery_id)

class WorkerExperiments(APIView):
    permission_classes = (AllowAny,)
    def get(self, request, worker_id, hit_id):
        try:
            hit = HIT.objects.get(mturk_id=hit_id)
            worker = Worker.objects.get(id=worker_id)
            # assignment = Assignment.objects.get(hit__mturk_id=hit_id)
            all_assignments = Assignment.objects.filter(worker_id=worker_id, hit__battery_id=hit.battery_id)
        except ObjectDoesNotExist:
            raise Http404
        exps = list(get_worker_experiments(worker, hit.battery))
        exps = [x.template.name for x in exps]
        submit = False
        status = 'Not Submitted'

        marked_complete = all_assignments.filter(completed=True).count() > 0

        if len(exps) ==  0 and not marked_complete:
            all_assignments.filter(completed=False).update(completed=True)
            submit = True
            updated_assign_experiment_credit.apply_async([worker_id, hit.battery_id], countdown=60)
        elif len(exps) == 0 and marked_complete:
            status = 'Submit Attempted'

        return Response({'experiments': exps, 'assignment_status': status, 'submit': submit})
