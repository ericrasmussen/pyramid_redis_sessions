import unittest
from pyramid import testing

class TestUniqueSessionIdInserts(unittest.TestCase):
    def get_client(self, redis=None):
        if redis is None:
            from redis import Redis
        return Redis(db=9)

    def make_key(self, generator=None):
        if generator is None:
            from pyramid_redis_sessions import _generate_session_id
            generator =  _generate_session_id
        return generator()

    def setUp(self):
        self.client = self.get_client()
        self.client.flushdb()
        self.timeout = 1200

    def tearDown(self):
        self.client.flushdb()
        self.client.connection_pool.disconnect()

    def test_fresh_key(self):
        from pyramid_redis_sessions import _insert_session_id_if_unique
        key = self.make_key()
        attempt = _insert_session_id_if_unique(self.client, self.timeout, key)
        self.assert_(attempt is not None, 'inserting new key in empty Redis')

    def test_duplicate_key_fails(self):
        from pyramid_redis_sessions import _insert_session_id_if_unique
        key = self.make_key()
        attempt = _insert_session_id_if_unique(self.client, self.timeout, key)
        attempt2 = _insert_session_id_if_unique(self.client, self.timeout, key)
        self.assertEquals(attempt2, None)

class TestSessionFactoryFromSettings(unittest.TestCase):
    def make_test_settings(self):
        settings = dict(
            secret='secret',
            host='localhost',
            cookie_domain='False',
            port=6379,
            db=9,
            charset='utf-8',
            errors='strict',
            )
        return settings

    def add_prefix(self, prefix, settings):
        new = {}
        for key, value in settings.items():
            prefixed = '%s%s' % (prefix, key)
            new[prefixed] = value
        return new

    def setUp(self):
        from pyramid_redis_sessions import session_factory_from_settings
        self.mock_settings = self.make_test_settings()
        self.make_factory = session_factory_from_settings
        self.request = testing.DummyRequest()

    def tearDown(self):
        pass

    def test_redis_prefix(self):
        prefix = 'redis.'
        prefixed = self.add_prefix(prefix, self.mock_settings)
        factory = self.make_factory(prefixed)
        session = factory(self.request)
        for key, value in self.mock_settings.items():
            if hasattr(session.redis, key):
                actual_value = getattr(session.redis, key)
                self.assertEquals(actual_value, value)

    def test_redis__sessions_prefix(self):
        prefix = 'redis.session.'
        prefixed = self.add_prefix(prefix, self.mock_settings)
        factory = self.make_factory(prefixed)
        session = factory(self.request)
        for key, value in self.mock_settings.items():
            if hasattr(session.redis, key):
                actual_value = getattr(session.redis, key)
                self.assertEquals(actual_value, value)

class TestCookieHandling(unittest.TestCase):
   def _makeOne(self, request, secret='secret', **kw):
       from pyramid_redis_sessions import RedisSessionFactory
       return RedisSessionFactory(secret, **kw)(request)

   def test_ctor_no_cookie(self):
       request = testing.DummyRequest()
       session = self._makeOne(request)
       self.assertEqual(session._deserialize_dict(), {})

   def test_instance_conforms(self):
       from zope.interface.verify import verifyObject
       from pyramid.interfaces import ISession
       request = testing.DummyRequest()
       session = self._makeOne(request)
       verifyObject(ISession, session)

   def _serialize(self, session_id='session_test', secret='secret'):
       from pyramid.session import signed_serialize
       return signed_serialize(session_id, secret)

   def test_ctor_with_cookie_still_valid(self):
       import time
       request = testing.DummyRequest()
       cookieval = self._serialize()
       request.cookies['session'] = cookieval
       session = self._makeOne(request)
       self.assertEqual(session.session_id, 'session_test')

   def test_ctor_with_bad_cookie(self):
       request = testing.DummyRequest()
       invalid_secret = 'aaaaaa'
       cookieval = self._serialize(secret=invalid_secret)
       request.cookies['session'] = cookieval
       session = self._makeOne(request)
       from pyramid.session import signed_deserialize
       deserialized_cookie = signed_deserialize(cookieval, invalid_secret)
       self.assert_(deserialized_cookie is not session.session_id)

   def test_set_cookie_on_exception(self):
       import webob
       request = testing.DummyRequest()
       request.exception = True
       session = self._makeOne(request, cookie_on_exception=False)
       response = webob.Response()
       self.assert_(response.headerlist[-1][0] is not 'Set-Cookie')

   def test_set_cookie_on_exception_no_request_exception(self):
       import webob
       request = testing.DummyRequest()
       request.exception = None
       session = self._makeOne(request, cookie_on_exception=False)
       response = webob.Response()
       self.assert_(response.headerlist[-1][0] is not 'Set-Cookie')

   def test_cookie_callback(self):
       import webob
       request = testing.DummyRequest()
       session = self._makeOne(request)
       callbacks = request.response_callbacks
       response = webob.Response()
       processed_callback = callbacks[0](request, response)
       self.assertEqual(response.headerlist[-1][0], 'Set-Cookie')

   def test_delete_cookie(self):
       import webob
       request = testing.DummyRequest()
       session = self._makeOne(request)
       session.delete_cookie()
       response = webob.Response()
       request.response_callbacks[1](request, response)
       self.assert_('Max-Age=0' in response.headers['Set-Cookie'])

