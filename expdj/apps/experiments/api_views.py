from rest_framework import generics
from rest_framework import permissions
from rest_framework import viewsets

from expdj.apps.experiments.models import Battery
from expdj.apps.experiments.serializers import BatterySerializer

class BatteryAPIList(generics.ListAPIView):
    serializer_class = BatterySerializer

    def get_queryset(self):
        queryset = Battery.objects.filter(owner=self.request.user)
        return queryset
