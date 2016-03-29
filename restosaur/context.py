import responses
import email
import times
import urllib
import urlparse
import types

from django.utils.encoding import force_bytes # todo: implement own conversion utility

from .loading import load_resource


def parse_http_date(header, headers):
    if header in headers and headers[header]:
        timetuple = email.utils.parsedate_tz(headers[header])
        try:
            return times.from_unix(email.utils.mktime_tz(timetuple))
        except (TypeError, ValueError):
            pass


class Context(object):
    def __init__(self, api, request, resource, method, parameters=None,
            body=None, data=None, files=None, raw=None, extra=None, headers=None):
        self.method = method
        self.api = api
        self.headers = headers or {}
        self.request = request
        self.body = body
        self.raw = raw
        self.resource = resource
        self.parameters = parameters or {} # GET
        self.data = data or {} # POST
        self.files = files or {} # FILES
        self.deserializer = None
        self.content_type = None
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
            current = 'http%s://%s%s' % ('s' if self.request.is_secure() else '',
                    self.request.get_host(), self.request.path)
            return urlparse.urljoin(current, path)

        params = {}
        if path:
            full_path = u'/'.join(filter(None, (self.api.path+path).split('/')))
            if path.endswith('/'):
                full_path+='/'
            uri = build_uri('/'+full_path)
        else:
            params = dict(self.parameters)
            uri = build_uri(self.request.path)

        enc = self.request.GET.encoding # todo: change to internal restosaur settings

        params.update(parameters or {})
        params = dict(map(lambda x: (force_bytes(x[0], enc), force_bytes(x[1], enc)),
            params.items()))

        if params:
            return '%s?%s' % (uri, urllib.urlencode(params))
        else:
            return uri

    def url_for(self, resource, **kwargs):
        """
        Shortcut wrapper of `resource.uri()`
        """
        if isinstance(resource, types.StringTypes):
            resource = load_resource(resource)
        return resource.uri(self, params=kwargs)

    def is_modified_since(self, dt):
        """
        Compares datetime `dt` with `If-Modified-Since` header value.
        Returns True if `dt` is newer than `If-Modified-Since`, False otherwise.
        """
        if_modified_since = parse_http_date('if-modified-since', self.headers)

        if if_modified_since:
            return times.to_unix(dt.replace(microsecond=0)) > times.to_unix(if_modified_since)

        return True

    @property
    def deserialized(self):
        return self.body

    # response factories

    def Response(self, *args, **kwargs):
        return responses.Response(self, *args, **kwargs)

    def Created(self, *args, **kwargs):
        return responses.CreatedResponse(self, *args, **kwargs)

    def ValidationError(self, *args, **kwargs):
        return responses.ValidationErrorResponse(self, *args, **kwargs)

    def NotAcceptable(self, *args, **kwargs):
        return responses.NotAcceptableResponse(self, *args, **kwargs)

    def NotFound(self, *args, **kwargs):
        return responses.NotFoundResponse(self, *args, **kwargs)

    def SeeOther(self, *args, **kwargs):
        return responses.SeeOtherResponse(self, *args, **kwargs)

    def NotModified(self, *args, **kwargs):
        return responses.NotModifiedResponse(self, *args, **kwargs)

    def MethodNotAllowed(self, *args, **kwargs):
        return responses.MethodNotAllowedResponse(self, *args, **kwargs)

    def Forbidden(self, *args, **kwargs):
        return responses.ForbiddenResponse(self, *args, **kwargs)

    def Unauthorized(self, *args, **kwargs):
        return responses.UnauthorizedResponse(self, *args, **kwargs)

    def NoContent(self, *args, **kwargs):
        return responses.NoContentResponse(self, *args, **kwargs)

    def Entity(self, *args, **kwargs):
        return responses.EntityResponse(self, *args, **kwargs)

    def Collection(self, *args, **kwargs):
        return responses.CollectionResponse(self, *args, **kwargs)

