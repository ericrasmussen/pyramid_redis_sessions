import os
import cPickle
import unittest

from . import (
    DummyRedis,
    DummyPipeline,
    )

class TestRedisSession(unittest.TestCase):
    def _makeOne(self, session_id='session.id', timeout=300,
                 delete_cookie=lambda : None,
                 encode=cPickle.dumps, decode=cPickle.loads):
        from ..redissession import RedisSession
        redis = DummyRedis()
        redis.set(session_id, encode({}))
        return RedisSession(redis, session_id, timeout, delete_cookie,
                         encode=encode, decode=decode)

    def test_delitem(self):
        inst = self._makeOne()
        inst['key'] = 'val'
        del inst['key']
        from_redis = inst.from_redis()
        self.assertNotIn('key', inst)
        self.assertNotIn('key', from_redis)

    def test_setitem(self):
        inst = self._makeOne()
        inst['key'] = 'val'
        from_redis = inst.from_redis()
        self.assertIn('key', inst)
        self.assertIn('key', from_redis)

    def test_getitem(self):
        inst = self._makeOne()
        inst['key'] = 'val'
        from_redis = inst.from_redis()
        self.assertEqual(inst['key'], from_redis['key'])

    def test_contains(self):
        inst = self._makeOne()
        inst['key'] = 'val'
        from_redis = inst.from_redis()
        self.assert_('key' in inst)
        self.assert_('key' in from_redis)

    def test_setdefault(self):
        inst = self._makeOne()
        result = inst.setdefault('key', 'val')
        self.assertEqual(result, inst['key'])

    def test_keys(self):
        inst = self._makeOne()
        inst['key1'] = ''
        inst['key2'] = ''
        inst_keys = inst.keys()
        from_redis = inst.from_redis()
        persisted_keys = from_redis.keys()
        self.assertEqual(inst_keys, persisted_keys)

    def test_items(self):
        inst = self._makeOne()
        inst['a'] = 1
        inst['b'] = 2
        inst_items = inst.items()
        from_redis = inst.from_redis()
        persisted_items = from_redis.items()
        self.assertEqual(inst_items, persisted_items)

    def test_clear(self):
        inst = self._makeOne()
        inst['a'] = 1
        inst.clear()
        from_redis = inst.from_redis()
        self.assertNotIn('a', inst)
        self.assertNotIn('a', from_redis)

    def test_get(self):
        inst = self._makeOne()
        inst['key'] = 'val'
        get_from_inst = inst.get('key')
        self.assertEqual(get_from_inst, 'val')
        from_redis = inst.from_redis()
        get_from_redis = from_redis.get('key')
        self.assertEqual(get_from_inst, get_from_redis)

    def test_get_default(self):
        inst = self._makeOne()
        get_from_inst = inst.get('key', 'val')
        self.assertEqual(get_from_inst, 'val')
        from_redis = inst.from_redis()
        get_from_redis = from_redis.get('key', 'val')
        self.assertEqual(get_from_inst, get_from_redis)

    def test_pop(self):
        inst = self._makeOne()
        inst['key'] = 'val'
        popped = inst.pop('key')
        self.assertEqual(popped, 'val')
        from_redis = inst.from_redis()
        self.assertNotIn('key', from_redis)

    def test_pop_default(self):
        inst = self._makeOne()
        popped = inst.pop('key', 'val')
        self.assertEqual(popped, 'val')

    def test_update(self):
        inst = self._makeOne()
        inst['a'] = 1
        to_be_updated = {'a': 'overriden', 'b': 2}
        inst.update(to_be_updated)
        self.assertEqual(inst['a'], 'overriden')
        self.assertEqual(inst['b'], 2)
        from_redis = inst.from_redis()
        self.assertEqual(from_redis['a'], 'overriden')
        self.assertEqual(from_redis['b'], 2)

    def test_iter(self):
        inst = self._makeOne()
        keys = ['a', 'b', 'c']
        for k in keys:
            inst[k] = k
        itered = list(inst.__iter__())
        itered.sort()
        self.assertEqual(keys, itered)

    def test_has_key(self):
        inst = self._makeOne()
        inst['actual_key'] = ''
        self.assertTrue(inst.has_key('actual_key'))
        self.assertFalse(inst.has_key('not_a_key'))

    def test_values(self):
        inst = self._makeOne()
        inst['a'] = 1
        inst['b'] = 2
        expected_values = [1, 2]
        actual_values = inst.values()
        actual_values.sort()
        self.assertEqual(actual_values, expected_values)

    def test_itervalues(self):
        inst = self._makeOne()
        inst['a'] = 1
        inst['b'] = 2
        itered = list(inst.itervalues())
        itered.sort()
        expected = [1, 2]
        self.assertEqual(expected, itered)

    def test_iteritems(self):
        inst = self._makeOne()
        inst['a'] = 1
        inst['b'] = 2
        itered = list(inst.iteritems())
        itered.sort()
        expected = [('a', 1), ('b', 2)]
        self.assertEqual(expected, itered)

    def test_iterkeys(self):
        inst = self._makeOne()
        inst['a'] = 1
        inst['b'] = 2
        itered = list(inst.iterkeys())
        itered.sort()
        expected = ['a', 'b']
        self.assertEqual(expected, itered)

    def test_popitem(self):
        inst = self._makeOne()
        inst['a'] = 1
        inst['b'] = 2
        popped = inst.popitem()
        options = [('a', 1), ('b', 2)]
        self.assertIn(popped, options)
        from_redis = inst.from_redis()
        self.assertNotIn(popped, from_redis)

    def test_IDict_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IDict
        inst = self._makeOne()
        verifyObject(IDict, inst)

    def test_created(self):
        import time
        before = time.time()
        inst = self._makeOne()
        created = inst.created
        after = time.time()
        self.assertLessEqual(before, created)
        self.assertGreaterEqual(after, created)

    def test_not_new(self):
        inst = self._makeOne()
        self.assertFalse(inst.new)

    def test_new(self):
        inst = self._makeOne()
        inst._v_new = True
        self.assertTrue(inst.new)

    def test_invalidate_dict(self):
        inst = self._makeOne()
        inst['key'] = 'val'
        inst.invalidate()
        self.assertNotIn('key', inst)

    def test_mutablevalue_changed(self):
        inst = self._makeOne()
        inst['a'] = {'1':1, '2':2}
        tmp = inst['a']
        tmp['3'] = 3
        inst.changed()
        from_redis = inst.from_redis()
        self.assertEqual(from_redis['a'], {'1':1, '2':2, '3':3})

    def test_csrf_token(self):
        inst = self._makeOne()
        new_token = inst.new_csrf_token()
        got_token = inst.get_csrf_token()
        self.assertEqual(new_token, got_token)

    def test_get_new_csrf_token(self):
        inst = self._makeOne()
        self.assertNotIn('_csrft_', inst)
        token = inst.get_csrf_token()
        self.assertEqual(inst['_csrft_'], token)

    def test_flash(self):
        inst = self._makeOne()
        inst.flash('message')
        msgs = inst.peek_flash()
        self.assertIn('message', msgs)

    def test_flash_alternate_queue(self):
        inst = self._makeOne()
        inst.flash('message', 'queue')
        default_queue = inst.peek_flash()
        self.assertNotIn('message', default_queue)
        other_queue = inst.peek_flash('queue')
        self.assertIn('message', other_queue)

    def test_pop_flash(self):
        inst = self._makeOne()
        inst.flash('message')
        popped = inst.pop_flash()
        self.assertIn('message', popped)
        msgs = inst.peek_flash()
        self.assertEqual(msgs, [])

    def test_ISession_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import ISession
        inst = self._makeOne()
        verifyObject(ISession, inst)

