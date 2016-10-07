import six
import times
import warnings

from django.utils.http import http_date

from .utils import Collection


def dummy_converter(x, context):
    return x


class Response(object):
    def __init__(
            self, context, data=None, status=200, headers=None,
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

    def set_last_modified(self, dt):
        if dt:
            self.headers['Last-Modified'] = http_date(times.to_unix(dt))
        else:
            self.headers.pop('Last-Modified', None)


class OKResponse(Response):
    pass


class CreatedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(CreatedResponse, self).__init__(
                context, data=data, status=201, headers=headers)


class NoContentResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NoContentResponse, self).__init__(
                context, data=data, status=204, headers=headers)


class SeeOtherResponse(Response):
    def __init__(self, context, uri, data=None, headers=None):
        headers = headers or {}
        headers['Location'] = uri
        super(SeeOtherResponse, self).__init__(
                context, data=data, status=303, headers=headers)


class NotModifiedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NotModifiedResponse, self).__init__(
                context, data=data, status=304, headers=headers)


class BadRequestResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(BadRequestResponse, self).__init__(
                context, data=data, status=400, headers=headers)


class UnauthorizedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(UnauthorizedResponse, self).__init__(
                context, data=data, status=401, headers=headers)


class ForbiddenResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(ForbiddenResponse, self).__init__(
                context, data=data, status=403, headers=headers)


class NotFoundResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NotFoundResponse, self).__init__(
                context, data=data, status=404, headers=headers)


class MethodNotAllowedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(MethodNotAllowedResponse, self).__init__(
                context, data=data, status=405, headers=headers)


class CollectionResponse(Response):
    def __init__(self, context, iterable, totalCount=None, key=None, **kwargs):
        warnings.warn(
            '`CollectionResponse` will be removed in Restosaur v0.9. '
            'You should use plain `Response` or `OKResponse` '
            '(ctx.Response() / ctx.OK() respectively).',
            DeprecationWarning, stacklevel=3)

        coll_obj = Collection(
                context, iterable, key=key, totalcount=totalCount)
        super(CollectionResponse, self).__init__(
                context, data=coll_obj, **kwargs)


class EntityResponse(Response):
    pass


class NotAcceptableResponse(Response):
    def __init__(self, context, headers=None):
        super(NotAcceptableResponse, self).__init__(
                context, data=None, status=406, headers=headers)


class UnsupportedMediaTypeResponse(Response):
    def __init__(self, context, headers=None):
        super(UnsupportedMediaTypeResponse, self).__init__(
                context, data=None, status=415, headers=headers)


class ValidationErrorResponse(Response):
    def __init__(self, context, errors, headers=None):
        resp = {
                'errors': errors,
                }
        super(ValidationErrorResponse, self).__init__(
                context, data=resp, status=422, headers=headers)


class InternalErrorResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(InternalErrorResponse, self).__init__(
                context, data=data, status=500, headers=headers)


class NotImplementedResponse(Response):
    def __init__(self, context, data=None, headers=None):
        super(NotImplementedResponse, self).__init__(
                context, data=data, status=501, headers=headers)


def exception_response_factory(context, ex, tb=None, extra=None):
    import traceback

    if isinstance(ex, NotImplementedError):
        cls = NotImplementedResponse
    else:
        cls = InternalErrorResponse

    data = {}
    data.update(extra or {})
    data.update({
        'error': six.text_type(ex),
        })

    if tb:
        def stack_trace(x):
            return dict(zip(['file', 'line', 'fn', 'source'], x))
        data['traceback'] = list(map(stack_trace, traceback.extract_tb(tb)))

    return cls(context=context, data=data)
