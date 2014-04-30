# -*- coding: utf-8 -*-

import unittest

from pyramid import testing


class TestConnection(unittest.TestCase):
    def setUp(self):
        testing.setUp(self)
        self.request = testing.DummyRequest()

    def tearDown(self):
        testing.tearDown(self)

    def test_get_default_connection(self):
        from . import DummyRedis
        from ..connection import get_default_connection
        options = dict(host='localhost',port=999)
        inst = get_default_connection(self.request,
                                      redis_client=DummyRedis,
                                      **options)
        self.assertEqual(inst.host, 'localhost')
        self.assertEqual(inst.port, 999)

    def test_get_default_connection_with_url(self):
        from . import DummyRedis
        from ..connection import get_default_connection
        url = 'redis://username:password@localhost:6379/0'
        inst = get_default_connection(self.request,
                                      url=url,
                                      redis_client=DummyRedis)
        self.assertEqual(inst.url, url)

    def test_get_default_connection_url_removes_duplicates(self):
        from . import DummyRedis
        from ..connection import get_default_connection
        options = dict(host='localhost', port=999, password='password', db=5)
        url = 'redis://username:password@localhost:6379/0'
        inst = get_default_connection(self.request,
                                      url=url,
                                      redis_client=DummyRedis,
                                      **options)
        self.assertEqual(inst.url, url)
        self.assertNotIn('password', inst.opts)
        self.assertNotIn('host', inst.opts)
        self.assertNotIn('port', inst.opts)
        self.assertNotIn('db', inst.opts)
