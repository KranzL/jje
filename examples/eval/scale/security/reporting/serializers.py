from rest_framework import serializers

from .columns import FILTERABLE_COLUMNS


class ReportQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=120)
    sort = serializers.CharField(required=False, allow_blank=True, max_length=64)
    direction = serializers.ChoiceField(
        choices=("asc", "desc"), required=False, default="asc"
    )
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(
        required=False, min_value=1, max_value=200, default=50
    )

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        filters = {}
        for key in FILTERABLE_COLUMNS:
            if key in data:
                filters[key] = data.get(key)
        validated["filters"] = filters
        return validated


class ReportRowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    region = serializers.CharField()
    owner = serializers.EmailField()
    amount_cents = serializers.IntegerField()
    created_at = serializers.DateTimeField()
