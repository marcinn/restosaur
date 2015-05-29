import functools
from .responses import UnauthorizedResponse


def login_required(func):
    @functools.wraps(func)
    def wrapped(request, *args, **kw):
        if not request.user.is_authenticated():
            return UnauthorizedResponse(request)
        return func(request, *args, **kw)
    return wrapped

