# -*- coding: utf-8 -*-

import unittest
from pyramid import testing

from ..compat import cPickle

from . import DummyRedis

class TestRedisSessionFactory(unittest.TestCase):
    def _makeOne(self, request, secret='secret', **kw):
        from .. import RedisSessionFactory
        return RedisSessionFactory(secret, **kw)(request)

    def _get_session_id(self, request):
        from ..util import get_unique_session_id
        redis = request.registry._redis_sessions
        session_id = get_unique_session_id(redis, timeout=100,
                                           serialize=cPickle.dumps)
        return session_id

    def _serialize(self, session_id, secret='secret'):
        from pyramid.session import signed_serialize
        return signed_serialize(session_id, secret)

    def _make_request(self):
        request = testing.DummyRequest()
        request.registry._redis_sessions = DummyRedis()
        return request

    def test_ctor_no_cookie(self):
        request = self._make_request()
        session = self._makeOne(request)
        self.assertEqual(session.from_redis(), {})

    def test_ctor_with_cookie_still_valid(self):
        request = self._make_request()
        session_id = self._get_session_id(request)
        cookieval = self._serialize(session_id)
        request.cookies['session'] = cookieval
        session = self._makeOne(request)
        self.assertEqual(session.session_id, session_id)

    def test_ctor_with_bad_cookie(self):
        from pyramid.session import signed_deserialize
        request = self._make_request()
        session_id = self._get_session_id(request)
        invalid_secret = 'aaaaaa'
        cookieval = self._serialize(session_id, secret=invalid_secret)
        request.cookies['session'] = cookieval
        session = self._makeOne(request)
        deserialized_cookie = signed_deserialize(cookieval, invalid_secret)
        self.assertNotEqual(deserialized_cookie, session.session_id)

    def test_cookie_on_exception_false_with_exception(self):
        import webob
        request = self._make_request()
        request.exception = True
        self._makeOne(request, cookie_on_exception=False)
        callbacks = request.response_callbacks
        response = webob.Response()
        callbacks[0](request, response)
        self.assertNotEqual(response.headerlist[-1][0], 'Set-Cookie')

    def test_cookie_on_exception_false_no_exception(self):
        import webob
        request = self._make_request()
        request.exception = None
        self._makeOne(request, cookie_on_exception=False)
        callbacks = request.response_callbacks
        response = webob.Response()
        callbacks[0](request, response)
        self.assertEqual(response.headerlist[-1][0], 'Set-Cookie')

    def test_cookie_callback(self):
        import webob
        request = self._make_request()
        self._makeOne(request)
        callbacks = request.response_callbacks
        response = webob.Response()
        callbacks[0](request, response)
        self.assertEqual(response.headerlist[-1][0], 'Set-Cookie')

    def test_delete_cookie(self):
        import webob
        request = self._make_request()
        session = self._makeOne(request)
        session.delete_cookie()
        response = webob.Response()
        request.response_callbacks[1](request, response)
        self.assertIn('Max-Age=0', response.headers['Set-Cookie'])

    def test_session_id_not_in_redis(self):
        request = self._make_request()
        session_id = self._get_session_id(request)
        cookieval = self._serialize(session_id)
        request.cookies['session'] = cookieval
        redis = request.registry._redis_sessions
        redis.store = {} # clears keys in DummyRedis
        session = self._makeOne(request)
        self.assertNotEqual(session.session_id, session_id)

    def test_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import ISession
        request = self._make_request()
        inst = self._makeOne(request)
        verifyObject(ISession, inst)

    def test_adjusted_session_timeout_persists(self):
        request = self._make_request()
        inst = self._makeOne(request)
        inst.adjust_timeout_for_session(555)
        session_id = inst.session_id
        cookieval = self._serialize(session_id)
        request.cookies['session'] = cookieval
        new_session = self._makeOne(request)
        self.assertEqual(new_session.timeout, 555)

    def test_client_callable(self):
        request = self._make_request()
        redis = DummyRedis()
        client_callable = lambda req, **kw: redis
        inst = self._makeOne(request, client_callable=client_callable)
        self.assertEqual(inst.redis, redis)

    def test_session_factory_from_settings(self):
        from .. import session_factory_from_settings
        request = self._make_request()
        settings = {'redis.sessions.secret': 'secret',
                    'redis.sessions.timeout': '999'}
        inst = session_factory_from_settings(settings)(request)
        self.assertEqual(inst.default_timeout, 999)
