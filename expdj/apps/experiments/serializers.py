from rest_framework import serializers

from expdj.apps.experiments.models import (
    Battery, CognitiveAtlasTask, ExperimentTemplate
)

class BatterySerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField()
    contributors = serializers.StringRelatedField(many=True)
    experiments = serializers.StringRelatedField(many=True)
    required_batteries = serializers.StringRelatedField(many=True)
    restricted_batteries = serializers.StringRelatedField(many=True)

    class Meta:
        model = Battery
        fields = [
            'name', 'description', 'credentials', 'consent', 'advertisement',
            'instructions', 'owner', 'contributors', 'experiments', 'add_date',
            'modify_date', 'maximum_time', 'number_of_experiments', 'active',
            'presentation_order', 'blacklist_active', 'blacklist_threshold',
            'bonus_active', 'required_batteries', 'restricted_batteries'
        ]

class BatteryDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Battery
        fields = ['name', 'description']

class CognitiveAtlasTaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CognitiveAtlasTask
        fields = ('name','cog_atlas_id')

class ExperimentTemplateSerializer(serializers.HyperlinkedModelSerializer):
    cognitive_atlas_task = CognitiveAtlasTaskSerializer()
    class Meta:
        model = ExperimentTemplate
        fields = [
            'exp_id','name','cognitive_atlas_task','reference','version',
            'template'
        ]
