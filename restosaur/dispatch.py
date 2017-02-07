from .context import QueryDict
from .headers import normalize_header_name


def build_context(api, resource, request):
    try:
        # Django may raise RawPostDataException sometimes;
        # i.e. when processing POST multipart/form-data;
        # In that cases we can't access raw body anymore, sorry

        raw_body = request.body
    except:
        raw_body = None

    parameters = {}

    if request.resolver_match:
        parameters.update(request.resolver_match.kwargs)

    parameters.update(QueryDict(list(request.GET.lists())))

    headers = dict(map(
        lambda x: (normalize_header_name(x[0]), x[1]),
        filter(lambda x: x[0].startswith('HTTP_'), request.META.items())))

    try:
        content_length = int(request.META['CONTENT_LENGTH'])
    except (KeyError, TypeError, ValueError):
        content_length = 0

    content_type = request.META.get('CONTENT_TYPE')

    return api.make_context(
            host=request.get_host(), path=request.path,
            method=request.method, parameters=parameters,
            data=request.POST, files=request.FILES, raw=raw_body,
            charset=request.encoding or api.default_charset,
            secure=request.is_secure(), encoding=request.GET.encoding,
            resource=resource, request=request, headers=headers,
            content_type=content_type, content_length=content_length)


def resource_dispatcher_factory(api, resource, response_class):
    def dispatch_request(request, *args, **kw):
        ctx = build_context(api, resource, request)
        bypass_resource_call = False
        middlewares_called = []

        for middleware in api.middlewares:
            middlewares_called.append(middleware)

            try:
                method = middleware.process_request
            except AttributeError:
                pass
            else:
                if method(request, ctx) is False:
                    bypass_resource_call = True
                    break

        if not bypass_resource_call:
            response = resource(ctx, *args, **kw)
        else:
            response = response_class()

        middlewares_called.reverse()

        for middleware in middlewares_called:
            try:
                method = middleware.process_response
            except AttributeError:
                pass
            else:
                if method(request, response, ctx) is False:
                    break

        return response
    return dispatch_request
