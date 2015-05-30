import functools
import logging
import mimeparse
import responses
import urltemplate
from .serializers import default_serializers
from .headers import normalize_header_name
from .context import Context


log = logging.getLogger(__name__)


class Resource(object):
    def __init__(self, path, serializers=None):
        self._path = path
        self._callbacks = {}
        self._representations = {}
        self._serializers = serializers or default_serializers
        # register aliases for the decorators
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'):
            setattr(self, verb.lower(), functools.partial(self._decorator, verb))

    def _decorator(self, method):
        def wrapper(view):
            if method in self._callbacks:
                raise ValueError('Already registered')
            self._callbacks[method] = view
            return view
        return wrapper

    @property
    def serializers(self):
        return self._serializers

    @property
    def representations(self):
        return self._representations

    def __call__(self, request, *args, **kw):
        method = request.method
        ctx = Context(request=request, resource=self)

        if request.META.get('CONTENT_LENGTH') and 'CONTENT_TYPE' in request.META:
            mimetype = mimeparse.best_match(dict(self._serializers.items()),
                    request.META['CONTENT_TYPE'])
            if mimetype:
                ctx.deserializer = self._serializers[mimetype]
                if request.body:
                    ctx.body = self._serializers[mimetype].loads(request.body)
            else:
                return ctx.NotAcceptable()

        ctx.content_type = request.META['CONTENT_TYPE']

        # prepare request headers

        headers = request.META.items()
        http_headers = dict(map(lambda x: (normalize_header_name(x[0]),x[1]),
            filter(lambda x: x[0].startswith('HTTP_'), headers)))
        ctx.headers.update(http_headers)

        log.debug('Calling %s, %s, %s' % (method, args, kw))
        if method in self._callbacks:
            resp = self._callbacks[method](ctx, *args, **kw)
            return resp
        else:
            return ctx.MethodNotAllowed()

    def representation(self, name='default'):
        def wrapped(func):
            self._representations[name] = func
            return func
        return wrapped

    def uri(self, context, params=None, query=None):
        assert params is None or isinstance(params, dict), "entity.uri() params should be passed as dict"

        params = params or {}
        uri = context.build_absolute_uri(self._path)

        return urltemplate.to_url(uri, params)

