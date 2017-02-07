def resource_dispatcher_factory(api, resource, response_builder, context_builder):
    def dispatch_request(request, *args, **kw):
        ctx = context_builder(api, resource, request)
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
            response, content, ct = resource(ctx, *args, **kw)
        else:
            response, content, ct = None, None, None

        middlewares_called.reverse()

        for middleware in middlewares_called:
            try:
                method = middleware.process_response
            except AttributeError:
                pass
            else:
                if method(request, response, ctx) is False:
                    break

        return response_builder(response, content, ct)
    return dispatch_request
