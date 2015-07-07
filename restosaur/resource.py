import functools
import logging
import mimeparse
import responses
import urltemplate
import urllib
from collections import OrderedDict

from .serializers import default_serializers
from .headers import normalize_header_name
from .context import Context


log = logging.getLogger(__name__)


def http_response(response):
    """
    RESTResponse -> HTTPResponse factory
    """

    from django.http import HttpResponse
    from .headers import parse_accept_header, build_content_type_header

    context = response.context

    content_type = None
    serializer = None
    representation = None

    if 'accept' in context.headers:
        accepting = parse_accept_header(context.headers['accept'])
        for content_type, representation, q in accepting:
            if content_type == '*/*' or content_type == 'application/*':
                content_type = 'application/json'
            if context.resource.serializers.contains(content_type)\
                and (not representation or representation in context.resource.representations):
                try:
                    representation = representation or context.resource.representations.keys()[0]
                except IndexError:
                    pass
                serializer = context.resource.serializers[content_type]
                content_type = build_content_type_header(content_type, representation)
                break
    else:
        content_type = 'application/json'

    if not content_type or not serializer:
        return HttpResponse(status=406) # Not Acceptable

    if response.data is not None:
        content = response.serialize(serializer, response.data, representation)
    else:
        content = ''

    httpresp = HttpResponse(content, status=response.status)
    httpresp['Content-Type'] = content_type
    return httpresp


class Resource(object):
    def __init__(self, path, serializers=None):
        self._path = path
        self._callbacks = {}
        self._representations = OrderedDict()
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

    def __call__(self, ctx, *args, **kw):
        method = ctx.method
        request = ctx.request

        try:
            content_length = int(request.META['CONTENT_LENGTH'])
        except (KeyError, TypeError, ValueError):
            content_length = 0

        if content_length and 'CONTENT_TYPE' in request.META:
            mimetype = mimeparse.best_match(dict(self._serializers.items()),
                    request.META['CONTENT_TYPE'])
            if mimetype:
                ctx.deserializer = self._serializers[mimetype]
                if request.body:
                    ctx.body = self._serializers[mimetype].loads(request.body)
            elif not content_length:
                self.body = None
            else:
                return http_response(ctx.NotAcceptable())

        ctx.content_type = request.META['CONTENT_TYPE']

        # prepare request headers

        headers = request.META.items()
        http_headers = dict(map(lambda x: (normalize_header_name(x[0]),x[1]),
            filter(lambda x: x[0].startswith('HTTP_'), headers)))
        ctx.headers.update(http_headers)

        log.debug('Calling %s, %s, %s' % (method, args, kw))
        if method in self._callbacks:
            resp = self._callbacks[method](ctx, *args, **kw)
            return http_response(resp)
        else:
            return http_response(ctx.MethodNotAllowed())

    def representation(self, name='default'):
        def wrapped(func):
            self._representations[name] = func
            return func
        return wrapped

    def uri(self, context, params=None, query=None):
        assert params is None or isinstance(params, dict), "entity.uri() params should be passed as dict"

        params = params or {}

        uri = context.build_absolute_uri(self._path)
        uri = urltemplate.to_url(uri, params)

        if query:
            uri += '?'+urllib.urlencode(query)

        return uri

    def convert(self, context, obj, representation=None):
        """
        Converts model (`obj`) using specified or default `representation`
        within a `context`
        """

        if representation is None:
            try:
                convert = self.representations.values()[0]
            except IndexError:
                convert = lambda x, ctx: x  # pass through
        else:
            convert = self.representations[representation]
        return convert(obj, context)

