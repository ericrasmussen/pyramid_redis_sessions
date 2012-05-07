class DummySession(object):
    def __init__(self, key, redis, timeout=300):
        self.session_id = key
        self.redis = redis
        self.timeout = timeout


class DummyRedis(object):
    def __init__(self, **kwarg):
        self.timeouts = {}
        self.pipeline = lambda *arg, **kwarg : DummyPipeline()

    def expire(self, key, timeout):
        self.timeouts[key] = timeout

    def ttl(self, key):
        return self.timeouts.get(key)

    def set_dummy_pipeline(self, pipeline):
        self.pipeline = lambda *arg, **kwarg : pipeline


class DummyPipeline(object):
    def __init__(self, raise_watch_error=False):
        self.redisdict = {}
        self.raise_watch_error = raise_watch_error

    def __enter__(self):
        return self

    def __exit__(self, *arg, **kwarg):
        pass

    def multi(self):
        pass

    def set(self, key, value):
        self.redisdict[key] = value

    def get(self, key):
        return self.redisdict.get(key)

    def expire(self, key, timeout):
        pass

    def watch(self, key):
        if self.raise_watch_error:
            from redis.exceptions import WatchError
            raise WatchError

    def execute(self):
        pass
