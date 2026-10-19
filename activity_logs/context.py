"""The request being served, so the model signals know who made a change and from where.

A context variable (not a thread-local): it is reset after every request, so one request's user can
never leak into the next one served by the same worker.
"""
import contextvars

_request = contextvars.ContextVar("logs_current_request", default=None)


def set_request(request):
    return _request.set(request)


def reset_request(token):
    _request.reset(token)


def current_request():
    return _request.get()


def current_user():
    """The signed-in user of the current request, or None (scripts, cron, anonymous calls)."""
    request = current_request()
    user = getattr(request, "user", None) if request is not None else None
    return user if user is not None and getattr(user, "is_authenticated", False) else None


def client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None
