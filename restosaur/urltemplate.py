import re

RE_PARAMS = re.compile('(/:([a-zA-Z_]+))')


def to_url(urltemplate, params):
    uri = None

    for needle, key in RE_PARAMS.findall(urltemplate):
        try:
            uri =urltemplate.replace(needle, '/%s' % params[key])
        except KeyError:
            pass
    return uri


def to_django_urlpattern(path):
    return RE_PARAMS.sub('/(?P<\\2>[^/]+)', path)


