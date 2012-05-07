import os
import cPickle
import binascii
from redis import Redis
from functools import partial
from pyramid.compat import text_
from zope.interface import implementer

from redis.exceptions import (
    ConnectionError,
    WatchError,
)

from .util import (
    session_factory_from_settings,
    get_unique_session_id,
    refresh,
    )

from .redisdict import RedisDict

from pyramid.interfaces import ISession

from pyramid.session import (
    signed_serialize,
    signed_deserialize,
    )

def includeme(config): # pragma no cover
    """Allows users to call ``config.include('pyramid_redis_sessions')``."""
    session_factory = session_factory_from_settings(config.registry.settings)
    config.set_session_factory(session_factory)


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

