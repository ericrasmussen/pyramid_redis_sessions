import os
import cPickle
import unittest

from . import (
    DummyRedis,
    DummyPipeline,
    )

# set environment variable "REDIS_LIVE_TESTS" to use a real Redis server
if os.environ.get('REDIS_LIVE_TESTS', False): # pragma no cover
    from redis import Redis
    db = os.environ.get('REDIS_TEST_DB', '9')
    test_redis = Redis(db=db)
    test_redis.set('session.id', cPickle.dumps({}))
    default_encoder = cPickle.dumps
    default_decoder = cPickle.loads
else: # pragma no cover
    test_redis = DummyRedis()
    default_encoder = lambda x : x
    default_decoder = lambda x : x


class TestRedisDict(unittest.TestCase):
    def _makeOne(self, redis=test_redis, session_id='session.id', timeout=300):
        from ..redisdict import RedisDict
        return RedisDict(redis, session_id, timeout,
                         encode=default_encoder, decode=default_decoder)

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


