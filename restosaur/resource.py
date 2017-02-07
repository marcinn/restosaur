import functools
import logging
import sys
import urllib

from collections import OrderedDict, defaultdict

from .exceptions import Http404
from .representations import (
        RepresentationAlreadyRegistered, ValidatorAlreadyRegistered,
        Representation, Validator)
from .utils import join_content_type_with_vnd, split_mediatype
from . import contentnegotiation, responses, urltemplate, serializers


log = logging.getLogger(__name__)


def _join_ct_vnd(content_type, vnd):
    return join_content_type_with_vnd(content_type, vnd)


def dict_as_text(obj, ctx, depth=0):
    output = u''

    for key, value in obj.items():
        if isinstance(value, dict):
            value = u'\n'+dict_as_text(value, ctx, depth+1)
        output += u'%s%s: %s\n' % (' '*depth*2, key, value)

    return output


def resource_name_from_path(path):
    return urltemplate.remove_parameters(path).strip('/')


class NoMoreMediaTypes(Exception):
    pass


class NoRepresentationFound(Exception):
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
        self._supported_media_types = defaultdict(set)

        # register "pass-through" validators

        for content_type, serializer in serializers.get_all():
            self.add_validator(content_type=content_type)

        if link_model:
            self._api.register_view(
                    model=link_model, resource=self, view_name=link_name)

        # register aliases for the decorators
        for verb in ('GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'):
            setattr(
                self, verb.lower(), functools.partial(self._decorator, verb))

    def is_callback_registered(self, method, content_type=None):
        content_type = content_type or self._default_content_type
        return method in self._callbacks[content_type]

    def register_method_callback(self, callback, method, content_type=None):
        content_type = content_type or self._default_content_type
        self._callbacks[content_type][method] = callback
        self._registered_methods.add(method)
        self._supported_media_types[method].add(content_type)

    def get_method_supported_mediatypes(self, method):
        return list(self._supported_media_types[method])

    def get_callback(self, method, content_type=None):
        content_type = content_type or self._default_content_type
        return self._callbacks[content_type][method]

    def get_allowed_methods(self):
        return list(self._registered_methods)

    @property
    def default_content_type(self):
        return self._default_content_type

    def _decorator(self, method, accept=None):
        def wrapper(view):
            if self.is_callback_registered(method, content_type=accept):
                raise ValueError(
                        'Method `%s` is already registered' % method)
            self.register_method_callback(
                    view, method=method, content_type=accept)
            return view
        return wrapper

    def _match_media_type(self, accept, representations, exclude=None):
        exclude = exclude or []

        def _drop_mt_args(x):
            return x.split(';')[0]

        mediatypes = list(filter(
                lambda x: _drop_mt_args(x) not in exclude, map(
                    lambda x: x.media_type(), representations)))

        if not mediatypes:
            raise NoMoreMediaTypes

        mediatype = contentnegotiation.best_match(mediatypes, accept)

        if not mediatype:
            raise NoMoreMediaTypes

        return _drop_mt_args(mediatype)

    def _match_representation(self, instance, ctx, accept=None):

        # Use "*/*" as default -- RFC 7231 (Section 5.3.2)
        accept = accept or ctx.headers.get('accept') or '*/*'

        exclude = []
        model = type(instance)

        representations = self.representations

        while True:
            try:
                mediatype = self._match_media_type(
                        accept, representations, exclude=exclude)
            except NoMoreMediaTypes:
                break

            if not self.has_representation_for(model, mediatype):
                exclude.append(mediatype)
            else:
                return self.get_representation(model, mediatype)

        for mediatype in exclude:
            if self.has_representation_for(None, mediatype):
                return self.get_representation(None, mediatype)

        raise NoRepresentationFound(
            '%s has no registered representation handler for `%s`' % (
                model, accept))

    def _http_response(self, response):
        content = ''
        content_type = self._default_content_type

        if response.data is not None:
            try:
                representation = self._match_representation(
                        response.data, response.context)
            except NoRepresentationFound:
                if isinstance(response, responses.SuccessfulResponse):
                    return self._http_response(
                        responses.NotAcceptableResponse(
                            response.context, headers=response.headers))
                elif isinstance(response, (
                        responses.ServerErrorResponse,
                        responses.ClientErrorResponse)):
                    # For errors use any representation supported by
                    # server. It is better to provide any information
                    # in any format instead of nothing.
                    # -- RFC7231 (Section 6.5 & 6.6)
                    #
                    # Restosaur will try to match most acceptible
                    # representation.

                    accept = response.context.headers.get('accept')
                    accepting = ['*/*;q=0.1']

                    if accept:
                        media_type, media_subtype = accept.split('/')
                        accepting.insert(0, '%s/*;q=1' % media_type)

                    try:
                        representation = self._match_representation(
                                response.data, response.context,
                                accept=','.join(accepting))
                    except NoRepresentationFound:
                        # return no content and preserve status code
                        pass
                    else:
                        content = representation.render(
                                response.context, response.data)
                        content_type = _join_ct_vnd(
                               representation.content_type, representation.vnd)
                else:
                    # return no content and preserve status code
                    pass
            else:
                content = representation.render(
                        response.context, response.data)
                content_type = _join_ct_vnd(
                       representation.content_type, representation.vnd)

        return (response, content, content_type)

    @property
    def name(self):
        return self._name

    @property
    def api(self):
        return self._api

    @property
    def path(self):
        return self._path

    @property
    def representations(self):
        result = []
        for models in self._representations.values():
            result += models.values()
        return result + self._api.representations

    def has_representation_for(self, model, media_type):
        return (media_type in self._representations
                and model in self._representations[media_type]) or (
                        self._api.has_representation_for(model, media_type))

    def get_representation(self, model, media_type):
        try:
            return self._representations[media_type][model]
        except KeyError:
            return self._api.get_representation(model, media_type)

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

    def __call__(self, ctx, *args, **kw):
        from django.http import Http404 as DjangoHttp404

        method = ctx.method
        request = ctx.request

        # support for X-HTTP-METHOD-OVERRIDE

        method = ctx.headers.get('x-http-method-override') or method

        # Check request method and raise MethodNotAllowed if unsupported

        allowed_methods = self.get_allowed_methods()

        if method not in allowed_methods:
            headers = {
                    'Allow': ', '.join(allowed_methods),
                }
            return self._http_response(ctx.MethodNotAllowed({
                'error': 'Method `%s` is not registered for resource `%s`' % (
                    method, self._path)}, headers=headers))

        # Negotiate payload content type and store the best matching
        # result in ctx.request_content_type

        if ctx.content_type and ctx.content_length:
            media_types = self.get_method_supported_mediatypes(method)
            if media_types:
                ctx.request_content_type = contentnegotiation.best_match(
                        media_types, ctx.content_type)
            else:
                # server does not support any representation
                ctx.request_content_type = None
        elif ctx.content_length:
            # No payload content-type was provided.
            # According to RFC7231 (Section 3.1.1.5) server may assume
            # "application/octet-stream" or try to examine the type.

            ctx.request_content_type = 'application/octet-stream'
        else:
            # No payload
            ctx.request_content_type = None

        # match response representation, serializer and content type

        if ctx.content_length and ctx.content_type:
            if ctx.request_content_type:
                if request.body:
                    try:
                        ctx.validator = self._validators[
                                    ctx.request_content_type]
                    except KeyError:
                        pass
                    else:
                        try:
                            ctx.body = ctx.validator.parse(ctx)
                        except serializers.DeserializationError as ex:
                            resp = responses.exception_response_factory(
                                    ctx, ex, cls=responses.BadRequestResponse)
                            return self._http_response(resp)
            elif not ctx.content_length:
                ctx.body = None
            else:
                return self._http_response(ctx.UnsupportedMediaType())

        log.debug('Calling %s, %s, %s' % (method, args, kw))

        try:
            callback = self.get_callback(method, ctx.request_content_type)

            try:
                resp = callback(ctx, *args, **kw)
            except DjangoHttp404:
                raise Http404
            else:
                if not resp:
                    raise TypeError(
                            'Function `%s` does not return '
                            'a response object' % callback)
                return self._http_response(resp)
        except Http404:
            return self._http_response(ctx.NotFound())
        except Exception as ex:
            if self._api.debug:
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
            return self._http_response(resp)

    def accept(self, media_type=None):
        media_type = media_type or self._default_content_type
        ct, vnd = split_mediatype(media_type)
        return self.validator(content_type=ct, vnd=vnd)

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
