from .context import reset_request, set_request


class RequestContextMiddleware:
    """Remembers the current request for the log recorders. Put it after the authentication (and any
    tenant) middleware in MIDDLEWARE."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_request(request)
        try:
            return self.get_response(request)
        finally:
            reset_request(token)
