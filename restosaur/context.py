import responses


class Context(object):
    def __init__(self, api, request, resource, method, parameters=None,
            body=None):
        self.method = method
        self.api = api
        self.headers = {}
        self.request = request
        self.body = body
        self.resource = resource
        self.parameters = parameters or {}
        self.deserializer = None
        self.content_type = None

    def build_absolute_uri(self, path):
        return self.request.build_absolute_uri('/%s%s' % (self.api.path, path))

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

