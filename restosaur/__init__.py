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
    from django.utils.importlib import import_module

    for app in settings.INSTALLED_APPS:
        mod = import_module(app)
        try:
            import_module('%s.views' % app)
        except:
            pass
        try:
            import_module('%s.restapi' % app)
        except:
            pass


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
                        out[key]=qd.get(key)
                    return out

                ctx = Context(self, request=request, resource=resource,
                    method=request.method, parameters=querydict_to_dict(request.GET))

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


