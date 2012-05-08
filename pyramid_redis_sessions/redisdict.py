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

    @refresh
    def setdefault(self, key, default=None):
        return self.managed_dict.setdefault(key, default)

    def keys(self):
        return self.managed_dict.keys()

    def items(self):
        return self.managed_dict.items()

    @refresh
    def clear(self):
        return self.managed_dict.clear()

    def get(self, key, default=None):
        return self.managed_dict.get(key, default)

    @refresh
    def pop(self, key, default=None):
        return self.managed_dict.pop(key, default)

    @refresh
    def update(self, other):
        return self.managed_dict.update(other)

    def __iter__(self):
        return self.managed_dict.__iter__()

    def has_key(self, key):
        return self.managed_dict.has_key(key)

    def values(self):
        return self.managed_dict.values()

    def itervalues(self):
        return self.managed_dict.itervalues()

    def iteritems(self):
        return self.managed_dict.iteritems()

    def iterkeys(self):
        return self.managed_dict.iterkeys()

    @refresh
    def popitem(self):
        return self.managed_dict.popitem()
