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
            'redis.sessions.cookie_secure' : 'false',
            'redis.sessions.host'          : 'localhost',
            'redis.sessions.port'          : '1234',
            'ignore.this.setting'         : '',
            }
        return settings

    def test_it(self):
        settings = self._makeSettings()
        inst = self._makeOne(settings)
        self.assertEqual(False, inst['cookie_secure'])
        self.assertEqual('localhost', inst['host'])
        self.assertEqual(1234, inst['port'])
        self.assertNotIn('ignore.this.setting', inst)


class Test__insert_session_id_if_unique(unittest.TestCase):
    def _makeOne(self, redis, timeout=1, session_id='id', encoder=lambda x: x):
        from ..util import _insert_session_id_if_unique
        return _insert_session_id_if_unique(redis, timeout, session_id, encoder)

    def test_id_is_unique(self):
        redis = DummyRedis()
        result = self._makeOne(redis)
        self.assertEqual(result, 'id')

    def test_id_not_unique(self):
        redis = DummyRedis()
        redis.set('id', '')
        result = self._makeOne(redis)
        self.assertEqual(result, None)

    def test_watcherror_returns_none(self):
        redis = DummyRedis(raise_watcherror=True)
        result = self._makeOne(redis)
        self.assertEqual(result, None)


class Test_get_unique_session_id(unittest.TestCase):
    def _makeGenerator(self):
        global x
        x = 0
        def gen():
            global x
            x += 1
            return x
        return gen

    def _makeOne(self, redis=DummyRedis(), timeout=300):
        from ..util import get_unique_session_id
        generator = self._makeGenerator()
        return get_unique_session_id(redis, timeout, generator=generator)

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
        self.assertEqual(len(result), 40)


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

