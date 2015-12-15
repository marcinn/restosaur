"""
Restosaur - a tiny but real REST library

Author: Marcin Nowak <marcin.j.nowak@gmail.com>
"""


import resource
import responses
import filters
import decorators


def autodiscover():
    from django.conf import settings

    try:
        from django.utils.module_loading import autodiscover_modules
    except ImportError:
        from django.utils.importlib import import_module
        from django.utils.module_loading import module_has_submodule
        autodiscover_modules = None

    if autodiscover_modules:
        autodiscover_modules('restapi')
    else:
        for app in settings.INSTALLED_APPS:
            mod = import_module(app)
            try:
                import_module('%s.restapi' % app)
            except:
                if module_has_submodule(mod, 'restapi'):
                    raise


class API(object):
    def __init__(self, path, resources=None, middlewares=None):
        if not path.endswith('/'):
            path += '/'
        self.path = path
        self.resources = resources or []
        self.middlewares = middlewares or []

    def add_resources(self, *resources):
        self.resources += resources

    def resource(self, *args, **kw):
        obj = resource.Resource(*args, **kw)
        self.add_resources(obj)
        return obj

    def get_urls(self):
        from django.conf.urls import patterns, url, include
        from django.views.decorators.csrf import csrf_exempt
        from .context import Context
        import urltemplate

        urls = []

        def middleware_executor(resource):
            def process(request, *args, **kw):
                def querydict_to_dict(qd):
                    out = {}
                    for key in qd:
                        if len(qd.getlist(key))>1:
                            out[key]=qd.getlist(key)
                        else:
                            out[key]=qd.get(key)
                    return out

                try:
                    raw_body = request.body # Django may raise RawPostDataException sometimes;
                                            # i.e. when processing POST multipart/form-data;
                                            # In that cases we can't access raw body anymore, sorry
                except:
                    raw_body = None

                parameters = {}
                parameters.update(request.resolver_match.kwargs)
                parameters.update(querydict_to_dict(request.GET))
                ctx = Context(self, request=request, resource=resource,
                    method=request.method, parameters=parameters, data=request.POST,
                    files=request.FILES, raw=raw_body)

                for middleware in self.middlewares:
                    try:
                        method = middleware.process_request
                    except AttributeError:
                        pass
                    else:
                        if method(request, ctx) == False:
                            break

                response = resource(ctx, *args, **kw)

                for middleware in self.middlewares:
                    try:
                        method = middleware.process_response
                    except AttributeError:
                        pass
                    else:
                        if method(request, response, ctx) == False:
                            break

                return response
            return process

        for resource in self.resources:
            path = urltemplate.to_django_urlpattern(resource._path)
            urls.append(url('^%s$' % path,
                csrf_exempt(middleware_executor(resource))))

        return [url('^%s' % self.path, include(patterns('', *urls)))]

    def urlpatterns(self):
        from django.conf.urls import patterns, include
        return patterns('', (r'^', include(self.get_urls())))

    def autodiscover(self):
        autodiscover()


