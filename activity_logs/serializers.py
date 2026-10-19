from rest_framework import serializers

from .models import ActivityLog

LIST_FIELDS = [
    "id",
    "created_at",
    "action",
    "tenant",
    "user_type",
    "user_id",
    "user_name",
    "user_phone",
    "user_role",
    "ip_address",
    "method",
    "path",
    "os",
    "browser",
    "model",
    "object_id",
    "object_label",
    "description",
    "changed_fields",
]


class ActivityLogListSerializer(serializers.ModelSerializer):
    """A row of the list: everything but the old / new values (read on the detail)."""

    class Meta:
        model = ActivityLog
        fields = LIST_FIELDS


class ActivityLogDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = LIST_FIELDS + ["user_agent", "old_data", "new_data"]
