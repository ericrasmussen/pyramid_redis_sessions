# -*- coding: utf-8 -*-

import unittest

from pyramid import testing


class TestRedisSessionFactory(unittest.TestCase):
    def _makeOne(self, request, secret='secret', **kw):
        from .. import RedisSessionFactory
        return RedisSessionFactory(secret, **kw)(request)

    def _get_session_id(self, request):
        from ..compat import cPickle
        from ..util import get_unique_session_id
        redis = request.registry._redis_sessions
        session_id = get_unique_session_id(redis, timeout=100,
                                           serialize=cPickle.dumps)
        return session_id

    def _serialize(self, session_id, secret='secret'):
        from pyramid.session import signed_serialize
        return signed_serialize(session_id, secret)

    def _set_session_cookie(self, request, session_id, secret='secret'):
        cookieval = self._serialize(session_id, secret=secret)
        request.cookies['session'] = cookieval

    def _make_request(self):
        from . import DummyRedis
        request = testing.DummyRequest()
        request.registry._redis_sessions = DummyRedis()
        request.exception = None
        return request

    def test_ctor_no_cookie(self):
        request = self._make_request()
        session = self._makeOne(request)
        session_dict = session.from_redis()['managed_dict']
        self.assertDictEqual(session_dict, {})
        self.assertIs(session.new, True)

    def test_ctor_with_cookie_still_valid(self):
        request = self._make_request()
        session_id_in_cookie = self._get_session_id(request)
        self._set_session_cookie(request=request,
                                 session_id=session_id_in_cookie)
        session = self._makeOne(request)
        self.assertEqual(session.session_id, session_id_in_cookie)
        self.assertIs(session.new, False)

    def test_ctor_with_bad_cookie(self):
        request = self._make_request()
        session_id_in_cookie = self._get_session_id(request)
        invalid_secret = 'aaaaaa'
        self._set_session_cookie(request=request,
                                 session_id=session_id_in_cookie,
                                 secret=invalid_secret)
        session = self._makeOne(request)
        self.assertNotEqual(session.session_id, session_id_in_cookie)
        self.assertIs(session.new, True)

    def test_session_id_not_in_redis(self):
        request = self._make_request()
        session_id_in_cookie = self._get_session_id(request)
        self._set_session_cookie(request=request,
                                 session_id=session_id_in_cookie)
        redis = request.registry._redis_sessions
        redis.store = {}  # clears keys in DummyRedis
        session = self._makeOne(request)
        self.assertNotEqual(session.session_id, session_id_in_cookie)
        self.assertIs(session.new, True)

    # The tests below with names beginning with test_new_session_ test cases
    # where first access to request.session creates a new session, as in
    # test_ctor_no_cookie, test_ctor_with_bad_cookie and
    # test_session_id_not_in_redis.

    def test_new_session_cookie_on_exception_true_no_exception(self):
        # cookie_on_exception is True by default, no exception raised
        import webob
        request = self._make_request()
        request.session = self._makeOne(request)
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn(self._serialize(request.session.session_id),
                      set_cookie_headers[0])

    def test_new_session_cookie_on_exception_true_exception(self):
        # cookie_on_exception is True by default, exception raised
        import webob
        request = self._make_request()
        request.session = self._makeOne(request)
        request.exception = Exception()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn(self._serialize(request.session.session_id),
                      set_cookie_headers[0])

    def test_new_session_cookie_on_exception_false_no_exception(self):
        # cookie_on_exception is False, no exception raised
        import webob
        request = self._make_request()
        request.session = self._makeOne(request, cookie_on_exception=False)
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn(self._serialize(request.session.session_id),
                      set_cookie_headers[0])

    def test_new_session_cookie_on_exception_false_exception(self):
        # cookie_on_exception is False, exception raised
        import webob
        request = self._make_request()
        request.session = self._makeOne(request, cookie_on_exception=False)
        request.exception = Exception()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        self.assertNotIn('Set-Cookie', response.headers)

    def test_new_session_invalidate(self):
        # new session -> invalidate()
        import webob
        request = self._make_request()
        request.session = self._makeOne(request)
        request.session.invalidate()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        self.assertNotIn('Set-Cookie', response.headers)

    def test_new_session_session_after_invalidate_coe_True_no_exception(self):
        # new session -> invalidate() -> new session
        # cookie_on_exception is True by default, no exception raised
        import webob
        request = self._make_request()
        session = request.session = self._makeOne(request)
        session.invalidate()
        session['key'] = 'value'
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn(self._serialize(request.session.session_id),
                      set_cookie_headers[0])

    def test_new_session_session_after_invalidate_coe_True_exception(self):
        # new session -> invalidate() -> new session
        # cookie_on_exception is True by default, exception raised
        import webob
        request = self._make_request()
        session = request.session = self._makeOne(request)
        session.invalidate()
        session['key'] = 'value'
        request.exception = Exception()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn(self._serialize(request.session.session_id),
                      set_cookie_headers[0])

    def test_new_session_session_after_invalidate_coe_False_no_exception(self):
        # new session -> invalidate() -> new session
        # cookie_on_exception is False, no exception raised
        import webob
        request = self._make_request()
        session = request.session = self._makeOne(request,
                                                  cookie_on_exception=False)
        session.invalidate()
        session['key'] = 'value'
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn(self._serialize(request.session.session_id),
                      set_cookie_headers[0])

    def test_new_session_session_after_invalidate_coe_False_exception(self):
        # new session -> invalidate() -> new session
        # cookie_on_exception is False, exception raised
        import webob
        request = self._make_request()
        session = request.session = self._makeOne(request,
                                                  cookie_on_exception=False)
        session.invalidate()
        session['key'] = 'value'
        request.exception = Exception()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        self.assertNotIn('Set-Cookie', response.headers)

    def test_new_session_multiple_invalidates(self):
        # new session -> invalidate() -> new session -> invalidate()
        # Invalidate more than once, no new session after last invalidate()
        import webob
        request = self._make_request()
        session = request.session = self._makeOne(request)
        session.invalidate()
        session['key'] = 'value'
        session.invalidate()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        self.assertNotIn('Set-Cookie', response.headers)

    def test_new_session_multiple_invalidates_with_no_new_session_in_between(
        self
        ):
        # new session -> invalidate() -> invalidate()
        # Invalidate more than once, no new session in between invalidate()s,
        # no new session after last invalidate()
        import webob
        request = self._make_request()
        session = request.session = self._makeOne(request)
        session.invalidate()
        session.invalidate()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        self.assertNotIn('Set-Cookie', response.headers)

    # The tests below with names beginning with test_existing_session_ test
    # cases where first access to request.session returns an existing session,
    # as in test_ctor_with_cookie_still_valid.

    def test_existing_session(self):
        import webob
        request = self._make_request()
        self._set_session_cookie(
            request=request,
            session_id=self._get_session_id(request),
            )
        request.session = self._makeOne(request)
        response = webob.Response()
        request.response_callbacks[0](request, response)
        self.assertNotIn('Set-Cookie', response.headers)

    def test_existing_session_invalidate(self):
        # existing session -> invalidate()
        import webob
        request = self._make_request()
        self._set_session_cookie(request=request,
                                 session_id=self._get_session_id(request))
        request.session = self._makeOne(request)
        request.session.invalidate()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn('Max-Age=0', set_cookie_headers[0])

    def test_existing_session_session_after_invalidate_coe_True_no_exception(
        self
        ):
        # existing session -> invalidate() -> new session
        # cookie_on_exception is True by default, no exception raised
        import webob
        request = self._make_request()
        self._set_session_cookie(request=request,
                                 session_id=self._get_session_id(request))
        session = request.session = self._makeOne(request)
        session.invalidate()
        session['key'] = 'value'
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn(self._serialize(request.session.session_id),
                      set_cookie_headers[0])

    def test_existing_session_session_after_invalidate_coe_True_exception(
        self
        ):
        # existing session -> invalidate() -> new session
        # cookie_on_exception is True by default, exception raised
        import webob
        request = self._make_request()
        self._set_session_cookie(request=request,
                                 session_id=self._get_session_id(request))
        session = request.session = self._makeOne(request)
        session.invalidate()
        session['key'] = 'value'
        request.exception = Exception()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn(self._serialize(request.session.session_id),
                      set_cookie_headers[0])

    def test_existing_session_session_after_invalidate_coe_False_no_exception(
        self
        ):
        # existing session -> invalidate() -> new session
        # cookie_on_exception is False, no exception raised
        import webob
        request = self._make_request()
        self._set_session_cookie(request=request,
                                 session_id=self._get_session_id(request))
        session = request.session = self._makeOne(request,
                                                  cookie_on_exception=False)
        session.invalidate()
        session['key'] = 'value'
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn(self._serialize(request.session.session_id),
                      set_cookie_headers[0])

    def test_existing_session_session_after_invalidate_coe_False_exception(
        self
        ):
        # existing session -> invalidate() -> new session
        # cookie_on_exception is False, exception raised
        import webob
        request = self._make_request()
        self._set_session_cookie(request=request,
                                 session_id=self._get_session_id(request))
        session = request.session = self._makeOne(request,
                                                  cookie_on_exception=False)
        session.invalidate()
        session['key'] = 'value'
        request.exception = Exception()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn('Max-Age=0', set_cookie_headers[0])
        # Cancel setting of cookie for new session, but still delete cookie for
        # the earlier invalidate().

    def test_existing_session_multiple_invalidates(self):
        # existing session -> invalidate() -> new session -> invalidate()
        # Invalidate more than once, no new session after last invalidate()
        import webob
        request = self._make_request()
        self._set_session_cookie(request=request,
                                 session_id=self._get_session_id(request))
        session = request.session = self._makeOne(request)
        session.invalidate()
        session['key'] = 'value'
        session.invalidate()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn('Max-Age=0', set_cookie_headers[0])

    def test_existing_session_multiple_invalidates_no_new_session_in_between(
        self
        ):
        # existing session -> invalidate() -> invalidate()
        # Invalidate more than once, no new session in between invalidate()s,
        # no new session after last invalidate()
        import webob
        request = self._make_request()
        self._set_session_cookie(request=request,
                                 session_id=self._get_session_id(request))
        session = request.session = self._makeOne(request)
        session.invalidate()
        session.invalidate()
        response = webob.Response()
        request.response_callbacks[0](request, response)
        set_cookie_headers = response.headers.getall('Set-Cookie')
        self.assertEqual(len(set_cookie_headers), 1)
        self.assertIn('Max-Age=0', set_cookie_headers[0])

    def test_instance_conforms(self):
        from pyramid.interfaces import ISession
        from zope.interface.verify import verifyObject
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
        from . import DummyRedis
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
