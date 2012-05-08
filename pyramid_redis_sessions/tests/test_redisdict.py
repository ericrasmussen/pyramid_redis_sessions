import os
import cPickle
import unittest

from . import (
    DummyRedis,
    DummyPipeline,
    )

class TestRedisDict(unittest.TestCase):
    def _makeOne(self, session_id='session.id', timeout=300,
                 encode=cPickle.dumps, decode=cPickle.loads):
        from ..redisdict import RedisDict
        redis = DummyRedis()
        redis.set(session_id, encode({}))
        return RedisDict(redis, session_id, timeout,
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

    def test_mutablevalue_changed(self):
        inst = self._makeOne()
        inst['a'] = {'1':1, '2':2}
        tmp = inst['a']
        tmp['3'] = 3
        self.assertEqual(inst['a'], {'1':1, '2':2, '3':3})

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

    def test_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IDict
        inst = self._makeOne()
        verifyObject(IDict, inst)

