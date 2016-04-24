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

from .headers import (
        normalize_header_name,
        parse_accept_header,
        build_content_type_header,
        )
from .context import Context
from .exceptions import Http404
from .loading import load_resource


log = logging.getLogger(__name__)


def _content_type_serializer(content_type):
    maintype,subtype=content_type.split('/')

    try:
        vnd,subtype=subtype.split('+')
    except ValueError:
        pass
    finally:
        serializer = '%s/%s' % (maintype, subtype)

    return serializer


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
    def __init__(self,
            api, path, serializers=None,
            default_representation=None, scope=None):

        self._api = api
        self._scope = self
        self._path = path
        self._callbacks = {}
        self._representations = OrderedDict()
        self._serializers = serializers or self._api.serializers

        self._default_representation = default_representation\
                or self._api.default_representation

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
    def path(self):
        return self._path

    @property
    def serializers(self):
        return self._serializers

    @property
    def representations(self):
        return self._api.representations[self._scope]

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
                for serializer, vnd, q in accepting:
                    maintype,subtype = serializer.split('/')
                    content_type = '%s/%s+%s' % (maintype, vnd, subtype)
                    if content_type == '*/*':
                        content_type = self._default_representation
                    elif content_type.split('/')[1]=='*':
                        raise NotImplementedError
                    if 'content_type' in ctx.resource.representations\
                            and serializer in ctx.resource.serializers:
                        response_representation = content_type
                        response_serializer = ctx.resource.serializers[serializer]
                        content_type = build_content_type_header(content_type, representation)
                        break

                if content_type and not response_serializer:
                    serializer = _content_type_serializer(content_type)
                    try:
                        response_serializer = ctx.resource.serializers[serializer]
                    except KeyError:
                        return http_response(ctx.NotAcceptable())

        else:
            content_type = self._default_representation
            serializer = _content_type_serializer(content_type)
            response_serializer = ctx.resource.serializers[serializer]
            response_representation = content_type

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

    def representation(self, content_type=None):
        """
        Create and register representation
        """

        if content_type:
            try:
                maintype,subtype=content_type.split('/')
            except ValueError:
                maintype,subtype=self._api.default_content_type.split('/')
                try:
                    vnd, subtype = subtype.split('+')
                except ValueError:
                    pass
                content_type='%s/%s+%s' % (maintype, content_type, subtype)

                warnings.warn(
                    'Restosaur v1.0 will require proper valid content_type '\
                    'declaration when registering `resource.representation()`. '\
                    'Please modify your code by setting `%s` here.' % content_type,
                        DeprecationWarning, stacklevel=2)

        return self._api.representation_for(
                self._scope, content_type=content_type)

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

        representation = representation or self._default_representation

        try:
            representation_obj = self.representations[representation]
        except KeyError:
            convert = lambda x, ctx: x  # pass through
        else:
            convert = representation_obj.read
        return convert(obj, context)

