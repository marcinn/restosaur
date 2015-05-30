from django.http import HttpResponse
from .headers import parse_accept_header, build_content_type_header
from .utils import model_to_dict


class Response(HttpResponse):
    def __init__(self, context, data=None, *args, **kwargs):
        self.representation = None
        self.content_type = None

        if 'accept' in context.headers:
            accepting = parse_accept_header(context.headers['accept'])
            for content_type, representation, q in accepting:
                if content_type == '*/*' or content_type == 'application/*':
                    content_type = 'application/json'
                if context.resource.serializers.contains(content_type)\
                    and (not representation or representation in context.resource.representations):
                    self.representation = representation or 'default'
                    self.serializer = context.resource.serializers[content_type]
                    self.content_type = build_content_type_header(content_type, representation)
                    break
        else:
            self.content_type = 'application/json'


        if not self.content_type or not self.representation:
            super(Response, self).__init__(status=406) # Not Acceptable
            return

        super(Response, self).__init__(*args, **kwargs)

        self.serializer = context.resource.serializers[content_type]
        self.context = context
        self['Content-Type'] = self.content_type

        if data:
            self.set_data(data)

    def set_data(self, data):
        self.content = self.serializer.dumps(data)

    def get_converter(self, representation):
        dummy_converter = lambda x, context: x
        converter = self.context.resource.representations.get(representation)
        return converter or dummy_converter


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
        super(CollectionResponse, self).__init__(context)
        key = key or 'items'
        resp = {
                key: self.get_items(iterable),
                'totalCount': totalCount if totalCount is not None else len(iterable),
                }
        self.set_data(resp)

    def get_items(self, iterable):
        dummy_converter = lambda x, context: x
        converter = self.get_converter(self.representation) or dummy_converter
        return list(map(lambda x: converter(x, self.context), iterable))


class EntityResponse(Response):
    def set_data(self, data):
        convert = self.get_converter(self.representation)
        content = convert(data, self.context)
        super(EntityResponse, self).set_data(content)


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

