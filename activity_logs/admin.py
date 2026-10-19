from django.contrib import admin

from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Read only: a log is evidence, so it is never added, changed or removed by hand."""

    list_display = ("created_at", "action", "tenant", "user_name", "user_phone", "model", "object_id", "ip_address")
    list_filter = ("action", "tenant", "user_type")
    search_fields = ("user_name", "user_phone", "description", "object_id")
    date_hierarchy = "created_at"

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
