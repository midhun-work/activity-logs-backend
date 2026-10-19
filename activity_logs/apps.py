from django.apps import AppConfig


class ActivityLogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "activity_logs"
    # Kept as "logs" so the table is logs_activitylog and migrations stay under the app label "logs".
    label = "logs"
    verbose_name = "Activity logs"

    def ready(self):
        # Connects the create / update / delete recorders.
        from . import signals  # noqa: F401
