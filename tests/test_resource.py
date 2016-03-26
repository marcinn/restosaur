import unittest
import datetime

from restosaur import API, responses
from restosaur.resource import Resource
from restosaur.dispatch import resource_dispatcher_factory


class ResourceTestCase(unittest.TestCase):
    def setUp(self):
        from django.test import RequestFactory

        super(ResourceTestCase, self).setUp()

        self.api = API('/')
        self.rqfactory = RequestFactory()

    def call(self, resource, method, *args, **kw):
        rq = getattr(self.rqfactory, method)(resource.path, *args, **kw)
        return resource_dispatcher_factory(self.api, resource)(rq)


class DefaultRepresentationTestCase(ResourceTestCase):
    def setUp(self):
        super(DefaultRepresentationTestCase, self).setUp()

        self.entity = self.api.resource('entity')

        @self.entity.get()
        def entity_GET(ctx):
            return ctx.Entity({'some':'test'})

    def test_successful_getting_200_status_code(self):
        resp = self.call(self.entity, 'get')
        self.assertEqual(resp.status_code, 200)

    def test_returning_valid_content_type(self):
        resp = self.call(self.entity, 'get')
        self.assertEqual(resp['Content-Type'], 'application/json')

    def test_getting_valid_entity_content(self):
        resp = self.call(self.entity, 'get')
        import json
        resp_json = json.loads(resp.content)
        self.assertTrue(resp_json['some'] == 'test')

    def test_raising_not_acceptable_for_unsupported_representation(self):
        resp = self.call(self.entity, 'get', HTTP_ACCEPT='application/vnd.not-defined+json')
        self.assertEqual(resp.status_code, 406)

    def test_raising_not_acceptable_for_unsupported_serializer(self):
        resp = self.call(self.entity, 'get', HTTP_ACCEPT='application/eggsandmeat')
        self.assertEqual(resp.status_code, 406)

    def test_returning_fallback_application_json_content_type_for_unsupported_serializer(self):
        resp = self.call(self.entity, 'get', HTTP_ACCEPT='application/eggsandmeat')
        self.assertEqual(resp['Content-Type'], 'application/json')


class SeeOtherTestCase(ResourceTestCase):
    def setUp(self):
        super(SeeOtherTestCase, self).setUp()

        self.seeother = self.api.resource('seeother')

        @self.seeother.get()
        def seeother_GET(ctx):
            return ctx.SeeOther('https://google.com')

    def test_that_seeother_accepts_any_content_type(self):
        resp = self.call(self.seeother, 'get', HTTP_ACCEPT='application/vnd.not-defined+json')
        self.assertEqual(resp.status_code, 303)

    def test_that_seeother_sends_back_location_header(self):
        resp = self.call(self.seeother, 'get')
        self.assertEqual(resp['Location'], 'https://google.com')

    def test_that_seeother_returns_no_content(self):
        resp = self.call(self.seeother, 'get')
        self.assertEqual(resp.content, '')

    def test_that_seeother_returns_application_json_content_type(self):
        resp = self.call(self.seeother, 'get')
        self.assertEqual(resp['Content-Type'], 'application/json')


class NotFoundTestCase(ResourceTestCase):
    def setUp(self):
        super(NotFoundTestCase, self).setUp()

        self.resource_exc = self.api.resource('notfound_exc')
        self.resource = self.api.resource('notfound')

        @self.resource.get()
        def notfound_GET(ctx):
            return ctx.NotFound()

        @self.resource_exc.get()
        def notfoundexc_GET(ctx):
            from django.http import Http404
            raise Http404

    def test_returning_404_code_when_handling_django_Http404_exception_and(self):
        resp = self.call(self.resource_exc, 'get')
        self.assertEqual(resp.status_code, 404)

    def test_valid_content_type_when_handling_django_Http404_exception_and(self):
        resp = self.call(self.resource_exc, 'get')
        self.assertEqual(resp['Content-Type'], 'application/json')

    def test_returning_404_code_when_returning_NotFoundResponse(self):
        resp = self.call(self.resource, 'get')
        self.assertEqual(resp.status_code, 404)

    def test_valid_content_type_when_returning_NotFoundResponse(self):
        resp = self.call(self.resource, 'get')
        self.assertEqual(resp['Content-Type'], 'application/json')