class TestRedisDict(unittest.TestCase):
    def get_client(self, redis=None):
        if redis is None:
            from redis import Redis
        return Redis(db=9)

    def make_one(self, redis):
        from pyramid_redis_sessions import RedisDict
        return RedisDict(redis, 'uid1', 1200)

    def make_plain_dict(self, sequence=[]):
        return dict(sequence)

    def value_from_client(self, key):
        return self.client.hget(self.client_dict_key, key)

    def setUp(self):
        self.client = self.get_client()
        self.client.flushdb()
        self.rdict = self.make_one(self.client)
        self.client_dict_key = self.rdict.dict_hash_key
        self.dict = self.make_plain_dict()

    def tearDown(self):
        self.client.flushdb()
        self.client.connection_pool.disconnect()

    def test_set_and_get(self):
        key = 'mylist'
        value = [1,2,3]
        self.dict[key] = value
        self.rdict[key] = value
        self.assertEquals(self.dict[key], self.rdict[key])

    def test_delitem(self):
        self.rdict['mykey'] = 'value'
        from_client_before = self.value_from_client('mykey')
        self.assert_(from_client_before is not None)
        del self.rdict['mykey']
        from_client_after = self.value_from_client('mykey')
        self.assertEquals(from_client_after, None)

    def test_setdefault_doesntexist(self):
        key = 'default'
        default = 5
        callback = lambda : self.rdict[key]
        self.assertRaises(KeyError, callback)
        self.rdict.setdefault(key, default)
        self.assertEquals(self.rdict[key], default)

    def test_setdefault_exists(self):
        adict = {'abc':1}
        key = 'default'
        self.rdict[key] = adict
        default = 5
        result = self.rdict.setdefault(key, default)
        self.assertEquals(result, adict)

    def test_contains(self):
        key = 'test'
        val = 'test'
        self.assertEquals(key in self.rdict, False)
        self.rdict[key] = val
        self.assertEquals(key in self.rdict, True)

    def test_keys(self):
        keys = ['one', 'two', 'three']
        for k in keys:
            self.rdict[k] = True
        self.assertEquals(keys, self.rdict.keys())

    def test_items(self):
        items = [('one', 1), ('two', 2.22), ('three', unicode('3'))]
        items.sort()
        for k, v in items:
            self.rdict[k] = v
        rdict_items = self.rdict.items()
        rdict_items.sort()
        self.assertEquals(items, rdict_items)

    def test_clear_items(self):
        empty_dict = {}
        self.rdict['notempty'] = True
        self.assertEquals(self.rdict['notempty'], True)
        self.rdict.clear()
        as_dict = self.rdict._deserialize_dict()
        self.assertEquals(as_dict, {})

    def test_get(self):
        self.assertRaises(KeyError, lambda: self.rdict['notakey'])
        default = 5
        value_from_dict = self.rdict.get('notakey', default)
        self.assertEquals(value_from_dict, default)

    def test_pop_exists(self):
        default = 'default'
        key = 'keytopop'
        self.rdict[key] = True
        self.assertEquals(self.rdict.pop(key), True)

    def test_pop_default(self):
        default = 'default'
        self.assertEquals(self.rdict.pop('notakey', default), default)

    def test_pop_doesnt_exist(self):
        self.assertRaises(KeyError, lambda: self.rdict.pop('notakey'))

    def test_update(self):
        master_dict = {'key1': 'val1', 'key2': 2, 'key3': 3.0}
        self.rdict.update(master_dict)
        deserialized = self.rdict._deserialize_dict()
        self.assertEquals(master_dict, deserialized)

    def test_iter(self):
        keys = ['a', 'b', 'c']
        for k in keys:
            self.rdict[k] = k
        itered = list(self.rdict.__iter__())
        itered.sort()
        self.assertEquals(itered, keys)

    def test_has_key(self):
        key = 'test'
        val = 'test'
        self.assertEquals(self.rdict.has_key(key), False)
        self.rdict[key] = val
        self.assertEquals(self.rdict.has_key(key), True)

    def test_values(self):
        values = [1, 'two', 3.3]
        for i in range(len(values)):
            self.rdict[i] = values[i]
        rdict_values = self.rdict.values()
        values.sort()
        rdict_values.sort()
        self.assertEquals(rdict_values, values)

    def test_itervalues(self):
        keys = [1,2,3]
        for k in keys:
            self.rdict[k] = k
        for val in self.rdict.itervalues():
            self.assert_(val in keys)

    def test_iteritems(self):
        items = [('one', 1), ('two', 2), ('three', 3)]
        for k, v in items:
            self.rdict[k] = v
        items.sort()
        rdict_items = list(self.rdict.iteritems())
        rdict_items.sort()
        self.assertEquals(items, rdict_items)

    # entire RedisDict.popitem block is coming up untested despite working here
    def popitem_when_populated(self):
        master_dict = {'one':1, 'two': 'two', 'three':3.3}
        self.rdict.update(master_dict)
        popped_key, popped_val = self.rdict.popitem()
        self.assertEquals(master_dict[popped_key], popped_val)
        self.assertRaises(KeyError, lambda: self.rdict[popped_key])

    def popitem_when_empty(self):
        self.assertRaises(KeyError, lambda: self.rdict.popitem())

    def test_iterkeys(self):
        keys = ['a', 'b', 'c']
        for k in keys:
            self.rdict[k] = True
        for val in self.rdict.iterkeys():
            self.assert_(val in keys)

