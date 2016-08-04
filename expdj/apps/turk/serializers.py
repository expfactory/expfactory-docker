from rest_framework import serializers

from expdj.apps.experiments.serializers import (
    BatteryDescriptionSerializer, ExperimentTemplateSerializer
)
from expdj.apps.turk.models import Result, Worker
from expdj.apps.turk.utils import to_dict

class ResultSerializer(serializers.HyperlinkedModelSerializer):
    experiment = ExperimentTemplateSerializer()
    data = serializers.SerializerMethodField('get_taskdata')

    def get_taskdata(self, result):
        return to_dict(result.taskdata)

    class Meta:
        model = Result
        fields = [
            'data', 'experiment', 'language', 'browser',
            'platform', 'completed', 'finishtime'
        ]

class WorkerResultsSerializer(serializers.HyperlinkedModelSerializer):
    results = ResultSerializer(many=True, read_only=True, source='result_worker')
    class Meta:
        model = Worker
        fields = ('id', 'results')
