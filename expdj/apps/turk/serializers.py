from rest_framework import serializers

from expdj.apps.experiments.serializers import (
    BatteryDescriptionSerializer, ExperimentTemplateSerializer
)
from expdj.apps.experiments.models import Battery, ExperimentTemplate, CognitiveAtlasTask
from expdj.apps.turk.models import Result, Worker
from expdj.apps.turk.utils import to_dict

class BatterySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Battery
        fields = ('name', 'description')

class CognitiveAtlasTaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CognitiveAtlasTask
        fields = ('name','cog_atlas_id')

class ExperimentTemplateSerializer(serializers.HyperlinkedModelSerializer):
    cognitive_atlas_task = CognitiveAtlasTaskSerializer()
    class Meta:
        model = ExperimentTemplate
        fields = ('exp_id','name','cognitive_atlas_task','reference','version','template')

class WorkerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Worker
        fields = ["id"]

class ResultSerializer(serializers.HyperlinkedModelSerializer):
    experiment = ExperimentTemplateSerializer()
    battery = BatterySerializer()
    worker = WorkerSerializer()
    data = serializers.SerializerMethodField('get_taskdata')

    def get_taskdata(self,result):
        return to_dict(result.taskdata)

    class Meta:
        model = Result
        fields = ('data','experiment','battery','worker','language','browser','platform','completed','finishtime')

class WorkerResultsSerializer(serializers.HyperlinkedModelSerializer):
    results = ResultSerializer(many=True, read_only=True, source='result_worker')
    class Meta:
        model = Worker
        fields = ('id', 'results')
