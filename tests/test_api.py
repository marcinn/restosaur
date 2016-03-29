import unittest
from restosaur import API


class APITestCase(unittest.TestCase):
    pass


class APIPathsTestCase(APITestCase):
    def test_appending_slash_to_api_path(self):
        api = API('foo')
        self.assertEqual(api.path, 'foo/')

    def test_not_appending_slash_to_api_path_if_exists(self):
        api = API('foo/')
        self.assertEqual(api.path, 'foo/')

    def test_that_root_url_pattern_does_not_contain_slash(self):
        api = API('foo')
        root = api.resource('/')
        urls = api.get_urls()
        root_url = urls[0].url_patterns[0]
        self.assertFalse('/' in root_url._regex)

    def test_that_typical_url_pattern_does_not_contain_prepending_slash(self):
        api = API('foo')
        bar = api.resource('bar/')
        urls = api.get_urls()
        bar_url = urls[0].url_patterns[0]
        self.assertEqual(bar_url._regex, '^bar/$')

