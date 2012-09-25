import os
import cPickle
import binascii
from redis import Redis
from functools import partial
from pyramid.compat import text_
from zope.interface import implementer

from .util import (
    get_unique_session_id,
    refresh,
    )

from .redissession import RedisSession

from pyramid.interfaces import ISession

from pyramid.session import (
    signed_serialize,
    signed_deserialize,
    )

def includeme(config): # pragma no cover
    """Allows users to call ``config.include('pyramid_redis_sessions')``."""
    session_factory = session_factory_from_settings(config.registry.settings)
    config.set_session_factory(session_factory)

def session_factory_from_settings(settings): # pragma no cover
    """ Return a Pyramid session factory using Redis session settings from
    a Paste config file.
    """
    from .util import _parse_settings
    options = _parse_settings(settings)
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

    def factory(request, new_session_id=get_unique_session_id):
        # note: will raise ConnectionError if connection is not established
        redis = getattr(request.registry, '_redis_sessions', None)
        if redis is None: # pragma no cover
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

        def add_cookie(session_key):
            if not cookie_on_exception:
                exc = getattr(request, 'exception', None)
                if exc is None: # don't set cookie during exceptions
                    return
            def set_cookie_callback(request, response):
                cookieval = signed_serialize(session_key, secret)
                response.set_cookie(
                    cookie_name,
                    value = cookieval,
                    max_age = cookie_max_age,
                    domain = cookie_domain,
                    secure = cookie_secure,
                    httponly = cookie_httponly,
                    )
            request.add_response_callback(set_cookie_callback)
            return

        def delete_cookie():
            def set_cookie_callback(request, response):
                response.delete_cookie(cookie_name)
            request.add_response_callback(set_cookie_callback)
            return

        if session_id is None:
            session_id = new_session_id(redis, timeout)
            add_cookie(session_id)

        # attempt to find the session by session_id
        session_check = redis.get(session_id)

        # case: found session associated with session_id
        if session_check is not None:
            session = RedisSession(redis, session_id, timeout, delete_cookie)

        # case: session id obtained from cookie is not in Redis; begin anew
        else:
            new_id = new_session_id(redis, timeout)
            add_cookie(new_id)
            session = RedisSession(redis, new_id, timeout, delete_cookie)
            session._v_new = True
        return session

    return factory

