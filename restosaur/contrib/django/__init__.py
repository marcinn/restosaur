from __future__ import absolute_import

from django.conf import settings
from django.utils.encoding import force_text
from django.views import debug

from ...api import API as BaseAPI
from ...representations import RestosaurException


def django_html_exception(obj, ctx):
    if settings.DEBUG:
        resp = debug.technical_500_response(
                ctx.request, exc_type=obj.exc_type,
                exc_value=obj.exc_value,
                tb=obj.tb, status_code=obj.status_code)
        return force_text(resp.content)
    return '<h1>Internal Server Error (%s)</h1>' % obj.status_code


class API(BaseAPI):
    def __init__(self, *args, **kw):
        from django.conf import settings
        charset = kw.pop('default_charset', None) or settings.DEFAULT_CHARSET
        debug = kw.pop('debug', None) or settings.DEBUG
        kw['default_charset'] = charset
        kw['debug'] = debug
        super(API, self).__init__(*args, **kw)

    def get_urls(self):
        try:
            from django.conf.urls import patterns, url, include
        except ImportError:
            from django.conf.urls import url, include

            def patterns(x, *urls):
                return list(urls)

        from django.views.decorators.csrf import csrf_exempt
        from ...dispatch import resource_dispatcher_factory
        from ... import urltemplate

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

    def add_resources(self, *resources):
        super(API, self).add_resources(*resources)

        for resource in resources:
            resource.add_representation(
                    RestosaurException, content_type='text/html',
                    _transform_func=django_html_exception)
