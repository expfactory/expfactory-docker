from rest_framework import generics
from rest_framework import permissions
from rest_framework import viewsets

from expdj.apps.turk.models import Result
from expdj.apps.turk.serializers import ResultSerializer

class ResultAPIList(generics.ListAPIView):
    serializer_class = ResultSerializer

    def get_queryset(self):
        queryset = Result.objects.filter(battery__owner=self.request.user)
        return queryset

class BatteryResultAPIList(ResultAPIList):
    def get_queryset(self):
        queryset = super(BatteryResultAPIList, self).get_queryset()
        battery_id = self.kwargs.get('bid')
        return queryset.filter(battery__id=battery_id)
