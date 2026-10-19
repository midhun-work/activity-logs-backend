"""The app's settings: everything a project sets lives in one `LOGS = {...}` dict in its settings.

    LOGS = {
        # Database alias the log table lives in.
        "DATABASE": "default",
        # Never logged: whole apps (app labels) and single models ("app_label.ModelName").
        "SKIP_APPS": [...],
        "SKIP_MODELS": [...],
        # Field names whose values are replaced by "***" (exact names, any model).
        "MASK_FIELDS": [...],
        # Dotted path to callable(user) -> {"type", "id", "name", "phone", "role"}; the default reads
        # common attributes (first_name, last_name, phone_number, role) off the user.
        "USER_INFO": "myproject.logging.user_info",
        # Dotted path to callable() -> str: the tenant / shop of the current request ("" for none).
        "TENANT": "myproject.logging.current_tenant",
        # Dotted path to callable(instance) -> str: a readable name for a changed record (e.g. a phone
        # number), shown beside its id. Return "" for models that have none.
        "OBJECT_LABEL": "myproject.logging.object_label",
        # Who may read the logs API (dotted DRF permission classes).
        "PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
        "PAGE_SIZE": 25,
        "MAX_PAGE_SIZE": 100,
    }

Anything left out falls back to the defaults below.
"""
from functools import lru_cache

from django.conf import settings
from django.utils.module_loading import import_string

DEFAULTS = {
    "DATABASE": "default",
    # Framework bookkeeping, and the log table itself (logging it would loop).
    "SKIP_APPS": ["logs", "sessions", "contenttypes", "admin", "migrations"],
    "SKIP_MODELS": ["auth.Permission"],
    "MASK_FIELDS": [
        "password",
        "mpin",
        "otp",
        "token",
        "access",
        "refresh",
        "secret",
        "account_number",
        "bank_account_number",
    ],
    "USER_INFO": None,
    "TENANT": None,
    "OBJECT_LABEL": None,
    "PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
    "PAGE_SIZE": 25,
    "MAX_PAGE_SIZE": 100,
}


def get(name):
    return getattr(settings, "LOGS", {}).get(name, DEFAULTS[name])


@lru_cache(maxsize=None)
def skip_apps():
    return {label.lower() for label in get("SKIP_APPS")}


@lru_cache(maxsize=None)
def skip_models():
    return {label.lower() for label in get("SKIP_MODELS")}


@lru_cache(maxsize=None)
def mask_fields():
    return {name.lower() for name in get("MASK_FIELDS")}


@lru_cache(maxsize=None)
def hook(name):
    """The project's callable for USER_INFO / TENANT / OBJECT_LABEL, or None."""
    path = get(name)
    return import_string(path) if path else None


def permission_classes():
    return [import_string(path) for path in get("PERMISSION_CLASSES")]
