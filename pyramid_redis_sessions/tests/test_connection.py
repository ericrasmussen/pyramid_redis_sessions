import unittest
from pyramid import testing

from . import DummyRedis

class TestConnection(unittest.TestCase):

    def setUp(self):
        testing.setUp(self)
        self.request = testing.DummyRequest()

    def tearDown(self):
        testing.tearDown(self)

    def test_get_default_connection(self):
        from ..connection import get_default_connection
        options = dict(host='localhost',port=999)
        inst = get_default_connection(self.request,
                                      redis_connect=DummyRedis,
                                      **options)
        self.assertEqual(inst.host, 'localhost')
        self.assertEqual(inst.port, 999)

    def test_get_default_connection_with_url(self):
        from ..connection import get_default_connection
        url = 'redis://username:password@localhost:6379/0'
        inst = get_default_connection(self.request,
                                      url=url,
                                      redis_connect=DummyRedis)
        self.assertEqual(inst.url, url)

