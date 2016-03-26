from .context import Context


def querydict_to_dict(qd):
    out = {}
    for key in qd:
        if len(qd.getlist(key))>1:
            out[key]=qd.getlist(key)
        else:
            out[key]=qd.get(key)
    return out


def build_context(api, resource, request):
    try:
        raw_body = request.body # Django may raise RawPostDataException sometimes;
                                # i.e. when processing POST multipart/form-data;
                                # In that cases we can't access raw body anymore, sorry
    except:
        raw_body = None

    parameters = {}

    if request.resolver_match:
        parameters.update(request.resolver_match.kwargs)

    parameters.update(querydict_to_dict(request.GET))

    ctx = Context(api, request=request, resource=resource,
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
                if method(request, ctx) == False:
                    break

        response = resource(ctx, *args, **kw)

        for middleware in api.middlewares:
            try:
                method = middleware.process_response
            except AttributeError:
                pass
            else:
                if method(request, response, ctx) == False:
                    break

        return response
    return dispatch_request


