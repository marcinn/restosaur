from collections import defaultdict

from .representations import (
        RepresentationAlreadyRegistered, UnknownRepresentation,
        Representation)
from .resource import Resource
from .utils import autodiscover, join_content_type_with_vnd


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
        self._representations = defaultdict(dict)  # type->repr_key

    def add_resources(self, *resources):
        self.resources += resources

    def resource(self, *args, **kw):
        obj = Resource(*args, **kw)
        self.add_resources(obj)
        return obj

    def add_representation(
            self, type_, content_type, vnd=None,
            serializer=None, _transform_func=None):

        representation = Representation(
            content_type=content_type, vnd=vnd,
            serializer=serializer, _transform_func=_transform_func)

        self.register_representation(representation)

    def register_representation(self, type_, representation):

        content_type = representation.content_type
        vnd = representation.vnd
        repr_key = join_content_type_with_vnd(content_type, vnd)

        if repr_key in self._representations[type_]:
            raise RepresentationAlreadyRegistered(
                            '%s: %s' % (type_, repr_key))

        self._representations[type_][repr_key] = representation

    def get_representation(self, type_, content_type, vnd=None):
        repr_key = join_content_type_with_vnd(content_type, vnd)
        try:
            return self._representations[type_][repr_key]
        except KeyError:
            raise UnknownRepresentation('%s: %s' % (
                            type_, repr_key))

    def get_urls(self):
        try:
            from django.conf.urls import patterns, url, include
        except ImportError:
            from django.conf.urls import url, include

            def patterns(x, *urls):
                return list(urls)

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
        try:
            from django.conf.urls import patterns, include
        except ImportError:
            return self.get_urls()
        else:
            return patterns('', (r'^', include(self.get_urls())))

    def autodiscover(self, *args, **kw):
        """
        Shortcut for `restosaur.autodiscover()`
        """
        autodiscover(*args, **kw)
