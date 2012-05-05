import os
import time
import random
import cPickle
import binascii
from redis import Redis
from hashlib import sha1
from functools import partial
from pyramid.compat import text_
from zope.interface import implementer

from redis.exceptions import (
    ConnectionError,
    WatchError,
)

from pyramid.interfaces import (
    ISession,
    IDict,
    )

from pyramid.session import (
    signed_serialize,
    signed_deserialize,
    )

pid = os.getpid()
_CURRENT_PERIOD = None
_marker = object()

def _generate_session_id():
    """Returns opaque 40-character session id
    An example is: e193a01ecf8d30ad0affefd332ce934e32ffce72
    """
    when = time.time()
    period = 1
    this_period = int(when - (when % period))
    rand = random.randint(0, 99999999)
    global _CURRENT_PERIOD
    if this_period != _CURRENT_PERIOD:
        _CURRENT_PERIOD = this_period
    source = '%s%s%s' % (rand, when, pid)
    session_id = sha1(source).hexdigest()
    return session_id

def _insert_session_id_if_unique(redis, timeout, session_id,
                                 encoder=cPickle.dumps):
    """Attempt to insert a given ``session_id`` and return the succesful id or
    ``None``."""
    with redis.pipeline() as pipe:
        try:
            pipe.watch(session_id)
            value = pipe.get(session_id)
            if value != None:
                return None
            pipe.multi()
            encoded_time = encoder(time.time())
            pipe.set(session_id, encoded_time)
            pipe.expire(session_id, timeout)
            pipe.execute()
            return session_id
        except WatchError: # pragma no cover (relies on redis-py tests)
            return None

def get_unique_session_id(redis, timeout):
    """Returns a unique session id after inserting it successfully in Redis."""
    while 1:
        session_id = _generate_session_id()
        attempt = _insert_session_id_if_unique(redis, timeout, session_id)
        if attempt is not None:
            return attempt
        else:
            continue # pragma no cover (would require chance/many cycles)

def session_factory_from_settings(settings):
    """Return a Pyramid session factory using Redis session settings from
    a Paste config file."""
    keys = filter(
        lambda s: s.startswith('redis.session.') or s.startswith('redis.'),
        settings
        )
    options = {}
    for k in keys:
        param = k.split('.')[-1]
        value = settings[k]
        if hasattr(value, 'lower') and value.lower() in ['true', 'false']:
            value = value.lower() == 'true' # coerce bools
        options[param] = value
    return RedisSessionFactory(**options)

