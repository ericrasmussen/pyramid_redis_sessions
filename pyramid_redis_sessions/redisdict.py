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

    def _serialize_val(self, k, v, f=None, d=None):
        """Convenience method to serialize value ``v`` and add it to hash ``d``
        with key ``k`` using Redis insert function ``f``."""
        setter = f or self.redis.hset
        dict_hash = d or self.dict_hash_key
        serialized = self.encode(v)
        setter(dict_hash, k, serialized)
        self.object_references[k] = v

    def _deserialize_val(self, k, f=None, d=None):
        """Convenience method to retrieve and decode a value from hash ``d``
        given key ``k`` and Redis retrieve function ``f``.
        Uses ``KeyError` to distinguish between non-existent
        values and values that decode to the ``None`` object. This supports
        edge cases such as:
          request.session.setdefault('mykey', None)
          request.session['mykey'] # produces None
          request.session['notakey'] # raises KeyError
        """
        getter = f or self.redis.hget
        dict_hash = d or self.dict_hash_key
        value = getter(dict_hash, k)
        if value is not None:
            deserialized = self.decode(value)
            return deserialized
        else:
            raise KeyError(k)

    def _serialize_dict(self, d):
        """Convenience method to encode all the values in dict ``d``."""
        serialized = {}
        for key, value in d.items():
            serialized[key] = self.encode(value)
            self.object_references[key] = value
        return serialized

    def _deserialize_dict(self, f=None, d=None):
        """``decode``s all the values from a given Redis hash and returns
        a dict."""
        getter = f or self.redis.hgetall
        dict_hash = d or self.dict_hash_key
        strdict = getter(dict_hash)
        new = {}
        for key, value in strdict.items():
            new[key] = self.decode(value)
        return new

    @refresh
    def __delitem__(self, k):
        """Remove key ``k`` from the miscellaneous hash for this session."""
        self.redis.delete(self.dict_hash_key, k)

    @refresh
    def setdefault(self, k, default=None):
        """Add ``default`` to the hash for key ``k``."""
        self._serialize_val(k, default, f=self.redis.hsetnx)
        return self.get(k, default)

    @refresh
    def __getitem__(self, k):
        """If key ``k`` exists, returns the unpickled value from the hash,
        otherwise raises ``KeyError``."""
        return self._deserialize_val(k)

    @refresh
    def __contains__(self, k):
        """Equivalent to Redis's HEXISTS command."""
        return self.redis.hexists(self.dict_hash_key, k)

    @refresh
    def keys(self):
        """Equivalent to Redis's HKEYS command."""
        return self.redis.hkeys(self.dict_hash_key)

    @refresh
    def items(self):
        """Derserialize the Redis hash into a Python dict and call
        ``items()``."""
        return self._deserialize_dict().items()

    @refresh
    def clear(self):
        """``redis-py`` treats a non-existent hash the same as an empty one
        for all of the methods supplied here, so clearing is analogous to
        deleting."""
        self.redis.delete(self.dict_hash_key)

    @refresh
    def get(self, k, default=None):
        """Attempts to get deserialized value. If key does not exist, catches
        ``KeyError`` and returns ``default``."""
        try:
            return self._deserialize_val(k)
        except KeyError:
            return default

    @refresh
    def __setitem__(self, k, value):
        """Sets the key/value pair in the Redis hash. If the hash didn't
        exist before, it is automatically created."""
        self._serialize_val(k, value)

    @refresh
    def pop(self, k, default=_marker):
        """Buffer commands to retrieve value by key and delete it. If
        the attempt to get the key returns ``None``, and no default is 
        passed, it will raise a ``KeyError``."""
        with self.redis.pipeline() as pipe:
            while 1:
                try:
                    pipe.watch(self.dict_hash_key)
                    value = pipe.hget(self.dict_hash_key, k)
                    pipe.multi()
                    pipe.hdel(self.dict_hash_key, k)
                    pipe.execute()
                    break
                except WatchError: # pragma no cover (relies on redis-py tests)
                    continue
        if value is None:
            if default is _marker:
                raise KeyError(k)
            return default
        return self.decode(value) # explicit ``decode`` required here

    @refresh
    def update(self, d):
        """``dict`` updates are equivalent to the Redis HMSET command.
        The supplied dict will be serialized prior to update."""
        serialized = self._serialize_dict(d)
        self.redis.hmset(self.dict_hash_key, serialized)

    @refresh
    def __iter__(self):
        """Get the (possibly empty) ``dict`` from Redis and return its
        ``__iter__`` method."""
        d = self._deserialize_dict()
        return d.__iter__()

    @refresh
    def has_key(self, k):
        """Equivalent to Redis's HEXISTS command."""
        return self.redis.hexists(self.dict_hash_key, k)

    @refresh
    def values(self):
        """Equivalent to Redis's HVALS command, but explicit decoding is
        required here."""
        vals = self.redis.hvals(self.dict_hash_key)
        deserialized = map(self.decode, vals)
        return deserialized

    @refresh
    def itervalues(self):
        """Turns ``self.values()`` into an iterator."""
        return iter(self.values())

    @refresh
    def iteritems(self):
        """Turns ``self.items()`` into an iterator."""
        return iter(self.items())

    @refresh
    def popitem(self):
        """Redis doesn't offer a facility for accessing a random key in
        the hash, so we instead retrieve the hash as a Python ``dict`` and
        rely on its ``popitem()`` method."""
        # ``popitem`` tests pass but coverage lists this block as uncovered
        with self.redis.pipeline() as pipe: # pragma no cover
            while 1:
                try:
                    pipe.watch(self.dict_hash_key)
                    d = pipe.hgetall(self.dict_hash_key)
                    key = None
                    key, val = d.popitem() # can intentionally raise key error
                    pipe.multi()
                    pipe.hdel(self.dict_hash_key, key)
                    pipe.execute()
                    break
                except WatchError:
                    continue
            return (key, self.decode(val))

    @refresh
    def iterkeys(self):
        """Turns ``self.keys()`` into an iterator."""
        return iter(self.keys())