class TestPyramidRedisSessions(unittest.TestCase):
    def get_client(self, redis=None):
        if redis is None:
            from redis import Redis
        return Redis(db=9)

    def make_key(self, generator=None):
        if generator is None:
            from pyramid_redis_sessions import _generate_session_id
            generator =  _generate_session_id
        return generator()

    def setUp(self):
        from pyramid_redis_sessions import (
            PyramidRedis,
            get_unique_session_id,
            )
        self.client = self.get_client()
        self.client.flushdb()
        timeout = 1200
        session_id = get_unique_session_id(self.client, timeout)
        self.request = testing.DummyRequest()
        self.session = PyramidRedis(self.client, session_id, timeout,
                                    lambda a, b=3600 : None, lambda : None)

    def tearDown(self):
        self.client.flushdb()
        self.client.connection_pool.disconnect()

    def test_created(self):
        time = self.session.created
        self.assertEquals(type(time), float)

    def test_invalidate(self):
        keys = self.session.all_keys
        keys_from_redis = [self.client.get(k) for k in keys]
        self.assertEquals(any(keys_from_redis), True) # some keys are None
        self.session.invalidate()
        deleted_keys_from_redis = [self.client.get(k) for k in keys]
        self.assertEquals(all(keys_from_redis), False)

    def test_new(self):
        self.assertEquals(self.session.new, False)

    def test_changed(self):
        test_dict = {'one':1, 'two':'two', 'three':3.3}
        self.session['test_dict'] = test_dict
        test_dict['new_key'] = True
        self.session.changed()
        from_redis = self.session['test_dict']
        self.assertEquals(test_dict, from_redis)

    def test_new_csrf_token(self):
        token_from_session = self.session.new_csrf_token()
        token_from_redis = self.client.get(self.session.csrf_key)
        self.assertEquals(token_from_session, token_from_redis)

    def test_get_csrf_token(self):
        first_time = self.session.get_csrf_token()
        second_time = self.session.get_csrf_token()
        self.assertEquals(first_time, second_time)

    def test_flash_and_peek(self):
        messages = ['test1', 'test2', unicode('test3')]
        for m in messages:
            self.session.flash(m)
        self.assertEquals(self.session.peek_flash(), messages)

    def test_flash_and_pop(self):
        messages = ['test1', 'test2', unicode('test3')]
        for m in messages:
            self.session.flash(m)
        self.assertEquals(self.session.pop_flash(), messages)
        self.assertEquals(self.session.pop_flash(), [])
