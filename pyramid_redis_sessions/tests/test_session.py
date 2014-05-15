# -*- coding: utf-8 -*-

import itertools
import time
import unittest

from ..compat import cPickle


class TestRedisSession(unittest.TestCase):
    def _makeOne(self, redis, session_id, new, new_session,
                 serialize=cPickle.dumps, deserialize=cPickle.loads):
        from ..session import RedisSession
        return RedisSession(
            redis=redis,
            session_id=session_id,
            new=new,
            new_session=new_session,
            serialize=serialize,
            deserialize=deserialize,
            )

    def _set_up_session_in_redis(self, redis, session_id, timeout,
                                 session_dict=None, serialize=cPickle.dumps):
        if session_dict is None:
            session_dict = {}
        redis.set(session_id, serialize({
            'managed_dict': session_dict,
            'created': time.time(),
            'timeout': timeout,
            }))
        return session_id

    def _make_id_generator(self):
        ids = itertools.count(start=0, step=1)
        return lambda: str(next(ids))

    def _set_up_session_in_Redis_and_makeOne(self, session_id=None,
                                             session_dict=None, new=True,
                                             timeout=300):
        from . import DummyRedis
        redis = DummyRedis()
        id_generator = self._make_id_generator()
        if session_id is None:
            session_id = id_generator()
        self._set_up_session_in_redis(redis=redis, session_id=session_id,
                                      session_dict=session_dict,
                                      timeout=timeout)
        new_session = lambda: self._set_up_session_in_redis(
            redis=redis,
            session_id=id_generator(),
            session_dict=session_dict,
            timeout=timeout,
            )
        return self._makeOne(
            redis=redis,
            session_id=session_id,
            new=new,
            new_session=new_session,
            )

    def test_init_new_session(self):
        session_id = 'session_id'
        new = True
        timeout = 300
        inst = self._set_up_session_in_Redis_and_makeOne(
            session_id=session_id,
            new=new,
            timeout=timeout,
            )
        self.assertEqual(inst.session_id, session_id)
        self.assertIs(inst.new, new)
        self.assertDictEqual(dict(inst), {})

    def test_init_existing_session(self):
        session_id = 'session_id'
        session_dict = {'key': 'value'}
        new = False
        timeout = 300
        inst = self._set_up_session_in_Redis_and_makeOne(
            session_id=session_id,
            session_dict=session_dict,
            new=new,
            timeout=timeout,
            )
        self.assertEqual(inst.session_id, session_id)
        self.assertIs(inst.new, new)
        self.assertDictEqual(dict(inst), session_dict)

    def test_delitem(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['key'] = 'val'
        del inst['key']
        session_dict_in_redis = inst.from_redis()['managed_dict']
        self.assertNotIn('key', inst)
        self.assertNotIn('key', session_dict_in_redis)

    def test_setitem(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['key'] = 'val'
        session_dict_in_redis = inst.from_redis()['managed_dict']
        self.assertIn('key', inst)
        self.assertIn('key', session_dict_in_redis)

    def test_getitem(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['key'] = 'val'
        session_dict_in_redis = inst.from_redis()['managed_dict']
        self.assertEqual(inst['key'], session_dict_in_redis['key'])

    def test_contains(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['key'] = 'val'
        session_dict_in_redis = inst.from_redis()['managed_dict']
        self.assert_('key' in inst)
        self.assert_('key' in session_dict_in_redis)

    def test_setdefault(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        result = inst.setdefault('key', 'val')
        self.assertEqual(result, inst['key'])

    def test_keys(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['key1'] = ''
        inst['key2'] = ''
        inst_keys = inst.keys()
        session_dict_in_redis = inst.from_redis()['managed_dict']
        persisted_keys = session_dict_in_redis.keys()
        self.assertEqual(inst_keys, persisted_keys)

    def test_items(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['a'] = 1
        inst['b'] = 2
        inst_items = inst.items()
        session_dict_in_redis = inst.from_redis()['managed_dict']
        persisted_items = session_dict_in_redis.items()
        self.assertEqual(inst_items, persisted_items)

    def test_clear(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['a'] = 1
        inst.clear()
        session_dict_in_redis = inst.from_redis()['managed_dict']
        self.assertNotIn('a', inst)
        self.assertNotIn('a', session_dict_in_redis)

    def test_get(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['key'] = 'val'
        get_from_inst = inst.get('key')
        self.assertEqual(get_from_inst, 'val')
        session_dict_in_redis = inst.from_redis()['managed_dict']
        get_from_redis = session_dict_in_redis.get('key')
        self.assertEqual(get_from_inst, get_from_redis)

    def test_get_default(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        get_from_inst = inst.get('key', 'val')
        self.assertEqual(get_from_inst, 'val')
        session_dict_in_redis = inst.from_redis()['managed_dict']
        get_from_redis = session_dict_in_redis.get('key', 'val')
        self.assertEqual(get_from_inst, get_from_redis)

    def test_pop(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['key'] = 'val'
        popped = inst.pop('key')
        self.assertEqual(popped, 'val')
        session_dict_in_redis = inst.from_redis()['managed_dict']
        self.assertNotIn('key', session_dict_in_redis)

    def test_pop_default(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        popped = inst.pop('key', 'val')
        self.assertEqual(popped, 'val')

    def test_update(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['a'] = 1
        to_be_updated = {'a': 'overriden', 'b': 2}
        inst.update(to_be_updated)
        self.assertEqual(inst['a'], 'overriden')
        self.assertEqual(inst['b'], 2)
        session_dict_in_redis = inst.from_redis()['managed_dict']
        self.assertEqual(session_dict_in_redis['a'], 'overriden')
        self.assertEqual(session_dict_in_redis['b'], 2)

    def test_iter(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        keys = ['a', 'b', 'c']
        for k in keys:
            inst[k] = k
        itered = list(inst.__iter__())
        itered.sort()
        self.assertEqual(keys, itered)

    def test_has_key(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['actual_key'] = ''
        self.assertTrue(inst.has_key('actual_key'))
        self.assertFalse(inst.has_key('not_a_key'))

    def test_values(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['a'] = 1
        inst['b'] = 2
        expected_values = [1, 2]
        actual_values = sorted(inst.values())
        self.assertEqual(actual_values, expected_values)

    def test_itervalues(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['a'] = 1
        inst['b'] = 2
        itered = list(inst.itervalues())
        itered.sort()
        expected = [1, 2]
        self.assertEqual(expected, itered)

    def test_iteritems(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['a'] = 1
        inst['b'] = 2
        itered = list(inst.iteritems())
        itered.sort()
        expected = [('a', 1), ('b', 2)]
        self.assertEqual(expected, itered)

    def test_iterkeys(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['a'] = 1
        inst['b'] = 2
        itered = list(inst.iterkeys())
        itered.sort()
        expected = ['a', 'b']
        self.assertEqual(expected, itered)

    def test_popitem(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['a'] = 1
        inst['b'] = 2
        popped = inst.popitem()
        options = [('a', 1), ('b', 2)]
        self.assertIn(popped, options)
        session_dict_in_redis = inst.from_redis()['managed_dict']
        self.assertNotIn(popped, session_dict_in_redis)

    def test_IDict_instance_conforms(self):
        from pyramid.interfaces import IDict
        from zope.interface.verify import verifyObject
        inst = self._set_up_session_in_Redis_and_makeOne()
        verifyObject(IDict, inst)

    def test_created(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        created = inst.from_redis()['created']
        self.assertEqual(inst.created, created)

    def test_timeout(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        timeout = inst.from_redis()['timeout']
        self.assertEqual(inst.timeout, timeout)

    def test_invalidate(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        first_session_id = inst.session_id
        inst.invalidate()
        self.assertNotIn(first_session_id, inst.redis.store)
        self.assertIs(inst._invalidated, True)

    def test_new_session_after_invalidate(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        first_session_id = inst.session_id
        inst['key'] = 'value'
        inst.invalidate()
        second_session_id = inst.session_id
        self.assertSetEqual(set(inst.redis.store.keys()), {second_session_id})
        self.assertNotEqual(second_session_id, first_session_id)
        self.assertIs(bool(second_session_id), True)
        self.assertDictEqual(dict(inst), {})
        self.assertIs(inst.new, True)
        self.assertIs(inst._invalidated, False)

    def test_session_id_access_after_invalidate_creates_new_session(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        first_session_id = inst.session_id
        inst.invalidate()
        second_session_id = inst.session_id
        self.assertNotEqual(second_session_id, first_session_id)
        self.assertIs(bool(second_session_id), True)

    def test_managed_dict_access_after_invalidate_creates_new_session(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        first_session_id = inst.session_id
        inst.invalidate()
        inst.managed_dict  # access
        # .session_id attribute access also creates a new session after
        # invalidate, so just asserting .session_id is not enough to prove that
        # a new session was created after .managed_dict access. Here we note
        # down the session_ids in Redis right after .managed_dict access for an
        # additional check.
        session_ids_in_redis = inst.redis.store.keys()
        second_session_id = inst.session_id
        self.assertSetEqual(set(session_ids_in_redis),
                            {second_session_id})
        self.assertNotEqual(second_session_id, first_session_id)
        self.assertIs(bool(second_session_id), True)

    def test_created_access_after_invalidate_creates_new_session(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        first_session_id = inst.session_id
        inst.invalidate()
        inst.created  # access
        # .session_id attribute access also creates a new session after
        # invalidate, so just asserting .session_id is not enough to prove that
        # a new session was created after .created access. Here we note down
        # the session_ids in Redis right after .created access for an
        # additional check.
        session_ids_in_redis = inst.redis.store.keys()
        second_session_id = inst.session_id
        self.assertSetEqual(set(session_ids_in_redis),
                            {second_session_id})
        self.assertNotEqual(second_session_id, first_session_id)
        self.assertIs(bool(second_session_id), True)

    def test_timeout_access_after_invalidate_creates_new_session(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        first_session_id = inst.session_id
        inst.invalidate()
        inst.timeout  # access
        # .session_id attribute access also creates a new session after
        # invalidate, so just asserting .session_id is not enough to prove that
        # a new session was created after .timeout access. Here we note down
        # the session_ids in Redis right after .timeout access for an
        # additional check.
        session_ids_in_redis = inst.redis.store.keys()
        second_session_id = inst.session_id
        self.assertSetEqual(set(session_ids_in_redis),
                            {second_session_id})
        self.assertNotEqual(second_session_id, first_session_id)
        self.assertIs(bool(second_session_id), True)

    def test_new_attribute_access_after_invalidate_creates_new_session(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        first_session_id = inst.session_id
        inst.invalidate()
        inst.new  # access
        # .session_id attribute access also creates a new session after
        # invalidate, so just asserting .session_id is not enough to prove that
        # a new session was created after .new access. Here we note down the
        # session_ids in Redis right after .new access for an additional check.
        session_ids_in_redis = inst.redis.store.keys()
        second_session_id = inst.session_id
        self.assertSetEqual(set(session_ids_in_redis),
                            {second_session_id})
        self.assertNotEqual(second_session_id, first_session_id)
        self.assertIs(bool(second_session_id), True)

    def test_repeated_invalidates_without_new_session_created_in_between(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        first_session_id = inst.session_id
        inst.invalidate()
        inst.invalidate()
        self.assertNotIn(first_session_id, inst.redis.store)
        self.assertIs(inst._invalidated, True)
        second_session_id = inst.session_id
        self.assertNotEqual(second_session_id, first_session_id)
        self.assertIs(bool(second_session_id), True)

    def test_invalidate_new_session_invalidate(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst.invalidate()
        second_session_id = inst.session_id
        inst.invalidate()
        session_ids_in_redis = inst.redis.store.keys()
        self.assertNotIn(second_session_id, session_ids_in_redis)
        self.assertIs(inst._invalidated, True)

    def test_invalidate_new_session_invalidate_new_session(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst.invalidate()
        second_session_id = inst.session_id
        inst.invalidate()
        third_session_id = inst.session_id
        session_ids_in_redis = inst.redis.store.keys()
        self.assertSetEqual(set(session_ids_in_redis),
                            {third_session_id})
        self.assertNotEqual(third_session_id, second_session_id)
        self.assertIs(bool(third_session_id), True)
        self.assertDictEqual(dict(inst), {})
        self.assertIs(inst.new, True)
        self.assertIs(inst._invalidated, False)

    def test_mutablevalue_changed(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst['a'] = {'1':1, '2':2}
        tmp = inst['a']
        tmp['3'] = 3
        inst.changed()
        session_dict_in_redis = inst.from_redis()['managed_dict']
        self.assertEqual(session_dict_in_redis['a'], {'1':1, '2':2, '3':3})

    def test_csrf_token(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        new_token = inst.new_csrf_token()
        got_token = inst.get_csrf_token()
        self.assertEqual(new_token, got_token)

    def test_get_new_csrf_token(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        self.assertNotIn('_csrft_', inst)
        token = inst.get_csrf_token()
        self.assertEqual(inst['_csrft_'], token)

    def test_flash(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst.flash('message')
        msgs = inst.peek_flash()
        self.assertIn('message', msgs)

    def test_flash_alternate_queue(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst.flash('message', 'queue')
        default_queue = inst.peek_flash()
        self.assertNotIn('message', default_queue)
        other_queue = inst.peek_flash('queue')
        self.assertIn('message', other_queue)

    def test_pop_flash(self):
        inst = self._set_up_session_in_Redis_and_makeOne()
        inst.flash('message')
        popped = inst.pop_flash()
        self.assertIn('message', popped)
        msgs = inst.peek_flash()
        self.assertEqual(msgs, [])

    def test_ISession_instance_conforms(self):
        from pyramid.interfaces import ISession
        from zope.interface.verify import verifyObject
        inst = self._set_up_session_in_Redis_and_makeOne()
        verifyObject(ISession, inst)

    def test_adjust_timeout_for_session(self):
        inst = self._set_up_session_in_Redis_and_makeOne(timeout=100)
        adjusted_timeout = 200
        inst.adjust_timeout_for_session(adjusted_timeout)
        self.assertEqual(inst.timeout, adjusted_timeout)
        self.assertEqual(inst.from_redis()['timeout'], adjusted_timeout)
