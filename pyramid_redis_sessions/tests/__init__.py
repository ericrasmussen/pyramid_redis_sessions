import cPickle
from urlparse import urlparse

class DummySession(object):
    def __init__(self, key, redis, timeout=300):
        self.session_id = key
        self.redis = redis
        self.timeout = timeout
        self.working_dict = {}

    def to_redis(self):
        return cPickle.dumps(self.working_dict)


class DummyRedis(object):
    def __init__(self, host=None, port=None, password=None, db=None, raise_watcherror=False, **kw):
        self.host = host
        self.port = port
        self.password = password
        self.db = db

        self.timeouts = {}
        self.store = {}
        self.pipeline = lambda : DummyPipeline(self.store, raise_watcherror)

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def expire(self, key, timeout):
        self.timeouts[key] = timeout

    def ttl(self, key):
        return self.timeouts.get(key)

    @classmethod
    def from_url(cls, url, db=None, **kwargs):
        url = urlparse(url)

        # We only support redis:// schemes.
        assert url.scheme == 'redis' or not url.scheme

        # Extract the database ID from the path component if hasn't been given.
        if db is None:
            try:
                db = int(url.path.replace('/', ''))
            except (AttributeError, ValueError):
                db = 0

        return cls(host=url.hostname, port=url.port, db=db,
                   password=url.password, **kwargs)


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
