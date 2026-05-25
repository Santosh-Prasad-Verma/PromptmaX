from rest_framework import serializers
from .models import PromptProject, PromptAsset, PromptVersion

class PromptProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptProject
        fields = ['id', 'name', 'description', 'user', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

class PromptVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptVersion
        fields = ['id', 'asset', 'version_number', 'content', 'commit_message', 'quality_score', 'history_reference', 'created_at']
        read_only_fields = ['id', 'asset', 'version_number', 'history_reference', 'created_at']

class PromptAssetSerializer(serializers.ModelSerializer):
    latest_version = serializers.SerializerMethodField()
    versions_count = serializers.SerializerMethodField()

    class Meta:
        model = PromptAsset
        fields = ['id', 'project', 'user', 'name', 'description', 'is_public', 'created_at', 'updated_at', 'latest_version', 'versions_count']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_latest_version(self, obj):
        latest = obj.versions.first()
        if latest:
            return PromptVersionSerializer(latest).data
        return None

    def get_versions_count(self, obj):
        return obj.versions.count()

class EnhanceRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(min_length=1, max_length=10000)
    enhancement_level = serializers.ChoiceField(
        choices=['basic', 'intermediate', 'advanced', 'expert'],
        default='intermediate',
    )
    mode = serializers.ChoiceField(
        choices=['enhance', 'generate'],
        default='enhance',
        help_text="'enhance' returns structured prompt template, 'generate' returns AI-generated response"
    )
    preferences = serializers.DictField(required=False, default=dict)
    model = serializers.CharField(required=False, default='auto')


class AnalyzeRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(min_length=1, max_length=10000)


class CompareRequestSerializer(serializers.Serializer):
    prompt_a = serializers.CharField(min_length=1, max_length=10000)
    prompt_b = serializers.CharField(min_length=1, max_length=10000)


class ABTestRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(min_length=1, max_length=10000)
    model = serializers.CharField(required=False, default='auto')


class AnalyzeURLRequestSerializer(serializers.Serializer):
    url = serializers.URLField()
    question = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class WebSearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1, max_length=2000)
    max_results = serializers.IntegerField(default=6, min_value=1, max_value=10)


class IdeasRequestSerializer(serializers.Serializer):
    count = serializers.IntegerField(default=5, min_value=1, max_value=10)


class FeedbackSerializer(serializers.Serializer):
    prompt_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class BatchEnhanceRequestSerializer(serializers.Serializer):
    prompts = serializers.ListField(
        child=serializers.CharField(min_length=1, max_length=10000),
        min_length=1, max_length=10,
    )
    enhancement_level = serializers.ChoiceField(
        choices=['basic', 'intermediate', 'advanced', 'expert'],
        default='intermediate',
    )

class ExecutePromptSerializer(serializers.Serializer):
    prompt_text = serializers.CharField(min_length=1, max_length=15000)
    model = serializers.ChoiceField(
        choices=['auto', 'nvidia_nemotron', 'nvidia_minimax', 'nvidia_gpt_oss'],
        default='auto'
    )
    max_tokens = serializers.IntegerField(default=1000, min_value=10, max_value=8000)
    temperature = serializers.FloatField(default=0.7, min_value=0.0, max_value=2.0)
