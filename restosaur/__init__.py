"""
Restosaur - a tiny but real REST library

Author: Marcin Nowak <marcin.j.nowak@gmail.com>
"""

from __future__ import absolute_import

from . import resource
from . import responses  # NOQA
from . import filters  # NOQA
from . import decorators  # NOQA


default_app_config = 'restosaur.apps.RestosaurAppConfig'


def autodiscover(module_name='restapi'):
    from django.conf import settings

    try:
        from django.utils.module_loading import autodiscover_modules
    except ImportError:
        from django.utils.importlib import import_module
        from django.utils.module_loading import module_has_submodule
        autodiscover_modules = None

    if autodiscover_modules:
        autodiscover_modules(module_name)
    else:
        for app in settings.INSTALLED_APPS:
            mod = import_module(app)
            try:
                import_module('%s.%s' % (app, module_name))
            except:
                if module_has_submodule(mod, module_name):
                    raise


class API(object):
    def __init__(self, path=None, resources=None, middlewares=None):
        path = path or ''
        if path and not path.endswith('/'):
            path += '/'
        if path and path.startswith('/'):
            path = path[1:]
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
        from .dispatch import resource_dispatcher_factory
        from . import urltemplate

        urls = []

        for resource in self.resources:
            path = urltemplate.to_django_urlpattern(resource._path)
            if path.startswith('/'):
                path = path[1:]
            urls.append(url(
                '^%s$' % path, csrf_exempt(
                    resource_dispatcher_factory(self, resource))))

        return [url('^%s' % self.path, include(patterns('', *urls)))]

    def urlpatterns(self):
        from django.conf.urls import patterns, include
        return patterns('', (r'^', include(self.get_urls())))

    def autodiscover(self, *args, **kw):
        """
        Shortcut for `restosaur.autodiscover()`
        """
        autodiscover(*args, **kw)
