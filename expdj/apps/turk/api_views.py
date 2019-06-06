from django.http.response import HttpResponseForbidden
from rest_framework import exceptions, generics, permissions, viewsets

from expdj.apps.experiments.models import Battery
from expdj.apps.turk.models import Result, Worker
from expdj.apps.turk.serializers import ResultSerializer

class BatteryResultAPIList(generics.ListAPIView):
    serializer_class = ResultSerializer

    def get_queryset(self):

        battery_id = self.kwargs.get('bid')

        if (Battery.objects.get(pk=battery_id).owner_id is not self.request.user.pk):
            raise exceptions.PermissionDenied()
        queryset = Result.objects.filter(battery__id=battery_id).prefetch_related('experiment', 'battery', 'worker')
        return queryset

