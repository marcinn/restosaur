"""
Restosaur - a tiny but real REST library

Author: Marcin Nowak <marcin.j.nowak@gmail.com>
"""


import resource
import responses
import decorators


class API(object):
    def __init__(self, path, *resources):
        if not path.endswith('/'):
            path += '/'
        self.path = path
        self.resources = resources

    def add_resources(self, *resources):
        self.resources += resources

    def resource(self, *args, **kw):
        obj = resource.Resource(*args, **kw)
        self.add_resources(obj)
        return obj

    def get_urls(self):
        from django.conf.urls import patterns, url, include
        from django.views.decorators.csrf import csrf_exempt
        import urltemplate

        urls = []

        for resource in self.resources:
            path = urltemplate.to_django_urlpattern(resource._path)
            urls.append(url('^%s$' % path, csrf_exempt(resource)))

        return [url('^%s' % self.path, include(patterns('', *urls)))]

