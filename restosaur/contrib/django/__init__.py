from __future__ import absolute_import

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_str as force_text

from django.views import debug

from ...api import API as BaseAPI
from ...representations import ExceptionRepresentation
from ...urltemplate import RE_PARAMS
from .utils import autodiscover


def to_django_urlpattern(path):
    return RE_PARAMS.sub("/(?P<\\2>[^/]+)", path)


def django_html_exception(obj, ctx):
    if ctx.api.debug:
        resp = debug.technical_500_response(
            ctx.request,
            exc_type=obj.exc_type,
            exc_value=obj.exc_value,
            tb=obj.tb,
            status_code=obj.status_code,
        )
        return force_text(resp.content)
    return "<h1>Internal Server Error (%s)</h1>" % obj.status_code


class API(BaseAPI):
    def __init__(self, *args, **kw):
        from django.conf import settings

        charset = kw.pop("default_charset", None) or settings.DEFAULT_CHARSET
        debug = kw.pop("debug", settings.DEBUG)

        self.append_slash = kw.pop("append_slash", False)

        kw["default_charset"] = charset
        kw["debug"] = debug

        super(API, self).__init__(*args, **kw)

        self.add_representation(
            ExceptionRepresentation,
            content_type="text/html",
            _transform_func=django_html_exception,
            qvalue=0.2,
        )

    def get_urls(self):
        try:
            from django.conf.urls import include, patterns, url
        except ImportError:
            try:
                from django.conf.urls import include, url
            except ImportError:
                from django.urls import path as url

            def patterns(x, *urls):
                return list(urls)

        from django.views.decorators.csrf import csrf_exempt

        from .dispatch import resource_dispatcher_factory

        urls = []
        api_prefix = self.path.strip("/")

        for resource in self.resources:
            path = to_django_urlpattern(resource._path)
            if self.append_slash:
                path = path + "/"

            urls.append(
                url(
                    r"%s" % (path or ("/" if api_prefix else "")),
                    csrf_exempt(resource_dispatcher_factory(self, resource)),
                )
            )

        return [url("%s" % api_prefix, include(patterns("", *urls)))]

    def urlpatterns(self):
        try:
            from django.conf.urls import include, patterns
        except ImportError:
            return self.get_urls()
        else:
            return patterns("", (r"^", include(self.get_urls())))

    def autodiscover(self, *args, **kw):
        """
        Shortcut for `restosaur.autodiscover()`
        """
        autodiscover(*args, **kw)
