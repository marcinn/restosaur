import functools
import logging
import mimeparse
import responses
import urltemplate
import urllib
import warnings
import sys
import types

from collections import OrderedDict
from django.http import HttpResponse
from django.conf import settings

from .serializers import default_serializers
from .headers import (
        normalize_header_name,
        parse_accept_header,
        build_content_type_header,
        )
from .context import Context
from .exceptions import Http404
from .loading import load_resource


log = logging.getLogger(__name__)


DEFAULT_REPRESENTATION_KEY = '__default__'


def http_response(response):
    """
    RESTResponse -> HTTPResponse factory
    """

    if isinstance(response, HttpResponse):
        return response

    context = response.context

    if response.data is not None:
        content_type = context.response_content_type
        serializer = context.serializer
        representation = context.representation_name
        content = serializer.dumps(response.serialize(response.data, representation))
    else:
        content = ''
        content_type = 'application/json'

    httpresp = HttpResponse(content, status=response.status)

    if content_type:
        httpresp['Content-Type'] = content_type

    for header, value in response.headers.items():
        httpresp[header]=value

    return httpresp


def resource_name_from_path(path):
    return urltemplate.remove_parameters(path).strip('/')


class Resource(object):
    def __init__(self, path, name=None, expose=False, serializers=None):
        self._path = path
        self._callbacks = {}
        self._expose = expose
        self._links = {}
        self._name = name or resource_name_from_path(path)
        self._representations = OrderedDict()
        self._serializers = serializers or default_serializers

        if expose:
            warnings.warn('`expose` argument will be removed in Restosaur 0.7'\
                    '\nUse `restosaur.contrib.apiroot` for exposing resources',
                    DeprecationWarning, stacklevel=3)
        if name:
            warnings.warn('`name` argument will be removed in Restosaur 0.7',
                    DeprecationWarning, stacklevel=3)

        # register aliases for the decorators
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'):
            setattr(self, verb.lower(), functools.partial(self._decorator, verb))

    def _decorator(self, method, link_to=None, link_as=None):
        def wrapper(view):
            if method in self._callbacks:
                raise ValueError('Already registered')
            self._callbacks[method] = view
            if link_to:
                if isinstance(link_to, types.StringTypes):
                    link_resource = load_resource(link_to)
                else:
                    link_resource = link_to
                key = link_as or link_resource.__name__
                link_resource._links[key] = (method, self)
            return view
        return wrapper

    @property
    def name(self):
        return self._name

    @property
    def expose(self):
        return self._expose

    @property
    def path(self):
        return self._path

    @property
    def serializers(self):
        return self._serializers

    @property
    def representations(self):
        return self._representations

    def __call__(self, ctx, *args, **kw):
        from django.http import Http404 as DjangoHttp404

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
                    ctx.body = self._serializers[mimetype].loads(ctx)
            elif not content_length:
                self.body = None
            else:
                return http_response(ctx.NotAcceptable())

        ctx.content_type = request.META.get('CONTENT_TYPE')

        # prepare request headers

        headers = request.META.items()
        http_headers = dict(map(lambda x: (normalize_header_name(x[0]),x[1]),
            filter(lambda x: x[0].startswith('HTTP_'), headers)))
        ctx.headers.update(http_headers)

        # match response representation, serializer and content type

        response_content_type = None
        response_serializer = None
        response_representation = None

        if 'accept' in ctx.headers:
            try:
                accepting = parse_accept_header(ctx.headers['accept'])
            except ValueError:
                content_type = None
            else:
                for content_type, representation, q in accepting:
                    if content_type == '*/*' or content_type == 'application/*':
                        content_type = 'application/json'
                        response_representation = DEFAULT_REPRESENTATION_KEY
                    if ctx.resource.serializers.contains(content_type)\
                            and (not representation or representation in ctx.resource.representations):
                        response_representation = representation or DEFAULT_REPRESENTATION_KEY
                        response_serializer = ctx.resource.serializers[content_type]
                        content_type = build_content_type_header(content_type, representation)
                        break

                if content_type and not response_serializer:
                    try:
                        response_serializer = ctx.resource.serializers[content_type]
                    except KeyError:
                        return http_response(ctx.NotAcceptable())

        else:
            content_type = 'application/json'
            response_serializer = ctx.resource.serializers[content_type]
            response_representation = DEFAULT_REPRESENTATION_KEY

        response_content_type = content_type

        if content_length and (not response_content_type or not response_serializer):
            return HttpResponse('Not acceptable `%s`' % ctx.headers.get('accept'),
                    status=406) # Not Acceptable

        ctx.representation_name = response_representation
        ctx.response_content_type = response_content_type
        ctx.serializer = response_serializer


        # support for X-HTTP-METHOD-OVERRIDE
        method = http_headers.get('x-http-method-override') or method

        log.debug('Calling %s, %s, %s' % (method, args, kw))
        if method in self._callbacks:
            try:
                try:
                    resp = self._callbacks[method](ctx, *args, **kw)
                except DjangoHttp404:
                    raise Http404
                else:
                    if not resp:
                        raise TypeError('Method `%s` does not return a response object' % self._callbacks[method])
                    if not response_representation and resp.data is not None:
                        return http_response(ctx.NotAcceptable())

                    return http_response(resp)
            except Http404:
                return http_response(ctx.NotFound())
            except Exception, ex:
                if settings.DEBUG:
                    tb = sys.exc_info()[2]
                else:
                    tb = None
                resp = responses.exception_response_factory(ctx, ex, tb)
                log.exception('Internal Server Error: %s', ctx.request.path,
                    exc_info=sys.exc_info(),
                    extra={
                        'status_code': resp.status,
                        'context': ctx,
                    }
                )
                return http_response(resp)
        else:
            return http_response(ctx.MethodNotAllowed({'error': 'Method `%s` is not registered for resource `%s`' % (
                method, self._path)}))

    def representation(self, name=DEFAULT_REPRESENTATION_KEY):
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

        if representation is None or representation==DEFAULT_REPRESENTATION_KEY:
            try:
                convert = self.representations[DEFAULT_REPRESENTATION_KEY]
            except KeyError:
                convert = lambda x, ctx: x  # pass through
        else:
            convert = self.representations[representation]
        return convert(obj, context)

