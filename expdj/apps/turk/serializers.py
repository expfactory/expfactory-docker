from rest_framework import serializers

from expdj.apps.experiments.serializers import (
    BatteryDescriptionSerializer, ExperimentTemplateSerializer
)
from expdj.apps.turk.models import Result
from expdj.apps.turk.utils import to_dict

#  class ResultSerializer(serializers.ModelSerializer):
class ResultSerializer(serializers.HyperlinkedModelSerializer):
    experiment = ExperimentTemplateSerializer()
    battery = BatteryDescriptionSerializer()
    worker = serializers.StringRelatedField()
    data = serializers.SerializerMethodField('get_taskdata')

    def get_taskdata(self, result):
        return to_dict(result.taskdata)

    class Meta:
        model = Result
        fields = [
            'data','experiment','battery','worker','language','browser',
            'platform','completed','finishtime'
        ]