def RedisSessionFactory(
    secret,
    timeout=1200,
    period=300,
    cookie_name='session',
    cookie_max_age=None,
    cookie_path='/',
    cookie_domain=None,
    cookie_secure=False,
    cookie_httponly=False,
    cookie_on_exception=True,
    host='localhost',
    port=6379,
    db=0,
    password=None,
    socket_timeout=None,
    connection_pool=None,
    charset='utf-8',
    errors='strict',
    unix_socket_path=None,
    ):
    """
    Configure a :term:`session factory` which will provide session data from
    a Redis server.

    The return value of this function is a :term:`session factory`, which may
    be provided as the ``session_factory`` argument of a
    :class:`pyramid.config.Configurator` constructor, or used as the
    ``session_factory`` argument of the
    :meth:`pyramid.config.Configurator.set_session_factory` method.

    Parameters:

    ``secret``
    A string which is used to sign the cookie.

    ``timeout``
    A number of seconds of inactivity before a session times out.

    ``period``
    Granularity of inactivity checking in seconds (should be lower
    than timeout).

    ``cookie_name``
    The name of the cookie used for sessioning. Default: ``session``.

    ``cookie_max_age``
    The maximum age of the cookie used for sessioning (in seconds).
    Default: ``None`` (browser scope).

    ``cookie_path``
    The path used for the session cookie. Default: ``/``.

    ``cookie_domain``
    The domain used for the session cookie. Default: ``None`` (no domain).

    ``cookie_secure``
    The 'secure' flag of the session cookie. Default: ``False``.

    ``cookie_httponly``
    The 'httpOnly' flag of the session cookie. Default: ``False``.

    ``cookie_on_exception``
    If ``True``, set a session cookie even if an exception occurs
    while rendering a view. Default: ``True``.

    ``host``
    A string representing the IP of your Redis server. Default: ``localhost``.

    ``port``
    An integer represnting the port of your Redis server. Default: ``6379``.

    ``db``
    An integer to select a specific database on your Redis server.
    Default: ``0``

    ``password``
    A string password to connect to your Redis server/database if
    required. Default: ``None``

    The following arguments are passed straight to the redis-py Redis instance
    and allow you to further configure the Redis client:
      ``socket_timeout``
      ``connection_pool``
      ``charset``
      ``errors``
      ``unix_socket_path``
    """

    port = int(port)

    def factory(request, new_session_id=get_unique_session_id):
        # note: will raise ConnectionError if connection is not established
        redis = getattr(request.registry, '_redis_sessions', None)
        if redis is None:
            redis = Redis(host=host, port=port, db=db, password=password,
                          socket_timeout=socket_timeout,
                          connection_pool=connection_pool, charset=charset,
                          errors=errors, unix_socket_path=unix_socket_path)
            setattr(request.registry, '_redis_sessions', redis)

        cookieval = request.cookies.get(cookie_name)

        session_id = None

        if cookieval is not None:
            try:
                session_id = signed_deserialize(cookieval, secret)
            except ValueError:
                pass

        def add_cookie(session_id, max_age=cookie_max_age):
            if not cookie_on_exception:
                exc = getattr(request, 'exception', None)
                if exc is None: # don't set cookie during exceptions
                    return
            def set_cookie_callback(request, response):
                cookieval = signed_serialize(session_id, secret)
                response.set_cookie(
                    cookie_name,
                    value = cookieval,
                    max_age = max_age,
                    domain = cookie_domain,
                    secure = cookie_secure,
                    httponly = cookie_httponly,
                    )
            request.add_response_callback(set_cookie_callback)

        def delete_cookie():
            def set_cookie_callback(request, response):
                response.delete_cookie(cookie_name)
            request.add_response_callback(set_cookie_callback)

        if session_id is None:
            session_id = new_session_id(redis, timeout)
            add_cookie(session_id)

        # attempt to find the session by ``session_id``
        session_check = redis.get(session_id)

        # case: found session associated with ``session_id``
        if session_check is not None:
            session = PyramidRedis(redis, session_id, timeout,
                                   add_cookie, delete_cookie)

        # case: session id obtained from cookie is not in Redis; begin anew
        else:
            unique_id = _insert_session_id_if_unique(redis, session_id, timeout)
            add_cookie(unique_id)
            session = PyramidRedis(redis, session_id, timeout,
                                   add_cookie, delete_cookie)
            session._v_new = True
        return session
    return factory

def refresh(wrapped):
    """Decorator to refresh the timeout on all keys for a given session.
    Expects underlying object to have attributes:
      ``redis``" Redis connection object
      ``all_keys``: names of session-specific Redis keys
      ``timeout``: time in seconds to keep Redis keys alive
    """
    def reset_timeout(session, *arg, **kw):
        result = wrapped(session, *arg, **kw)
        with session.redis.pipeline() as pipe:
            for key in session.all_keys:
                pipe.expire(key, session.timeout)
            pipe.execute()
        return result

    return reset_timeout

@implementer(IDict)
class RedisDict(object):
    """A Redis-backed implementation of the ``IDict`` interface.
    If a larger session object inherits from ``RedisDict``, it must override
    ``self.all_keys`` to include any other session-specific keys that need to be
    refreshed when the ``dict``-like hash is read or modified."""

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
        The dual of ``encode`` to convert serialized strings back to Python
        objects. Default: ``cPickle.loads``.
        """

        self.session_id = session_id
        self.redis = redis
        self.timeout = timeout
        self.dict_hash_key = self.session_id + ':dict'
        self.all_keys = (self.dict_hash_key)
        self.encode = encode
        self.decode = decode
        self.object_references = {}

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

@implementer(ISession)
class PyramidRedis(RedisDict):
    """Implements the Pyramid ISession interface and is returned by
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

def includeme(config): # pragma no cover
    """Allows users to call ``config.include('pyramid_redis_sessions')``."""
    session_factory = session_factory_from_settings(config.registry.settings)
    config.set_session_factory(session_factory)
