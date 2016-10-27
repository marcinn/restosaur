import functools
import logging
import sys
import urllib

from collections import OrderedDict, defaultdict

from .exceptions import Http404
from .headers import normalize_header_name
from .representations import (
        RepresentationAlreadyRegistered, ValidatorAlreadyRegistered,
        Representation, Validator)
from .utils import join_content_type_with_vnd, split_mediatype
from . import contentnegotiation, responses, urltemplate


log = logging.getLogger(__name__)


def _join_ct_vnd(content_type, vnd):
    return join_content_type_with_vnd(content_type, vnd)


def resource_name_from_path(path):
    return urltemplate.remove_parameters(path).strip('/')


class NoMoreMediaTypes(Exception):
    pass


class Resource(object):
    def __init__(
            self, api, path, name=None,
            default_content_type='application/json',
            link_model=None, link_name=None):
        self._api = api
        self._path = path
        self._required_parameters = urltemplate.get_parameters(self._path)
        self._callbacks = defaultdict(dict)
        self._registered_methods = set()
        self._name = name or resource_name_from_path(path)
        self._representations = OrderedDict()
        self._validators = OrderedDict()
        self._default_content_type = default_content_type

        self.add_representation(content_type=self._default_content_type)
        self.add_validator(content_type=self._default_content_type)

        if link_model:
            self._api.register_view(
                    model=link_model, resource=self, view_name=link_name)

        # register aliases for the decorators
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'):
            setattr(
                self, verb.lower(), functools.partial(self._decorator, verb))

    def _decorator(
            self, method, content_type=None, vnd=None):
        def wrapper(view):
            mt = _join_ct_vnd(content_type or self._default_content_type, vnd)
            if method in self._callbacks[mt]:
                raise ValueError('%s already registered for %s' % (method, mt))
            self._callbacks[mt][method] = view
            self._registered_methods.add(method)
            return view
        return wrapper

    def _match_media_type(self, accept, exclude=None):
        exclude = exclude or []

        def _drop_mt_args(x):
            return x.split(';')[0]

        mediatypes = list(filter(
                lambda x: _drop_mt_args(x) not in exclude, map(
                    lambda x: x.media_type(), self.representations)))

        if not mediatypes:
            raise NoMoreMediaTypes

        mediatype = contentnegotiation.best_match(mediatypes, accept)

        if not mediatype:
            raise NoMoreMediaTypes

        return _drop_mt_args(mediatype)

    def _match_representation(self, instance, ctx):
        accept = ctx.headers.get('accept') or '*/*'
        exclude = []
        model = type(instance)
        types = {}

        while True:
            try:
                mediatype = self._match_media_type(accept, exclude=exclude)
            except NoMoreMediaTypes:
                break

            try:
                types = self._representations[mediatype]
            except KeyError:
                exclude.append(mediatype)
            else:
                try:
                    return types[model]
                except KeyError:
                    exclude.append(mediatype)

        for mediatype in exclude:
            types = self._representations[mediatype]

            try:
                return types[None]
            except KeyError:
                pass

        raise KeyError(
            '%s has no registered representation handler for `%s`' % (
                model, accept))

    def _http_response(self, response):
        """
        RESTResponse -> HTTPResponse factory
        """

        from django.http import HttpResponse

        if isinstance(response, HttpResponse):
            return response

        context = response.context
        content_type = context.response_content_type
        content = ''

        if response.data is not None:
            representation = self._match_representation(response.data, context)
            content = representation.render(context, response.data)
            content_type = _join_ct_vnd(
                   representation.content_type, representation.vnd)

        httpresp = HttpResponse(content, status=response.status)

        if content_type:
            httpresp['Content-Type'] = content_type

        for header, value in response.headers.items():
            httpresp[header] = value

        return httpresp

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def representations(self):
        result = []
        for models in self._representations.values():
            result += models.values()
        return result

    def model(self, view_name=None):
        """
        Decorator for registering `self` (the resource)
        as a view for the model
        """
        def register_model(model_class):
            self._api.register_view(
                    model=model_class, resource=self, view_name=view_name)
            return model_class
        return register_model

    def _setup_response_ct_and_repr(self, ctx, accept):
        try:
            response_content_type = self._match_media_type(accept)
        except NoMoreMediaTypes:
            ctx.response_content_type = None
            ctx.response_representations = {}
        else:
            ctx.response_content_type = response_content_type
            ctx.response_representations = self._representations[
                    response_content_type]

    def __call__(self, ctx, *args, **kw):
        from django.http import Http404 as DjangoHttp404, HttpResponse

        method = ctx.method
        request = ctx.request

        # prepare request headers

        headers = request.META.items()
        http_headers = dict(map(
            lambda x: (normalize_header_name(x[0]), x[1]),
            filter(lambda x: x[0].startswith('HTTP_'), headers)))
        ctx.headers.update(http_headers)

        if ('CONTENT_TYPE' in request.META
                and request.META.get('CONTENT_LENGTH')):
            if self._validators:
                ctx.request_content_type = contentnegotiation.best_match(
                    self._validators.keys(), request.META['CONTENT_TYPE'])
            else:
                ctx.request_content_type = None
        else:
            ctx.request_content_type = self._default_content_type

        # match response representation, serializer and content type

        self._setup_response_ct_and_repr(
            ctx, ctx.headers.get('accept') or self._default_content_type)

        if method not in self._registered_methods:
            return self._http_response(ctx.MethodNotAllowed({
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
                self._setup_response_ct_and_repr(
                        ctx, self._default_content_type)
                return self._http_response(ctx.UnsupportedMediaType())

        ctx.content_type = request.META.get('CONTENT_TYPE')

        if content_length and not ctx.response_representations:
            self._setup_response_ct_and_repr(ctx, self._default_content_type)
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
                if not ctx.response_representations and resp.data is not None:
                    self._setup_response_ct_and_repr(
                            ctx, self._default_content_type)
                    return self._http_response(ctx.NotAcceptable())

                return self._http_response(resp)
        except Http404:
            return self._http_response(ctx.NotFound())
        except Exception as ex:
            if self._api.debug:
                tb = sys.exc_info()[2]
            else:
                tb = None
            ctx.response_content_type = self._default_content_type
            ctx.response_representations = {None: Representation(
                        content_type=ctx.response_content_type)}
            resp = responses.exception_response_factory(ctx, ex, tb)
            log.exception(
                    'Internal Server Error: %s', ctx.request.path,
                    exc_info=sys.exc_info(),
                    extra={
                        'status_code': resp.status,
                        'context': ctx,
                    }
            )
            return self._http_response(resp)

    def representation(self, model=None, media=None, serializer=None):
        def wrapped(func):
            if isinstance(media, (list, tuple)):
                content_types = map(split_mediatype, media)
            else:
                content_types = [split_mediatype(
                    media or self._default_content_type)]

            for ct, v, args in content_types:
                self.add_representation(
                    model=model, vnd=v, content_type=ct, qvalue=args.get('q'),
                    serializer=serializer, _transform_func=func)
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
            self, model=None, vnd=None, content_type=None, qvalue=None,
            serializer=None, _transform_func=None):

        content_type = content_type or self._default_content_type
        repr_key = _join_ct_vnd(content_type, vnd)

        if (repr_key in self._representations and
                not repr_key == self._default_content_type
                and model in self._representations[repr_key]):
            raise RepresentationAlreadyRegistered(
                    '%s: %s (%s)' % (self._path, repr_key, model))

        obj = Representation(
                vnd=vnd, content_type=content_type, serializer=serializer,
                _transform_func=_transform_func, qvalue=qvalue)

        self._representations.setdefault(repr_key, {})
        self._representations[repr_key][model] = obj
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
