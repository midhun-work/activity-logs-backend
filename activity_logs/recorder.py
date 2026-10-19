"""Writing log rows. `log_event` is the public helper for things the model signals cannot see, such as
signing in with a token:

    from activity_logs.recorder import log_event
    log_event("login", "Signed in", user=user, request=request)
"""
import logging

from django.db import transaction

from . import conf
from .context import client_ip, current_request
from .models import ActivityLog
from .utils import device

logger = logging.getLogger(__name__)


def _user_info(user):
    """{"type", "id", "name", "phone", "role"} of `user`, from the project's USER_INFO hook if it has one."""
    if user is None:
        return {}
    hook = conf.hook("USER_INFO")
    if hook is not None:
        try:
            return hook(user) or {}
        except Exception:
            logger.exception("logs: USER_INFO hook failed")
    name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    return {
        "type": user._meta.label_lower,
        "id": getattr(user, "pk", ""),
        "name": name or getattr(user, "get_username", lambda: "")(),
        "phone": getattr(user, "phone_number", "") or "",
        "role": getattr(user, "role", "") or "",
    }


def _tenant():
    hook = conf.hook("TENANT")
    if hook is None:
        return ""
    try:
        return hook() or ""
    except Exception:
        logger.exception("logs: TENANT hook failed")
        return ""


def object_label(instance):
    """The project's readable name for `instance` (its OBJECT_LABEL hook), "" when it has none."""
    hook = conf.hook("OBJECT_LABEL")
    if hook is None:
        return ""
    try:
        return str(hook(instance) or "")
    except Exception:  # a record whose name cannot be read must not stop the log
        return ""


def build(action, *, user=None, request=None, description="", model="", object_id="", label="", old=None, new=None, changed=None):
    """The values of one log row, taken now (who, where, which tenant) while the request is still current."""
    request = request if request is not None else current_request()
    info = _user_info(user)
    meta = getattr(request, "META", None) or {}
    user_agent = str(meta.get("HTTP_USER_AGENT", ""))[:255]
    os_name, browser = device(user_agent)
    return {
        "action": action,
        "tenant": str(_tenant())[:100],
        "user_type": str(info.get("type", ""))[:30],
        "user_id": str(info.get("id", ""))[:64],
        "user_name": str(info.get("name", ""))[:150],
        "user_phone": str(info.get("phone", ""))[:30],
        "user_role": str(info.get("role", ""))[:50],
        "ip_address": client_ip(request),
        "method": (getattr(request, "method", "") or "")[:10],
        "path": (getattr(request, "path", "") or "")[:255],
        "user_agent": user_agent,
        "os": os_name[:50],
        "browser": browser[:50],
        "model": model[:100],
        "object_id": str(object_id)[:64],
        "object_label": str(label)[:100],
        "description": description[:255],
        "old_data": old,
        "new_data": new,
        "changed_fields": changed,
    }


def write(values):
    """Save one row. A failure is only reported: logging must never break the action being logged."""
    try:
        ActivityLog.objects.using(conf.get("DATABASE")).create(**values)
    except Exception:
        logger.exception("logs: could not write a log row")


def write_after_commit(values, using):
    """Save the row once the change it describes is committed (and never, if it is rolled back)."""
    try:
        transaction.on_commit(lambda: write(values), using=using)
    except Exception:
        logger.exception("logs: could not schedule a log row")


def log_event(action, description="", *, user=None, request=None, **fields):
    """Record something that is not a model save (sign-in, sign-out, an export, ...) straight away."""
    write(build(action, user=user, request=request, description=description, **fields))
