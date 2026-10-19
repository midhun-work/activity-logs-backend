from django.db import models
from django.utils import timezone


class ActivityLog(models.Model):
    """One thing someone did: created, changed or deleted a record, or signed in / out.

    Who did it is copied in as plain values rather than linked, so the log works with any user model
    (or several, in different databases) and stays readable after the user is gone.
    """

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        OTHER = "other", "Other"

    created_at = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=16, choices=Action.choices, default=Action.OTHER)
    # The tenant / shop the request was for ("" when there is none).
    tenant = models.CharField(max_length=100, blank=True, default="")

    user_type = models.CharField(max_length=30, blank=True, default="")
    user_id = models.CharField(max_length=64, blank=True, default="")
    user_name = models.CharField(max_length=150, blank=True, default="")
    user_phone = models.CharField(max_length=30, blank=True, default="")
    user_role = models.CharField(max_length=50, blank=True, default="")

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    method = models.CharField(max_length=10, blank=True, default="")
    path = models.CharField(max_length=255, blank=True, default="")
    # The device the request came from: the browser's own description, and the system / browser read from it.
    user_agent = models.CharField(max_length=255, blank=True, default="")
    os = models.CharField(max_length=50, blank=True, default="")
    browser = models.CharField(max_length=50, blank=True, default="")

    # "app_label.ModelName" and the record's primary key, for record changes.
    model = models.CharField(max_length=100, blank=True, default="")
    object_id = models.CharField(max_length=64, blank=True, default="")
    # A readable name for the record taken when it was logged (e.g. a customer's phone), "" when the project gives none.
    object_label = models.CharField(max_length=100, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    # A create keeps the new values, a delete the old ones, an update only the fields that changed.
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    changed_fields = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Activity log"
        verbose_name_plural = "Activity logs"
        indexes = [
            models.Index(fields=["created_at", "id"], name="log_created_idx"),
            models.Index(fields=["tenant", "created_at"], name="log_tenant_created_idx"),
            models.Index(fields=["action", "created_at"], name="log_action_created_idx"),
            models.Index(fields=["model", "created_at"], name="log_model_created_idx"),
            models.Index(fields=["user_phone"], name="log_user_phone_idx"),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.model or ''} {self.user_name or self.user_phone}"
