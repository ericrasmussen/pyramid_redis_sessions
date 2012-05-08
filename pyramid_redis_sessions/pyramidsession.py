import os
import cPickle
import binascii
from pyramid.compat import text_
from zope.interface import implementer

from .utils import refresh

from .redisdict import RedisDict

from pyramid.interfaces import ISession

@implementer(ISession)
class PyramidRedis(RedisDict):
    """ Implements the Pyramid ISession interface and is returned by
    the RedisSessionFactory.
    Inherits from ``RedisDict`` to implement the required ``IDict``
    interface."""

    def __init__(self, redis, session_id, timeout, add_cookie, delete_cookie,
                 encode=cPickle.dumps, decode=cPickle.loads):
        # essentials
        self.session_id = session_id
        self.redis = redis
        self.timeout = timeout
        self.encode = encode
        self.decode = decode
        self.object_references = {}
        self.add_cookie = add_cookie
        self.delete_cookie = delete_cookie

        # handy key defaults
        self.csrf_key = self.session_id + ':csrft'
        self.queue_hash_key = self.session_id + ':queue'
        self.default_queue_key = '_f_'
        self.dict_hash_key = self.session_id + ':dict'
        self.all_keys = (self.session_id, self.dict_hash_key,
                         self.queue_hash_key, self.csrf_key)

    def invalidate(self):
        """Delete all keys unique to this session and expire cookie."""
        # clear session in Redis
        with self.redis.pipeline() as pipe:
            for key in self.all_keys:
                pipe.delete(key)
            pipe.execute()
        # expire cookie
        self.delete_cookie()

    @property
    @refresh
    def created(self):
        serialized_time = self.redis.get(self.session_id)
        decoded = self.decode(serialized_time)
        return decoded

    @property
    def new(self):
        return getattr(self, '_v_new', False)

    @refresh
    def changed(self):
        """Reserialize objects immediately."""
        self.update(self.object_references)

    @refresh
    def new_csrf_token(self):
        """Generate a new ``token`` and persist in Redis."""
        token = text_(binascii.hexlify(os.urandom(20)))
        self.redis.set(self.csrf_key, token)
        return token

    @refresh
    def get_csrf_token(self):
        """Get existing ``token`` or generate a new one."""
        token = self.redis.get(self.csrf_key)
        if token is None:
            token = self.new_csrf_token()
        else:
            token = unicode(token)
        return token

    @refresh
    def _get_flash_contents(self, queue):
        """Convenience method to get a pickled list from the queue or []."""
        queue_key = self.default_queue_key + queue
        encoded = self.redis.hget(self.queue_hash_key, queue_key)
        if encoded is not None:
            return self.decode(encoded)
        else:
            return []

    @refresh
    def peek_flash(self, queue=''):
        """Retrieve contents of queue as a list."""
        return self._get_flash_contents(queue)

    @refresh
    def flash(self, msg, queue='', allow_duplicate=True):
        """Add a message to the queue."""
        queue_key = self.default_queue_key + queue
        storage = self._get_flash_contents(queue)
        if allow_duplicate or (msg not in storage):
            storage.append(msg)
            updated = self.encode(storage)
            self.redis.hset(self.queue_hash_key, queue_key, updated)

    @refresh
    def pop_flash(self, queue=''):
        """Returns the contents of the queue before emptying it.
        Note: would be more efficient to buffer the HGET/HDEL commands and
        send them through a pipe."""
        queue_key = self.default_queue_key + queue
        storage = self._get_flash_contents(queue)
        self.redis.hdel(self.queue_hash_key, queue_key)
        return storage
