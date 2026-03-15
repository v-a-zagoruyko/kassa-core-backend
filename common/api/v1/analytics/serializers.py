"""Сериализаторы аналитического API."""

from rest_framework import serializers

from analytics.models import Dashboard, Metric, Report


class MetricSerializer(serializers.ModelSerializer):
    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)

    class Meta:
        model = Metric
        fields = ('id', 'metric_type', 'metric_type_display', 'store', 'date', 'value', 'metadata')


class ReportSerializer(serializers.ModelSerializer):
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)

    class Meta:
        model = Report
        fields = (
            'id', 'report_type', 'report_type_display',
            'store', 'date_from', 'date_to', 'format', 'format_display',
            'data', 'created_by', 'created_at',
        )
        read_only_fields = ('id', 'data', 'created_by', 'created_at')


class GenerateReportSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=Report.ReportType.choices)
    store_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    format = serializers.ChoiceField(choices=Report.Format.choices, default=Report.Format.JSON)

    def validate(self, attrs):
        if attrs['date_from'] > attrs['date_to']:
            raise serializers.ValidationError('date_from не может быть позже date_to.')
        return attrs


class DashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ('id', 'name', 'config', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class CreateDashboardSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    config = serializers.JSONField(default=dict)
    is_active = serializers.BooleanField(default=True)
