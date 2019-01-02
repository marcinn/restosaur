import unittest

from restosaur import API
from restosaur.dispatch import resource_dispatcher_factory


class CountMiddleware(object):
    def __init__(self):
        self.process_request_count = 0
        self.process_response_count = 0

    def process_request(self, *args, **kw):
        self.process_request_count += 1

    def process_response(self, *args, **kw):
        self.process_response_count += 1


class BreakRequestMiddleware(object):
    def process_request(self, request, context):
        return context.Created()


class ReplaceResponseMiddleware(object):
    def process_response(self, request, response, context):
        return context.Created()


class ModifyResponseMiddleware(object):
    def process_response(self, request, response, context):
        response._status = 666


class BaseMiddlewareTestCase(unittest.TestCase):
    def setUp(self):
        self.api = self.createAPI()

        self.resource = self.api.resource('/')

        @self.resource.get()
        @self.resource.post()
        def resource_callback(ctx):
            return ctx.OK()

    def call(
            self, resource=None, method='get', parameters=None, data=None,
            headers=None):

        resource = resource or self.resource

        def response_builder(response):
            return response

        def context_builder(api, resource, request):
            return api.make_context(**request)

        dispatcher = resource_dispatcher_factory(
                self.api, resource, response_builder, context_builder)

        return dispatcher({
            'path': resource.path,
            'method': method.upper(),
            'parameters': parameters,
            'data': data,
            'headers': headers,
            })


class NoMiddlewareTestCase(BaseMiddlewareTestCase):
    def createAPI(self):
        middlewares = []
        return API('/', middlewares=middlewares)

    def test_that_no_middlewares_creates_valid_response(self):
        resp = self.call()
        self.assertEqual(resp.status, 200)


class TwoMiddlewaresTestCase(BaseMiddlewareTestCase):
    def createAPI(self):
        self.countmiddleware = CountMiddleware()
        middlewares = [
                self.countmiddleware,
                self.countmiddleware
                ]
        return API('/', middlewares=middlewares)

    def test_middlewares_returnig_none_does_not_change_response(self):
        resp = self.call()
        self.assertEqual(resp.status, 200)

    def test_both_middlewares_processed_request(self):
        self.call()
        self.assertEqual(self.countmiddleware.process_request_count, 2)

    def test_both_middlewares_processed_response(self):
        self.call()
        self.assertEqual(self.countmiddleware.process_response_count, 2)


class RequestProcessingBreakTestCase(BaseMiddlewareTestCase):
    def createAPI(self):
        self.countmiddleware = CountMiddleware()
        middlewares = [
                self.countmiddleware,
                BreakRequestMiddleware(),
                self.countmiddleware
                ]
        return API('/', middlewares=middlewares)

    def test_middleware_changes_response(self):
        resp = self.call()
        self.assertEqual(resp.status, 201)

    def test_one_middleware_processed_request(self):
        self.call()
        self.assertEqual(self.countmiddleware.process_request_count, 1)

    def test_both_middlewares_processed_response(self):
        self.call()
        self.assertEqual(self.countmiddleware.process_response_count, 2)


class MiddlewareResponseReplacingTestCase(BaseMiddlewareTestCase):
    def createAPI(self):
        self.countmiddleware = CountMiddleware()
        middlewares = [
                self.countmiddleware,
                ReplaceResponseMiddleware(),
                self.countmiddleware
                ]
        return API('/', middlewares=middlewares)

    def test_middleware_changes_response(self):
        resp = self.call()
        self.assertEqual(resp.status, 201)

    def test_one_middleware_processed_request(self):
        self.call()
        self.assertEqual(self.countmiddleware.process_request_count, 2)

    def test_both_middlewares_processed_response(self):
        self.call()
        self.assertEqual(self.countmiddleware.process_response_count, 2)


class MiddlewareResponseModyfingBreakTestCase(BaseMiddlewareTestCase):
    def createAPI(self):
        self.countmiddleware = CountMiddleware()
        middlewares = [
                self.countmiddleware,
                ModifyResponseMiddleware(),
                self.countmiddleware
                ]
        return API('/', middlewares=middlewares)

    def test_middleware_changes_response(self):
        resp = self.call()
        self.assertEqual(resp.status, 666)

    def test_one_middleware_processed_request(self):
        self.call()
        self.assertEqual(self.countmiddleware.process_request_count, 2)

    def test_both_middlewares_processed_response(self):
        self.call()
        self.assertEqual(self.countmiddleware.process_response_count, 2)
