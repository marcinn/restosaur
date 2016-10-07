from .context import Context, QueryDict


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

    context_class = api.context_class or Context

    ctx = context_class(
            api, request=request, resource=resource,
            method=request.method, parameters=parameters, data=request.POST,
            files=request.FILES, raw=raw_body,
            charset=request.encoding or api.default_charset)

    return ctx


def resource_dispatcher_factory(api, resource):
    from django.http import HttpResponse

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
            response = HttpResponse()

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
