import collections
import email
import functools
import six

try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import times
# todo: implement own conversion utility
from django.utils.encoding import force_bytes

from .loading import load_resource
from . import responses


def parse_http_date(header, headers):
    if header in headers and headers[header]:
        timetuple = email.utils.parsedate_tz(headers[header])
        try:
            return times.from_unix(email.utils.mktime_tz(timetuple))
        except (TypeError, ValueError):
            pass


class QueryDict(collections.MutableMapping):
    """
    QueryDict acts like a plain `dict` type, but it handles
    automatially multiple values for same key.

    The most safest representation of URI query parameters is a list
    of tuples, because the parameter names aren't unique. Unfortunately
    accessing list of tuples is not so handy, so a mapping is
    required.

    In most cases query parameters looks like a mapping of simple
    key => value pairs, so we're expecting just one value per key. But when
    value is a list, we're expecting that accessing a key will return that
    list, not last nor first value.

    The problematic case is for keys, for which we're expecting always a list
    of values, but just one was passed in URI. Accessing the key will give
    just straight value instead of expected list with one item. In that cases
    you should use `QueryDict.getlist()` directly, which returns always a list.

    The values are stored internally as lists.

    `.items()` method returns a list of (key, value) tuples, where value is
    a single value from a key's values list. This means that key may not be
    unique. This representation is compatible with `urllib.urlencode()`.

    `.keys()` returns unique key names, same as for pure `dict`.

    `.values()` returns list of same values, which can be accessed by key,

    `.lists()` returns internal representation as list of lists.
    """

    def __init__(self, initial=None):
        self._data = {}
        self.update(initial)

    def update(self, data):
        if data is None:
            return
        else:
            try:
                data = data.items()
            except AttributeError:
                pass
        keys = set([x[0] for x in data])
        for key in keys:
            self._data[key] = []
        for key, value in data:
            if isinstance(value, (list, tuple)):
                for x in value:
                    self._data[key].append(x)
            else:
                self._data[key].append(value)

    def items(self):
        result = []
        for key, values in self._data.items():
            result += list(map(lambda x: (key, x), values))
        return result

    def getlist(self, key, default=None):
        return self._data.get(key, default)

    def lists(self):
        return self._data.items()

    def __setitem__(self, key, value):
        return self.update({key: value})

    def __getitem__(self, key):
        return self._data[key][-1]\
                if len(self._data[key]) < 2 else self._data[key]

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return repr(self._data)


