# -*- coding: utf-8 -*-

import itertools
import time
import unittest

from . import (
    DummyRedis,
    DummySession,
    )


class Test_parse_settings(unittest.TestCase):
    def _makeOne(self, settings):
        from ..util import _parse_settings
        return _parse_settings(settings)

    def _makeSettings(self):
        settings = {
            'redis.sessions.secret'        : 'mysecret',
            'redis.sessions.cookie_secure' : 'false',
            'redis.sessions.host'          : 'localhost',
            'redis.sessions.port'          : '1234',
            'redis.sessions.socket_timeout': '1234',
            'ignore.this.setting'          : '',
            }
        return settings

    def test_it(self):
        settings = self._makeSettings()
        inst = self._makeOne(settings)
        self.assertEqual(False, inst['cookie_secure'])
        self.assertEqual('localhost', inst['host'])
        self.assertEqual(1234, inst['port'])
        self.assertEqual(1234.0, inst['socket_timeout'])
        self.assertNotIn('ignore.this.setting', inst)

    def test_minimal_configuration(self):
        settings = { 'redis.sessions.secret': 'mysecret' }
        inst = self._makeOne(settings)
        self.assertEqual('mysecret', inst['secret'])

    def test_no_secret_raises_error(self):
        from pyramid.exceptions import ConfigurationError
        settings = {}
        self.assertRaises(ConfigurationError, self._makeOne, settings)

    def test_prefix_and_generator_raises_error(self):
        from pyramid.exceptions import ConfigurationError
        settings = {'redis.sessions.secret': 'test',
                    'redis.sessions.prefix': 'test',
                    'redis.sessions.id_generator': 'test'}
        self.assertRaises(ConfigurationError, self._makeOne, settings)

    def test_prefix_in_options(self):
        settings = {'redis.sessions.secret': 'test',
                    'redis.sessions.prefix': 'testprefix'}
        inst = self._makeOne(settings)
        implicit_generator = inst['id_generator']
        self.assertIn('testprefix', implicit_generator())


class Test__insert_session_id_if_unique(unittest.TestCase):
    def _makeOne(self, redis, timeout=1, session_id='id',
                 serialize=lambda x: x):
        from ..util import _insert_session_id_if_unique
        return _insert_session_id_if_unique(redis, timeout, session_id,
                                            serialize)

    def test_id_is_unique(self):
        redis = DummyRedis()
        before = time.time()
        result = self._makeOne(redis)
        after = time.time()
        persisted = redis.get('id')
        managed_dict = persisted['managed_dict']
        created = persisted['created']
        timeout = persisted['timeout']
        self.assertDictEqual(managed_dict, {})
        self.assertGreaterEqual(created, before)
        self.assertLessEqual(created, after)
        self.assertEqual(timeout, 1)
        self.assertEqual(result, 'id')

    def test_id_not_unique(self):
        redis = DummyRedis()
        original_value = object()
        redis.set('id', original_value)
        result = self._makeOne(redis)
        # assert value under key has not been changed
        self.assertEqual(redis.get('id'), original_value)
        self.assertEqual(result, None)

    def test_watcherror_returns_none(self):
        redis = DummyRedis(raise_watcherror=True)
        result = self._makeOne(redis)
        self.assertIs(redis.get('id'), None)
        self.assertEqual(result, None)


class Test_get_unique_session_id(unittest.TestCase):
    def _makeOne(self, redis=DummyRedis(), timeout=300):
        from ..util import get_unique_session_id
        serialize = lambda x: x
        ids = itertools.count(start=1, step=1)
        generator = lambda: next(ids)
        return get_unique_session_id(redis, timeout, serialize,
                                     generator=generator)

    def test_id_is_unique(self):
        result = self._makeOne()
        self.assertEqual(result, 1)

    def test_id_not_unique(self):
        redis = DummyRedis()
        redis.set(1, '')
        result = self._makeOne(redis)
        self.assertEqual(result, 2)


class Test__generate_session_id(unittest.TestCase):
    def _makeOne(self):
        from ..util import _generate_session_id
        return _generate_session_id

    def test_it(self):
        inst = self._makeOne()
        result = inst()
        self.assertEqual(len(result), 64)

class Test_prefixed_id(unittest.TestCase):
    def _makeOne(self):
        from ..util import prefixed_id
        return prefixed_id

    def test_it(self):
        inst = self._makeOne()
        result = inst('prefix')
        self.assertEqual(len(result), 70)
        self.assertEqual(result[:6], 'prefix')


class Test_persist_decorator(unittest.TestCase):
    def _makeOne(self, wrapped):
        from ..util import persist
        return persist(wrapped)

    def _makeSession(self, timeout):
        redis = DummyRedis()
        session_id = 'session.session_id'
        redis.timeouts[session_id] = timeout
        session = DummySession(session_id, redis, timeout)
        return session

    def test_it(self):
        def wrapped(session, *arg, **kwarg):
            return 'expected result'
        inst = self._makeOne(wrapped)
        timeout = 300
        session = self._makeSession(timeout)
        result = inst(session)
        ttl = session.redis.ttl(session.session_id)
        self.assertEqual(result, 'expected result')
        self.assertEqual(timeout, ttl)


class Test_refresh_decorator(unittest.TestCase):
    def _makeOne(self, wrapped):
        from ..util import refresh
        return refresh(wrapped)

    def _makeSession(self, timeout):
        redis = DummyRedis()
        session_id = 'session.session_id'
        redis.timeouts[session_id] = timeout
        session = DummySession(session_id, redis, timeout)
        return session

    def test_it(self):
        def wrapped(session, *arg, **kwarg):
            return 'expected result'
        inst = self._makeOne(wrapped)
        timeout = 300
        session = self._makeSession(timeout)
        result = inst(session)
        ttl = session.redis.ttl(session.session_id)
        self.assertEqual(result, 'expected result')
        self.assertEqual(timeout, ttl)

