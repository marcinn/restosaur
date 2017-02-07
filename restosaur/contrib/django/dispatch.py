from django.http import HttpResponse

from restosaur.context import QueryDict
from restosaur.headers import normalize_header_name
from restosaur import dispatch as restosaur_dispatch


def build_context(api, resource, request):
    try:
        # Django may raise RawPostDataException sometimes;
        # i.e. when processing POST multipart/form-data;
        # In that cases we can't access raw body anymore, sorry

        raw_body = request.body
    except:
        raw_body = None

    parameters = {}

    if request.resolver_match:
        parameters.update(request.resolver_match.kwargs)

    parameters.update(QueryDict(list(request.GET.lists())))

    headers = dict(map(
        lambda x: (normalize_header_name(x[0]), x[1]),
        filter(lambda x: x[0].startswith('HTTP_'), request.META.items())))

    try:
        content_length = int(request.META['CONTENT_LENGTH'])
    except (KeyError, TypeError, ValueError):
        content_length = 0

    content_type = request.META.get('CONTENT_TYPE')

    return api.make_context(
            host=request.get_host(), path=request.path,
            method=request.method, parameters=parameters,
            data=request.POST, files=request.FILES, raw=raw_body,
            charset=request.encoding or api.default_charset,
            secure=request.is_secure(), encoding=request.GET.encoding,
            resource=resource, request=request, headers=headers,
            content_type=content_type, content_length=content_length)


def _do_http_response(response, content, content_type):
    """
    RESTResponse -> HTTPResponse factory
    """

    if isinstance(response, HttpResponse):
        return response

    httpresp = HttpResponse(content, status=response.status)

    if content_type:
        httpresp['Content-Type'] = content_type

    for header, value in response.headers.items():
        httpresp[header] = value

    return httpresp


def response_builder(response, content, content_type):
    if response is None:
        return HttpResponse()
    else:
        return _do_http_response(response, content, content_type)


def resource_dispatcher_factory(api, resource):
    return restosaur_dispatch.resource_dispatcher_factory(
                    api, resource, response_builder, build_context)