class Context(object):
    def __init__(
            self, api, host='localhost', path='/', method='GET',
            parameters=None, body=None, data=None, files=None, raw=None,
            extra=None, headers=None, charset=None, secure=False,
            encoding='utf-8', resource=None, request=None, content_length=None,
            content_type=None):
        self.method = method
        self.api = api
        self.charset = charset
        self.headers = headers or {}
        self.resource = resource
        self.request = request
        self.encoding = encoding
        self.secure = secure
        self.host = host
        self.path = path
        self.body = body
        self.raw = raw
        self.parameters = QueryDict(parameters)  # GET
        self.data = data or {}  # POST
        self.files = files or {}  # FILES
        self.deserializer = None
        self.content_type = content_type
        self.content_length = content_length
        self.extra = extra or {}

    def build_absolute_uri(self, path=None, parameters=None):
        """
        Returns absolute uri to the specified `path` with optional
        query string `parameters`.

        If no `path` is provided, the current request full path
        (including query string) will be used and extended by
        optional `parameters`.
        """

        def build_uri(path):
            current = 'http%s://%s%s' % (
                    's' if self.secure else '', self.host, self.path)
            return urlparse.urljoin(current, path)

        params = QueryDict()
        if path:
            full_path = u'/'.join(
                    filter(None, (self.api.path+path).split('/')))
            if path.endswith('/'):
                full_path += '/'
            uri = build_uri('/'+full_path)
        else:
            params.update(self.parameters.items())
            uri = build_uri(self.path)

        # todo: change to internal restosaur settings
        enc = self.encoding

        params.update(parameters or {})
        params = list(map(
                lambda x: (x[0], force_bytes(x[1], enc)),
                params.items()))

        if params:
            return '%s?%s' % (uri, urlencode(params))
        else:
            return uri

    def url_for(self, resource, **kwargs):
        """
        Shortcut wrapper of `resource.uri()`
        """
        if isinstance(resource, six.string_types):
            resource = load_resource(resource)
        return resource.uri(self, params=kwargs)

    def link_model(self, model_instance, view_name=None, query=None):
        resource = self.api.resource_for_viewmodel(
                type(model_instance), view_name)
        return self.link(
                resource, model=model_instance, query=query)

    def link(self, resource, model=None, query=None):
        """
        Generate URL for `model` instance based on `resource`
        path template.

        Handy shortcut for `resource.uri()`
        """

        if not resource._required_parameters or not model:
            return resource.uri(self, query=query)

        params = {}

        for parameter in resource._required_parameters:
            try:
                params[parameter] = getattr(model, parameter)
            except AttributeError:
                try:
                    params[parameter] = model[parameter]
                except (KeyError, TypeError, ValueError):
                    raise ValueError(
                        'Can\'t construct URL parameter "%s" from `%s`' % (
                            parameter, model))

        return resource.uri(self, params=params, query=query)

    def is_modified_since(self, dt):
        """
        Compares datetime `dt` with `If-Modified-Since` header value.
        Returns True if `dt` is newer than `If-Modified-Since`,
        False otherwise.
        """
        if_modified_since = parse_http_date('if-modified-since', self.headers)

        if if_modified_since:
            return times.to_unix(
                dt.replace(microsecond=0)) > times.to_unix(if_modified_since)

        return True

    @property
    def deserialized(self):
        return self.body

    def wrap(self, func):
        """Wrap `func` with the Context instance as a last argument"""

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            args = list(args)+[self]
            return func(*args, **kwargs)
        return wrapped

    # response factories

    def Continue(self, *args, **kwargs):  # 100
        return responses.ContinueResponse(self, *args, **kwargs)

    def OK(self, *args, **kwargs):  # 200
        return responses.OKResponse(self, *args, **kwargs)

    def Response(self, *args, **kwargs):  # deprecated 200-like response
        return self.OK(*args, **kwargs)

    def Created(self, *args, **kwargs):  # 201
        return responses.CreatedResponse(self, *args, **kwargs)

    def Accepted(self, *args, **kwargs):  # 202
        return responses.AcceptedResponse(self, *args, **kwargs)

    def NoContent(self, *args, **kwargs):  # 204
        return responses.NoContentResponse(self, *args, **kwargs)

    def MovedPermanently(self, *args, **kwargs):  # 301
        return responses.MovedPermanentlyResponse(self, *args, **kwargs)

    def Found(self, *args, **kwargs):  # 302
        return responses.FoundResponse(self, *args, **kwargs)

    def SeeOther(self, *args, **kwargs):  # 303
        return responses.SeeOtherResponse(self, *args, **kwargs)

    def NotModified(self, *args, **kwargs):  # 304
        return responses.NotModifiedResponse(self, *args, **kwargs)

    def BadRequest(self, *args, **kwargs):  # 400
        return responses.BadRequestResponse(self, *args, **kwargs)

    def Unauthorized(self, *args, **kwargs):  # 401
        return responses.UnauthorizedResponse(self, *args, **kwargs)

    def Forbidden(self, *args, **kwargs):  # 403
        return responses.ForbiddenResponse(self, *args, **kwargs)

    def NotFound(self, *args, **kwargs):  # 404
        return responses.NotFoundResponse(self, *args, **kwargs)

    def MethodNotAllowed(self, *args, **kwargs):  # 405
        return responses.MethodNotAllowedResponse(self, *args, **kwargs)

    def NotAcceptable(self, *args, **kwargs):  # 406
        return responses.NotAcceptableResponse(self, *args, **kwargs)

    def Conflict(self, *args, **kwargs):  # 409
        return responses.ConflictResponse(self, *args, **kwargs)

    def Gone(self, *args, **kwargs):  # 410
        return responses.GoneResponse(self, *args, **kwargs)

    def UnsupportedMediaType(self, *args, **kwargs):  # 415
        return responses.UnsupportedMediaTypeResponse(self, *args, **kwargs)

    def ValidationError(self, *args, **kwargs):  # 422 WEBDAV Deprecated
        return responses.ValidationErrorResponse(self, *args, **kwargs)

    def Entity(self, *args, **kwargs):  # deprecated, 200
        return responses.EntityResponse(self, *args, **kwargs)

    def Collection(self, *args, **kwargs):  # deprecated, 200
        return responses.CollectionResponse(self, *args, **kwargs)
