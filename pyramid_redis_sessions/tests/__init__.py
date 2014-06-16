# -*- coding: utf-8 -*-

from ..compat import cPickle


class DummySession(object):
    def __init__(self, session_id, redis, timeout=300,
                 serialize=cPickle.dumps):
        self.session_id = session_id
        self.redis = redis
        self.timeout = timeout
        self.serialize = serialize
        self.managed_dict = {}
        self.created = float()

    def to_redis(self):
        return self.serialize({
            'managed_dict': self.managed_dict,
            'created': self.created,
            'timeout': self.timeout,
            })


class DummyRedis(object):
    def __init__(self, raise_watcherror=False, **kw):
        self.url = None
        self.timeouts = {}
        self.store = {}
        self.pipeline = lambda : DummyPipeline(self.store, raise_watcherror)
        self.__dict__.update(kw)

    @classmethod
    def from_url(cls, url, **opts):
        redis = DummyRedis()
        redis.url = url
        redis.opts = opts
        return redis

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def delete(self, *keys):
        for key in keys:
            del self.store[key]

    def exists(self, key):
        return key in self.store

    def expire(self, key, timeout):
        self.timeouts[key] = timeout

    def ttl(self, key):
        return self.timeouts.get(key)


class DummyPipeline(object):
    def __init__(self, store, raise_watcherror=False):
        self.store = store
        self.raise_watcherror = raise_watcherror

    def __enter__(self):
        return self

    def __exit__(self, *arg, **kwarg):
        pass

    def multi(self):
        pass

    def set(self, key, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def expire(self, key, timeout):
        pass

    def watch(self, key):
        if self.raise_watcherror:
            from redis.exceptions import WatchError
            raise WatchError

    def execute(self):
        pass
