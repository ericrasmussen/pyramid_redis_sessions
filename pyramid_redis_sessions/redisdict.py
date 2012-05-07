import cPickle
from zope.interface import implementer
from pyramid.interfaces import IDict

from .util import refresh

_marker = object()

@implementer(IDict)
class RedisDict(object):
    """A Redis-backed implementation of the ``IDict`` interface.
    """

    def __init__(self, redis, session_id, timeout,
                 encode=cPickle.dumps, decode=cPickle.loads):
        """Initializes a per-session ``dict``-like object backed by Redis.

        All keys are stored in a unique Redis hash (the key is the session_id +
        ':dict') and exposed with a dictionary interface.

        Parameters:

        ``redis``
        A Redis connection object.

        ``session_id``
        A unique string associated with the session. Used as a prefix for keys
        and hashes associated with the session.

        ``timeout``
        Keys will be set to expire in ``timeout`` seconds on each read/write
        access. If keys are not accessed for the duration of a ``timeout``,
        Redis will remove them.

        ``encode``
        A function to serialize pickleable Python objects. Default:
        ``cPickle.dumps``.

        ``decode``
        The dual of ``encode``, to convert serialized strings back to Python
        objects. Default: ``cPickle.loads``.
        """

        self.session_id = session_id
        self.redis = redis
        self.timeout = timeout
        self.encode = encode
        self.decode = decode
        self.managed_dict = self.from_redis()

    def to_redis(self):
        """ Encode this session's ``managed_dict`` for storage in Redis."""
        return self.encode(self.managed_dict)

    def from_redis(self):
        """ Get this session's pickled/encoded ``dict`` from Redis."""
        persisted = self.redis.get(self.session_id)
        decoded = self.decode(persisted)
        return decoded

    @refresh
    def __delitem__(self, key):
        """Remove ``key`` from the session."""
        del self.managed_dict[key]

    @refresh
    def __setitem__(self, key, value):
        self.managed_dict[key] = value

    @refresh
    def __getitem__(self, key):
        return self.managed_dict[key]

    @refresh
    def __contains__(self, key):
        return key in self.managed_dict

#    @refresh
#    def setdefault(self, k, default=None):
#        """Add ``default`` to the hash for key ``k``."""
#        self._serialize_val(k, default, f=self.redis.hsetnx)
#        return self.get(k, default)
#
#    @refresh
#    def __contains__(self, k):
#        """Equivalent to Redis's HEXISTS command."""
#        return self.redis.hexists(self.dict_hash_key, k)
#
#    @refresh
#    def keys(self):
#        """Equivalent to Redis's HKEYS command."""
#        return self.redis.hkeys(self.dict_hash_key)
#
#    @refresh
#    def items(self):
#        """Derserialize the Redis hash into a Python dict and call
#        ``items()``."""
#        return self._deserialize_dict().items()
#
#    @refresh
#    def clear(self):
#        """``redis-py`` treats a non-existent hash the same as an empty one
#        for all of the methods supplied here, so clearing is analogous to
#        deleting."""
#        self.redis.delete(self.dict_hash_key)
#
#    @refresh
#    def get(self, k, default=None):
#        """Attempts to get deserialized value. If key does not exist, catches
#        ``KeyError`` and returns ``default``."""
#        try:
#            return self._deserialize_val(k)
#        except KeyError:
#            return default
#
#
#    @refresh
#    def pop(self, k, default=_marker):
#        """Buffer commands to retrieve value by key and delete it. If
#        the attempt to get the key returns ``None``, and no default is 
#        passed, it will raise a ``KeyError``."""
#        with self.redis.pipeline() as pipe:
#            while 1:
#                try:
#                    pipe.watch(self.dict_hash_key)
#                    value = pipe.hget(self.dict_hash_key, k)
#                    pipe.multi()
#                    pipe.hdel(self.dict_hash_key, k)
#                    pipe.execute()
#                    break
#                except WatchError: # pragma no cover (relies on redis-py tests)
#                    continue
#        if value is None:
#            if default is _marker:
#                raise KeyError(k)
#            return default
#        return self.decode(value) # explicit ``decode`` required here
#
#    @refresh
#    def update(self, d):
#        """``dict`` updates are equivalent to the Redis HMSET command.
#        The supplied dict will be serialized prior to update."""
#        serialized = self._serialize_dict(d)
#        self.redis.hmset(self.dict_hash_key, serialized)
#
#    @refresh
#    def __iter__(self):
#        """Get the (possibly empty) ``dict`` from Redis and return its
#        ``__iter__`` method."""
#        d = self._deserialize_dict()
#        return d.__iter__()
#
#    @refresh
#    def has_key(self, k):
#        """Equivalent to Redis's HEXISTS command."""
#        return self.redis.hexists(self.dict_hash_key, k)
#
#    @refresh
#    def values(self):
#        """Equivalent to Redis's HVALS command, but explicit decoding is
#        required here."""
#        vals = self.redis.hvals(self.dict_hash_key)
#        deserialized = map(self.decode, vals)
#        return deserialized
#
#    @refresh
#    def itervalues(self):
#        """Turns ``self.values()`` into an iterator."""
#        return iter(self.values())
#
#    @refresh
#    def iteritems(self):
#        """Turns ``self.items()`` into an iterator."""
#        return iter(self.items())
#
#    @refresh
#    def popitem(self):
#        """Redis doesn't offer a facility for accessing a random key in
#        the hash, so we instead retrieve the hash as a Python ``dict`` and
#        rely on its ``popitem()`` method."""
#        # ``popitem`` tests pass but coverage lists this block as uncovered
#        with self.redis.pipeline() as pipe: # pragma no cover
#            while 1:
#                try:
#                    pipe.watch(self.dict_hash_key)
#                    d = pipe.hgetall(self.dict_hash_key)
#                    key = None
#                    key, val = d.popitem() # can intentionally raise key error
#                    pipe.multi()
#                    pipe.hdel(self.dict_hash_key, key)
#                    pipe.execute()
#                    break
#                except WatchError:
#                    continue
#            return (key, self.decode(val))
#
#    @refresh
#    def iterkeys(self):
#        """Turns ``self.keys()`` into an iterator."""
#        return iter(self.keys())
#
