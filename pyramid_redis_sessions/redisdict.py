import cPickle
from zope.interface import implementer
from pyramid.interfaces import IDict

from .util import (
    refresh,
    persist,
    )


@implementer(IDict)
class RedisDict(object):
    """A Redis-backed implementation of the ``IDict`` interface.
    """

    def __init__(self, redis, session_id, timeout,
                 encode=cPickle.dumps, decode=cPickle.loads):
        """Initializes a per-session ``dict``-like object backed by Redis.

        Methods that modify the ``dict`` (get, set, update, etc.) are decorated
        with ``@persist`` to update the persisted copy in Redis and reset the
        timeout.

        Methods that are read-only (items, keys, values, etc.) are decorated
        with ``@refresh`` to reset the session's expire time in Redis.

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

    # TODO: verify that session_id is always present here or handle case: None
    def from_redis(self):
        """ Get this session's pickled/encoded ``dict`` from Redis."""
        persisted = self.redis.get(self.session_id)
        decoded = self.decode(persisted)
        return decoded

    # dict modifying methods decorated with @persist
    @persist
    def __delitem__(self, key):
        del self.managed_dict[key]

    @persist
    def __setitem__(self, key, value):
        self.managed_dict[key] = value

    @persist
    def setdefault(self, key, default=None):
        return self.managed_dict.setdefault(key, default)

    @persist
    def clear(self):
        return self.managed_dict.clear()

    @persist
    def pop(self, key, default=None):
        return self.managed_dict.pop(key, default)

    @persist
    def update(self, other):
        return self.managed_dict.update(other)

    @persist
    def popitem(self):
        return self.managed_dict.popitem()

    # dict read-only methods decorated with @refresh
    @refresh
    def __getitem__(self, key):
        return self.managed_dict[key]

    @refresh
    def __contains__(self, key):
        return key in self.managed_dict

    @refresh
    def keys(self):
        return self.managed_dict.keys()

    @refresh
    def items(self):
        return self.managed_dict.items()

    @refresh
    def get(self, key, default=None):
        return self.managed_dict.get(key, default)

    @refresh
    def __iter__(self):
        return self.managed_dict.__iter__()

    @refresh
    def has_key(self, key):
        return self.managed_dict.has_key(key)

    @refresh
    def values(self):
        return self.managed_dict.values()

    @refresh
    def itervalues(self):
        return self.managed_dict.itervalues()

    @refresh
    def iteritems(self):
        return self.managed_dict.iteritems()

    @refresh
    def iterkeys(self):
        return self.managed_dict.iterkeys()
