import json
import re
import unittest

from restosaur import API
from restosaur.contrib.django import API as DjangoAPI
from restosaur.contrib.django.dispatch import resource_dispatcher_factory

from .utils import response_content_as_text


def _urlpattern_regex(urlpattern):
    try:
        return urlpattern._regex  # django < 2.0
    except AttributeError:
        try:
            return urlpattern.pattern._regex  # django 2.0
        except AttributeError:
            return urlpattern.pattern.regex.pattern


class APITestCase(unittest.TestCase):
    def setUp(self):
        from django.test import RequestFactory

        super(APITestCase, self).setUp()
        self.rqfactory = RequestFactory()

    def call(self, api, resource, method, *args, **kw):
        rq = getattr(self.rqfactory, method)(resource.path, *args, **kw)
        return resource_dispatcher_factory(api, resource)(rq)


class APIPathsTestCase(APITestCase):
    def test_prepending_slash_to_api_path(self):
        api = API("foo")
        self.assertEqual(api.path, "/foo")

    def test_not_striping_slash_from_api_path(self):
        api = API("foo/")
        self.assertEqual(api.path, "/foo")

    def test_status_200OK_of_nonprefixed_api_path(self):
        api = API()
        root = api.resource("/")

        @root.get()
        def root_view(ctx):
            return ctx.Response({"root": "ok"})

        resp = self.call(api, root, "get")
        self.assertEqual(resp.status_code, 200)

    def test_valid_response_of_nonprefixed_api_path(self):
        api = API()
        root = api.resource("/")

        @root.get()
        def root_view(ctx):
            return ctx.Response({"root": "ok"})

        resp = self.call(api, root, "get")
        resp_json = json.loads(response_content_as_text(resp))
        self.assertEqual(resp_json["root"], "ok")
