from .utils import model_to_dict


class Response(object):
    def __init__(self, context, data=None, status=200, headers=None):
        self.headers = {}
        self.headers.update(headers or {})
        self.representation = None
        self.content_type = None
        self.context = context
        self.status = status
        self.data = data

    def get_converter(self, representation):
        dummy_converter = lambda x, context: x
        converter = self.context.resource.representations.get(representation)
        return converter or dummy_converter

    def serialize(self, serializer, data, representation):
        if data is None:
            return ''
        else:
            output = self.context.resource.convert(self.context, data, representation)
            return serializer.dumps(output)


class CreatedResponse(Response):
    def __init__(self, context, data=None):
        super(CreatedResponse, self).__init__(context, data=None, status=201)


class NoContentResponse(Response):
    def __init__(self, context, data=None):
        super(NoContentResponse, self).__init__(context, data=None, status=204)


class UnauthorizedResponse(Response):
    def __init__(self, context):
        super(UnauthorizedResponse, self).__init__(context, data=None, status=401)


class ForbiddenResponse(Response):
    def __init__(self, context):
        super(ForbiddenResponse, self).__init__(context, data=None, status=403)


class NotFoundResponse(Response):
    def __init__(self, context):
        super(NotFoundResponse, self).__init__(context, data=None, status=404)


class MethodNotAllowedResponse(Response):
    def __init__(self, context):
        super(MethodNotAllowedResponse, self).__init__(context, data=None, status=405)


class CollectionResponse(Response):
    def __init__(self, context, iterable, totalCount=None, key=None):
        super(CollectionResponse, self).__init__(context, data=iterable)
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
    def __init__(self, context):
        super(NotAcceptableResponse, self).__init__(context, data=None, status=406)


class ValidationErrorResponse(Response):
    def __init__(self, context, errors):
        resp = {
                'errors': errors,
                }
        super(ValidationErrorResponse, self).__init__(context, data=resp,
                status=422)

