import functools
import logging
import sys
import types
import urllib
import warnings
from collections import OrderedDict

import mimeparse
import responses
import urltemplate
from django.conf import settings
from django.http import HttpResponse

from .exceptions import Http404
from .headers import normalize_header_name
from .loading import load_resource
from .representations import RepresentationAlreadyRegistered, Representation


log = logging.getLogger(__name__)


def _join_ct_vnd(content_type, vnd):
    if not vnd:
        return content_type

    x, y = content_type.split('/')
    return '%s/%s+%s' % (x, vnd, y)


def http_response(response):
    """
    RESTResponse -> HTTPResponse factory
    """

    if isinstance(response, HttpResponse):
        return response

    context = response.context
    content_type = context.response_content_type
    content = ''

    if response.data is not None:
        representation = context.response_representation
        content = representation.render(context, response.data)

    httpresp = HttpResponse(content, status=response.status)

    if content_type:
        httpresp['Content-Type'] = content_type

    for header, value in response.headers.items():
        httpresp[header] = value

    return httpresp


def resource_name_from_path(path):
    return urltemplate.remove_parameters(path).strip('/')


class Resource(object):
    def __init__(
            self, path, name=None, expose=False,
            default_content_type='application/json'):
        self._path = path
        self._callbacks = {}
        self._expose = expose
        self._links = {}
        self._name = name or resource_name_from_path(path)
        self._representations = OrderedDict()
        self._default_content_type = default_content_type

        self.add_representation(content_type=self._default_content_type)

        if expose:
            warnings.warn(
                    '`expose` argument will be removed in Restosaur 0.7\n'
                    'Use `restosaur.contrib.apiroot` for exposing resources',
                    DeprecationWarning, stacklevel=3)
        if name:
            warnings.warn(
                    '`name` argument will be removed in Restosaur 0.7',
                    DeprecationWarning, stacklevel=3)

        # register aliases for the decorators
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'):
            setattr(
                self, verb.lower(), functools.partial(self._decorator, verb))

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
    def representations(self):
        return self._representations

    def __call__(self, ctx, *args, **kw):
        from django.http import Http404 as DjangoHttp404

        method = ctx.method
        request = ctx.request

        # prepare request headers

        headers = request.META.items()
        http_headers = dict(map(
            lambda x: (normalize_header_name(x[0]), x[1]),
            filter(lambda x: x[0].startswith('HTTP_'), headers)))
        ctx.headers.update(http_headers)

        # match response representation, serializer and content type

        def setup_response_ct_and_repr(ctx, accept):
            response_content_type = mimeparse.best_match(
                        self._representations.keys(), accept)
            response_representation = self._representations.get(
                    response_content_type)
            ctx.response_content_type = response_content_type
            ctx.response_representation = response_representation

        setup_response_ct_and_repr(
            ctx, ctx.headers.get('accept') or self._default_content_type)

        if method not in self._callbacks:
            return http_response(ctx.MethodNotAllowed({
                'error': 'Method `%s` is not registered for resource `%s`' % (
                    method, self._path)}))

        try:
            content_length = int(request.META['CONTENT_LENGTH'])
        except (KeyError, TypeError, ValueError):
            content_length = 0

        if content_length and 'CONTENT_TYPE' in request.META:
            mimetype = mimeparse.best_match(
                self._representations.keys(), request.META['CONTENT_TYPE'])
            if mimetype:
                ctx.representation = self._representations[mimetype]
                if request.body:
                    ctx.body = ctx.representation.parse(ctx)
            elif not content_length:
                self.body = None
            else:
                setup_response_ct_and_repr(ctx, self._default_content_type)
                return http_response(ctx.NotAcceptable())

        ctx.content_type = request.META.get('CONTENT_TYPE')

        if content_length and not ctx.response_representation:
            setup_response_ct_and_repr(ctx, self._default_content_type)
            return HttpResponse(
                    'Not acceptable `%s`' % ctx.headers.get('accept'),
                    status=406)

        # support for X-HTTP-METHOD-OVERRIDE
        method = http_headers.get('x-http-method-override') or method

        log.debug('Calling %s, %s, %s' % (method, args, kw))
        try:
            try:
                resp = self._callbacks[method](ctx, *args, **kw)
            except DjangoHttp404:
                raise Http404
            else:
                if not resp:
                    raise TypeError(
                            'Method `%s` does not return '
                            'a response object' % self._callbacks[method])
                if not ctx.response_representation and resp.data is not None:
                    setup_response_ct_and_repr(ctx, self._default_content_type)
                    return http_response(ctx.NotAcceptable())

                return http_response(resp)
        except Http404:
            return http_response(ctx.NotFound())
        except Exception as ex:
            if settings.DEBUG:
                tb = sys.exc_info()[2]
            else:
                tb = None
            resp = responses.exception_response_factory(ctx, ex, tb)
            log.exception(
                    'Internal Server Error: %s', ctx.request.path,
                    exc_info=sys.exc_info(),
                    extra={
                        'status_code': resp.status,
                        'context': ctx,
                    }
            )
            return http_response(resp)

    def representation(self, vnd=None, content_type=None, serializer=None):
        def wrapped(func):
            self.add_representation(
                    vnd=vnd, content_type=content_type, serializer=serializer,
                    _transform_func=func)
            return func
        return wrapped

    def add_representation(
            self, vnd=None, content_type=None, serializer=None,
            _transform_func=None):

        content_type = content_type or self._default_content_type
        repr_key = _join_ct_vnd(content_type, vnd)

        if (repr_key in self._representations and
                not repr_key == self._default_content_type):
            raise RepresentationAlreadyRegistered(
                    '%s: %s' % (self._path, repr_key))

        obj = Representation(
                vnd=vnd, content_type=content_type, serializer=serializer,
                _transform_func=_transform_func)

        self._representations[content_type] = obj
        return obj

    def uri(self, context, params=None, query=None):
        assert params is None or isinstance(
                params, dict), "entity.uri() params should be passed as dict"

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

