import unittest

from restosaur import API
from restosaur.contrib.django.dispatch import resource_dispatcher_factory


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()

        from django.test import RequestFactory
        from django.http import StreamingHttpResponse, HttpResponse

        self.api = API('foo')
        self.resource = self.api.resource('test')
        self.stream_resource = self.api.resource('test-stream')

        self.StreamingHttpResponse = StreamingHttpResponse
        self.HttpResponse = HttpResponse

        @self.resource.get()
        def ctrl(ctx):
            return HttpResponse()

        @self.stream_resource.get()
        def ctrl_stream(ctx):
            return StreamingHttpResponse()

        self.rqfactory = RequestFactory()

    def call(self, resource, method, *args, **kw):
        rq = getattr(self.rqfactory, method)(resource.path, *args, **kw)
        return resource_dispatcher_factory(self.api, resource)(rq)


class PassingThroughNativeResponseTestCase(BaseTestCase):
    def test_http_response_class(self):
        resp = self.call(self.resource, 'get', HTTP_ACCEPT='application/json')
        self.assertTrue(isinstance(resp, self.HttpResponse))

    def test_http_streaming_response_class(self):
        resp = self.call(
            self.stream_resource, 'get', HTTP_ACCEPT='application/json')
        self.assertTrue(isinstance(resp, self.StreamingHttpResponse))
