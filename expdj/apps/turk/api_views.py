from rest_framework import generics, permissions, viewsets

from expdj.apps.turk.models import Result, Worker
from expdj.apps.turk.serializers import ResultSerializer


class BatteryResultAPIList(generics.ListAPIView):
    serializer_class = ResultSerializer

    def get_queryset(self):
        battery_id = self.kwargs.get('bid')
        return Result.objects.filter(battery__id=battery_id)
