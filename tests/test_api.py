import json
import unittest

from restosaur import API
from restosaur.dispatch import resource_dispatcher_factory


class APITestCase(unittest.TestCase):
    def setUp(self):
        from django.test import RequestFactory

        super(APITestCase, self).setUp()
        self.rqfactory = RequestFactory()

    def call(self, api, resource, method, *args, **kw):
        rq = getattr(self.rqfactory, method)(resource.path, *args, **kw)
        return resource_dispatcher_factory(api, resource)(rq)


class APIPathsTestCase(APITestCase):

    def test_appending_slash_to_api_path(self):
        api = API('foo')
        self.assertEqual(api.path, 'foo/')

    def test_not_appending_slash_to_api_path_if_exists(self):
        api = API('foo/')
        self.assertEqual(api.path, 'foo/')

    def test_that_root_url_pattern_does_not_contain_slash(self):
        api = API('foo')
        api.resource('/')
        urls = api.get_urls()
        root_url = urls[0].url_patterns[0]
        self.assertFalse('/' in root_url._regex)

    def test_that_typical_url_pattern_does_not_contain_prepending_slash(self):
        api = API('foo')
        api.resource('bar/')
        urls = api.get_urls()
        bar_url = urls[0].url_patterns[0]
        self.assertEqual(bar_url._regex, '^bar/$')

    def test_status_200OK_of_nonprefixed_api_path(self):
        api = API()
        root = api.resource('/')

        @root.get()
        def root_view(ctx):
            return ctx.Response({'root': 'ok'})

        resp = self.call(api, root, 'get')
        self.assertEqual(resp.status_code, 200)

    def test_valid_response_of_nonprefixed_api_path(self):
        api = API()
        root = api.resource('/')

        @root.get()
        def root_view(ctx):
            return ctx.Response({'root': 'ok'})

        resp = self.call(api, root, 'get')
        resp_json = json.loads(resp.content)
        self.assertEqual(resp_json['root'], 'ok')

