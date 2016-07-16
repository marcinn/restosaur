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

    parameters.update(QueryDict(request.GET.lists()))

    ctx = Context(
            api, request=request, resource=resource,
            method=request.method, parameters=parameters, data=request.POST,
            files=request.FILES, raw=raw_body)

    return ctx


def resource_dispatcher_factory(api, resource):
    def dispatch_request(request, *args, **kw):
        ctx = build_context(api, resource, request)

        for middleware in api.middlewares:
            try:
                method = middleware.process_request
            except AttributeError:
                pass
            else:
                if method(request, ctx) is False:
                    break

        response = resource(ctx, *args, **kw)

        for middleware in api.middlewares:
            try:
                method = middleware.process_response
            except AttributeError:
                pass
            else:
                if method(request, response, ctx) is False:
                    break

        return response
    return dispatch_request
