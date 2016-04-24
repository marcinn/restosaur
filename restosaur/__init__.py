"""
Restosaur - a tiny but real REST library

Author: Marcin Nowak <marcin.j.nowak@gmail.com>
"""

from collections import defaultdict
import types

import resource
import responses
import filters
import decorators
import serializers
import representations



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
    def __init__(self, path='', middlewares=None,
            default_content_type='application/json',
            default_representation='application/json',
            serializers=serializers.default_serializers):

        path = path or ''

        if not path.endswith('/'):
            path += '/'

        self.path = path
        self.resources = []
        self.middlewares = middlewares or []
        self.default_representation = default_representation
        self.default_content_type = default_content_type
        self.serializers = serializers
        self.representations = defaultdict(dict)

    def resource(self, *args, **kw):
        obj = resource.Resource(self, *args, **kw)
        self.resources.append(obj)
        return obj

    def representation_for(self, scope, content_type=None):
        content_type = content_type or self.default_content_type

        scope_representations = self.representations[scope]

        try:
            representation = scope_representations[content_type]
        except KeyError:
            representation = representations.Representation()
            self.representations[scope][content_type]=representation

        return representation

    def get_urls(self):
        from django.conf.urls import patterns, url, include
        from django.views.decorators.csrf import csrf_exempt
        from .dispatch import resource_dispatcher_factory
        import urltemplate

        urls = []

        for resource in self.resources:
            path = urltemplate.to_django_urlpattern(resource._path)
            if path.startswith('/'):
                path=path[1:]
            urls.append(url('^%s$' % path,
                csrf_exempt(resource_dispatcher_factory(self, resource))))

        return [url('^%s' % self.path, include(patterns('', *urls)))]

    def urlpatterns(self):
        from django.conf.urls import patterns, include
        return patterns('', (r'^', include(self.get_urls())))

    def autodiscover(self, *args, **kw):
        """
        Shortcut for `restosaur.autodiscover()`
        """
        autodiscover(*args, **kw)