class MethodNotAllowedTestCase(ResourceTestCase):
    def setUp(self):
        super(MethodNotAllowedTestCase, self).setUp()
        self.empty_resource = self.api.resource('empty')

    def test_that_empty_resource_raises_method_not_allowed_for_GET(self):
        resp = self.call(self.empty_resource, 'get')
        self.assertEqual(resp.status_code, 405)

    def test_that_empty_resource_raises_method_not_allowed_for_POST(self):
        resp = self.call(self.empty_resource, 'post')
        self.assertEqual(resp.status_code, 405)

    def test_that_empty_resource_raises_method_not_allowed_for_PUT(self):
        resp = self.call(self.empty_resource, 'put')
        self.assertEqual(resp.status_code, 405)

    def test_that_empty_resource_raises_method_not_allowed_for_PATCH(self):
        resp = self.call(self.empty_resource, 'patch')
        self.assertEqual(resp.status_code, 405)

    def test_that_empty_resource_raises_method_not_allowed_for_DELETE(self):
        resp = self.call(self.empty_resource, 'delete')
        self.assertEqual(resp.status_code, 405)

    def test_that_empty_resource_raises_method_not_allowed_for_OPTIONS(self):
        resp = self.call(self.empty_resource, 'options')
        self.assertEqual(resp.status_code, 405)


class MethodsHandlingTestCase(ResourceTestCase):
    def setUp(self):
        super(MethodsHandlingTestCase, self).setUp()
        self.get = self.api.resource('get')
        self.post = self.api.resource('post')
        self.delete = self.api.resource('delete')
        self.patch = self.api.resource('patch')
        self.put = self.api.resource('put')
        self.options = self.api.resource('options')

        @self.post.post()
        @self.get.get()
        @self.patch.patch()
        @self.put.put()
        @self.options.options()
        def response_200_OK(ctx):
            return ctx.Response()

    def test_succesful_handling_registered_GET(self):
        resp = self.call(self.get, 'get')
        self.assertEqual(resp.status_code, 200)

    def test_succesful_handling_registered_POST(self):
        resp = self.call(self.post, 'post')
        self.assertEqual(resp.status_code, 200)

    def test_succesful_handling_registered_PUT(self):
        resp = self.call(self.put, 'put')
        self.assertEqual(resp.status_code, 200)

    def test_succesful_handling_registered_PATCH(self):
        resp = self.call(self.patch, 'patch')
        self.assertEqual(resp.status_code, 200)

    def test_succesful_handling_registered_OPTIONS(self):
        resp = self.call(self.options, 'options')
        self.assertEqual(resp.status_code, 200)

    def test_not_handling_notregistered_POST(self):
        for resource in (self.get, self.put, self.patch, self.options):
            resp = self.call(resource, 'post')
            self.assertEqual(resp.status_code, 405)

    def test_not_handling_notregistered_PUT(self):
        for resource in (self.get, self.post, self.patch, self.options):
            resp = self.call(resource, 'put')
            self.assertEqual(resp.status_code, 405)

    def test_not_handling_notregistered_GET(self):
        for resource in (self.put, self.post, self.patch, self.options):
            resp = self.call(resource, 'get')
            self.assertEqual(resp.status_code, 405)

    def test_not_handling_notregistered_PATCH(self):
        for resource in (self.put, self.post, self.get, self.options):
            resp = self.call(resource, 'patch')
            self.assertEqual(resp.status_code, 405)

    def test_not_handling_notregistered_OPTIONS(self):
        for resource in (self.put, self.post, self.get, self.patch):
            resp = self.call(resource, 'options')
        self.assertEqual(resp.status_code, 405)

