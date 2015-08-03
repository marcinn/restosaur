from django.utils.http import http_date
from .utils import model_to_dict
import times


class Response(object):
    def __init__(self, context, data=None, status=200, headers=None,
            last_modified=None):
        self.headers = {}
        self.headers.update(headers or {})
        self.representation = None
        self.content_type = None
        self.context = context
        self.status = status
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

    def serialize(self, serializer, data, representation):
        if data is None:
            return ''
        else:
            if self.status >= 200 and self.status <300:
                output = self.context.resource.convert(self.context, data, representation)
            else:
                output = data
            return serializer.dumps(output)


class CreatedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(CreatedResponse, self).__init__(context, data=data, status=201,
                headers=headers)


class NoContentResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NoContentResponse, self).__init__(context, data=None, status=204,
                headers=headers)


class NotModifiedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NotModifiedResponse, self).__init__(context, data=None, status=304,
                headers=headers)


class UnauthorizedResponse(Response):
    def __init__(self, context, headers=None):
        super(UnauthorizedResponse, self).__init__(context, data=None,
                status=401, headers=headers)


class ForbiddenResponse(Response):
    def __init__(self, context, headers=None):
        super(ForbiddenResponse, self).__init__(context, data=None, status=403,
                headers=headers)


class NotFoundResponse(Response):
    def __init__(self, context, headers=None):
        super(NotFoundResponse, self).__init__(context, data=None, status=404,
                headers=headers)


class MethodNotAllowedResponse(Response):
    def __init__(self, context, headers=None):
        super(MethodNotAllowedResponse, self).__init__(context, data=None,
                status=405, headers=headers)


class CollectionResponse(Response):
    def __init__(self, context, iterable, totalCount=None, key=None, headers=None):
        super(CollectionResponse, self).__init__(context, data=iterable,
                headers=headers)
        self.key = key or 'items'
        self.totalCount = totalCount

    def serialize(self, serializer, iterable, representation):
        resp = {
                self.key: map(lambda x: self.context.resource.convert(self.context, x, representation), iterable),
                'totalCount': self.totalCount if self.totalCount is not None else len(iterable),
                }
        return serializer.dumps(resp)


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

