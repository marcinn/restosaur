from django.utils.http import http_date
from .utils import model_to_dict
import times


class Response(object):
    def __init__(self, context, data=None, status=200, headers=None,
            last_modified=None, extra=None, add_links=True, links_key='_links'):
        self.headers = {}
        self.headers.update(headers or {})
        self.representation = None
        self.content_type = None
        self.context = context
        self.status = status
        self.extra = extra
        self.links_key = links_key
        self.add_links = add_links
        self.data = data
        if last_modified:
            self.set_last_modified(last_modified)

    def get_converter(self, representation):
        dummy_converter = lambda x, context: x
        converter = self.context.resource.representations.get(representation)
        return converter or dummy_converter

    def set_last_modified(self, dt):
        if dt:
            self.headers['Last-Modified'] = http_date(times.to_unix(dt))
        else:
            self.headers.pop('Last-Modified', None)

    def serialize(self, data, representation):
        if data is None and not self.extra:
            return ''
        else:
            if self.status >= 200 and self.status <300:
                output = {}
                output.update(self.extra or {})
                output.update(self.context.resource.convert(self.context, data, representation))
                self._add_links(output, data, representation)
            else:
                output = data
            return output

    def _serialize_links(self, data, representation):
        links = {}
        if self.add_links and self.context.resource._links:
            for key in self.context.resource._links:
                method, linked_resource = self.context.resource._links[key]
                links[key]={
                    'uri': linked_resource.uri(self.context, params=self.context.parameters),
                    'method': method.upper(),
                    }
        return links

    def _add_links(self, resp, data, representation):
        if not self.links_key in resp:
            resp[self.links_key] = {}
        resp[self.links_key].update(
                self._serialize_links(data, representation))
        return resp


class CreatedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(CreatedResponse, self).__init__(context, data=data, status=201,
                headers=headers)


class NoContentResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NoContentResponse, self).__init__(context, data=data, status=204,
                headers=headers)


class SeeOtherResponse(Response):
    def __init__(self, context, uri, data=None, headers=None):
        headers = headers or {}
        headers['Location'] = uri
        super(SeeOtherResponse, self).__init__(context, data=data,
                status=303, headers=headers)


class NotModifiedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NotModifiedResponse, self).__init__(context, data=data, status=304,
                headers=headers)


class UnauthorizedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(UnauthorizedResponse, self).__init__(context, data=data,
                status=401, headers=headers)


class ForbiddenResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(ForbiddenResponse, self).__init__(context, data=data, status=403,
                headers=headers)


class NotFoundResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NotFoundResponse, self).__init__(context, data=data, status=404,
                headers=headers)


class MethodNotAllowedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(MethodNotAllowedResponse, self).__init__(context, data=data,
                status=405, headers=headers)


class CollectionResponse(Response):
    def __init__(self, context, iterable, totalCount=None, key=None, **kwargs):
        super(CollectionResponse, self).__init__(context, data=iterable,
                **kwargs)
        self.key = key or 'items'
        self.totalCount = totalCount

    def serialize(self, iterable, representation):
        resp = {
                self.key: map(lambda x: self.context.resource.convert(self.context, x, representation), iterable),
                'totalCount': self.totalCount if self.totalCount is not None else len(iterable),
                }
        resp.update(self.extra or {})
        self._add_links(resp, iterable, representation)
        return resp


class EntityResponse(Response):
    pass


class NotAcceptableResponse(Response):
    def __init__(self, context, headers=None):
        super(NotAcceptableResponse, self).__init__(context, data=None,
                status=406, headers=headers)


class ValidationErrorResponse(Response):
    def __init__(self, context, errors, headers=None):
        resp = {
                'errors': errors,
                }
        super(ValidationErrorResponse, self).__init__(context, data=resp,
                status=422, headers=headers)


class InternalErrorResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(InternalErrorResponse, self).__init__(context, data=data,
                status=500, headers=headers)


class NotImplementedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NotImplementedResponse, self).__init__(context, data=data,
                status=501, headers=headers)


def exception_response_factory(context, ex, tb=None, extra=None):
    import traceback

    if isinstance(ex, NotImplementedError):
        cls = NotImplementedResponse
    else:
        cls = InternalErrorResponse

    data = {}
    data.update(extra or {})
    data.update({
        'error': unicode(ex),
        })

    if tb:
        def stack_trace(x):
            return dict(zip(['file','line','fn','source'], x))
        data['traceback'] = map(stack_trace, traceback.extract_tb(tb))

    return cls(context=context, data=data)

