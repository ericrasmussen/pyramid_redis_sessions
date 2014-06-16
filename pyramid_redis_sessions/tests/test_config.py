# -*- coding: utf-8 -*-

import unittest

from pyramid import testing
from pyramid.threadlocal import get_current_request


# dotted paths to dummy callables
_id_path = 'pyramid_redis_sessions.tests.test_config.dummy_id_generator'
_client_path ='pyramid_redis_sessions.tests.test_config.dummy_client_callable'


class Test_includeme(unittest.TestCase):
    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request=request)
        self.config.registry.settings = {
            'redis.sessions.secret': 'supersecret',
            'redis.sessions.db': 9,
            'redis.sessions.serialize': 'pickle.dumps',
            'redis.sessions.deserialize': 'pickle.loads',
            'redis.sessions.id_generator': _id_path,
            'redis.sessions.client_callable': _client_path,
        }
        self.config.include('pyramid_redis_sessions')
        self.settings = self.config.registry.settings

    def tearDown(self):
        testing.tearDown()

    def test_includeme_serialize_deserialize(self):
        request = get_current_request()
        serialize = self.settings['redis.sessions.serialize']
        deserialize = self.settings['redis.sessions.deserialize']
        result = deserialize(serialize('test'))
        self.assertEqual(result, 'test')

    def test_includeme_id_generator(self):
        request = get_current_request()
        generator = self.settings['redis.sessions.id_generator']
        self.assertEqual(generator(), 42)

    def test_includeme_client_callable(self):
        request = get_current_request()
        get_client = self.settings['redis.sessions.client_callable']
        self.assertEqual(get_client(request), 'client')


# used to ensure includeme can resolve a dotted path to an id generator
def dummy_id_generator():
    return 42

# used to ensure includeme can resolve a dotted path to a redis client callable
def dummy_client_callable(request, **opts):
    return 'client'
