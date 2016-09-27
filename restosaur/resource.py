import functools
import logging
import sys
import mimeparse
import responses
import urltemplate
import urllib

from collections import OrderedDict, defaultdict

from django.conf import settings
from django.http import HttpResponse

from .exceptions import Http404
from .headers import normalize_header_name
from .representations import (
        RepresentationAlreadyRegistered, ValidatorAlreadyRegistered,
        Representation, Validator)


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
            self, path, name=None, default_content_type='application/json'):
        self._path = path
        self._callbacks = defaultdict(dict)
        self._registered_methods = set()
        self._name = name or resource_name_from_path(path)
        self._representations = OrderedDict()
        self._validators = OrderedDict()
        self._default_content_type = default_content_type

        self.add_representation(content_type=self._default_content_type)
        self.add_validator(content_type=self._default_content_type)

        # register aliases for the decorators
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'):
            setattr(
                self, verb.lower(), functools.partial(self._decorator, verb))

    def _decorator(self, method, content_type=None, vnd=None):
        def wrapper(view):
            mt = _join_ct_vnd(content_type or self._default_content_type, vnd)
            if method in self._callbacks[mt]:
                raise ValueError('%s already registered for %s' % (method, mt))
            self._callbacks[mt][method] = view
            self._registered_methods.add(method)
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

        if 'CONTENT_TYPE' in request.META:
            if self._validators:
                ctx.request_content_type = mimeparse.best_match(
                    self._validators.keys(), request.META['CONTENT_TYPE'])
            else:
                ctx.request_content_type = None
        else:
            ctx.request_content_type = self._default_content_type

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

        if method not in self._registered_methods:
            return http_response(ctx.MethodNotAllowed({
                'error': 'Method `%s` is not registered for resource `%s`' % (
                    method, self._path)}))

        try:
            content_length = int(request.META['CONTENT_LENGTH'])
        except (KeyError, TypeError, ValueError):
            content_length = 0

        if content_length and 'CONTENT_TYPE' in request.META:
            if ctx.request_content_type:
                ctx.validator = self._validators[ctx.request_content_type]
                if request.body:
                    ctx.body = ctx.validator.parse(ctx)
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
                resp = self._callbacks[ctx.request_content_type][method](
                        ctx, *args, **kw)
            except DjangoHttp404:
                raise Http404
            else:
                if not resp:
                    raise TypeError(
                            'Method `%s` does not return '
                            'a response object' % self._callbacks[
                                ctx.request_content_type][method])
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
            ctx.response_content_type = self._default_content_type
            ctx.response_representation = Representation(
                    content_type=ctx.response_content_type)
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

    def validator(self, vnd=None, content_type=None, serializer=None):
        def wrapped(func):
            self.add_validator(
                    vnd=vnd, content_type=content_type, serializer=serializer,
                    _validator_func=func)
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

    def add_validator(
            self, vnd=None, content_type=None, serializer=None,
            _validator_func=None):

        content_type = content_type or self._default_content_type
        repr_key = _join_ct_vnd(content_type, vnd)

        if (repr_key in self._validators and
                not repr_key == self._default_content_type):
            raise ValidatorAlreadyRegistered(
                    '%s: %s' % (self._path, repr_key))

        obj = Validator(
                vnd=vnd, content_type=content_type, serializer=serializer,
                _validator_func=_validator_func)

        self._validators[content_type] = obj
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
