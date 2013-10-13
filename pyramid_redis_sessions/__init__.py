# -*- coding: utf-8 -*-


from .compat import cPickle
from .session import RedisSession

from .connection import get_default_connection

from .util import (
    get_unique_session_id,
    _generate_session_id,
)

from pyramid.session import (
    signed_serialize,
    signed_deserialize,
)

def includeme(config):
    """
    This function is detected by Pyramid so that you can easily include
    `pyramid_redis_sessions` in your `main` method like so::

        config.include('pyramid_redis_sessions')

    Parameters:

    ``config``
    A Pyramid ``config.Configurator``
    """
    settings = config.registry.settings

    # special rule for converting dotted python paths to callables
    for option in ('client_callable', 'serialize', 'deserialize',
                   'id_generator'):
        key = 'redis.sessions.%s' % option
        if key in settings:
            settings[key] = config.maybe_dotted(settings[key])

    session_factory = session_factory_from_settings(settings)
    config.set_session_factory(session_factory)

def session_factory_from_settings(settings):
    """
    Convenience method to construct a ``RedisSessionFactory`` from Paste config
    settings. Only settings prefixed with "redis.sessions" will be inspected
    and, if needed, coerced to their appropriate types (for example, casting
    the ``timeout`` value as an `int`).

    Parameters:

    ``settings``
    A dict of Pyramid application settings
    """
    from .util import _parse_settings
    options = _parse_settings(settings)
    return RedisSessionFactory(**options)

def RedisSessionFactory(
    secret,
    timeout=1200,
    cookie_name='session',
    cookie_max_age=None,
    cookie_path='/',
    cookie_domain=None,
    cookie_secure=False,
    cookie_httponly=True,
    cookie_on_exception=True,
    url=None,
    host='localhost',
    port=6379,
    db=0,
    password=None,
    socket_timeout=None,
    connection_pool=None,
    charset='utf-8',
    errors='strict',
    unix_socket_path=None,
    client_callable=None,
    serialize=cPickle.dumps,
    deserialize=cPickle.loads,
    id_generator=_generate_session_id,
    ):
    """
    Constructs and returns a session factory that will provide session data
    from a Redis server. The returned factory can be supplied as the
    ``session_factory`` argument of a :class:`pyramid.config.Configurator`
    constructor, or used as the ``session_factory`` argument of the
    :meth:`pyramid.config.Configurator.set_session_factory` method.

    Parameters:

    ``secret``
    A string which is used to sign the cookie.

    ``timeout``
    A number of seconds of inactivity before a session times out.

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

    ``url``
    A connection string for a Redis server, in the format:
    redis://username:password@localhost:6379/0
    Default: ``None``.

    ``host``
    A string representing the IP of your Redis server. Default: ``localhost``.

    ``port``
    An integer representing the port of your Redis server. Default: ``6379``.

    ``db``
    An integer to select a specific database on your Redis server.
    Default: ``0``

    ``password``
    A string password to connect to your Redis server/database if
    required. Default: ``None``.

    ``client_callable``
    A python callable that accepts a Pyramid `request` and Redis config options
    and returns a Redis client such as redis-py's `StrictRedis`.
    Default: ``None``.

    ``serialize``
    A function to serialize the session dict for storage in Redis.
    Default: ``cPickle.dumps``.

    ``deserialize``
    A function to deserialize the stored session data in Redis.
    Default: ``cPickle.loads``.

    ``id_generator``
    A function to create a unique ID to be used as the session key when a
    session is first created.
    Default: private function that uses sha1 with the time and random elements
    to create a 40 character unique ID.

    The following arguments are also passed straight to the ``StrictRedis``
    constructor and allow you to further configure the Redis client::

      socket_timeout
      connection_pool
      charset
      errors
      unix_socket_path
    """
    def factory(request, new_session_id=get_unique_session_id):
        redis_options = dict(
            host=host,
            port=port,
            db=db,
            password=password,
            socket_timeout=socket_timeout,
            connection_pool=connection_pool,
            charset=charset,
            errors=errors,
            unix_socket_path=unix_socket_path,
            )

        # an explicit client callable gets priority over the default
        if client_callable is not None:
            redis = client_callable(request, **redis_options)
        else:
            redis = get_default_connection(request, url=url, **redis_options)

        # sets an add cookie callback on the request when called
        def add_cookie(session_key):
            def set_cookie_callback(request, response):
                """
                The set cookie callback will first check to see if we're in an
                exception. If we're in an exception and ``cookie_on_exception``
                is False, we return immediately before setting the cookie.

                For all other cases the cookie will be set normally.
                """
                exc = getattr(request, 'exception', None)
                # exit early if there's an exception and the user specified
                # to not set cookies on exception
                if exc is not None and not cookie_on_exception:
                    return
                cookieval = signed_serialize(session_key, secret)
                response.set_cookie(
                    cookie_name,
                    value=cookieval,
                    max_age=cookie_max_age,
                    domain=cookie_domain,
                    secure=cookie_secure,
                    httponly=cookie_httponly,
                    )
            request.add_response_callback(set_cookie_callback)
            return

        # sets a delete cookie callback on the request when called
        def delete_cookie():
            def set_cookie_callback(request, response):
                response.delete_cookie(cookie_name)
            request.add_response_callback(set_cookie_callback)
            return

        # attempt to retrieve a session_id from the cookie
        session_id = _session_id_from_cookie(request, cookie_name, secret)

        is_new_session = redis.get(session_id) is None

        # if we couldn't find the session id in redis, create a new one
        if is_new_session:
            session_id = new_session_id(redis, timeout, serialize,
                                        generator=id_generator)

        session = RedisSession(
            redis,
            session_id,
            timeout,
            delete_cookie,
            serialize=serialize,
            deserialize=deserialize
        )

        # flag new sessions as new and add a cookie with the session id
        if is_new_session:
            add_cookie(session_id)
            session._rs_new = True

        return session

    return factory


def _session_id_from_cookie(request, cookie_name, secret):
    """
    Attempts to retrieve and return a session ID from a session cookie in the
    current request. Returns None if the cookie isn't found or the signed secret
    is bad.
    """
    cookieval = request.cookies.get(cookie_name)

    if cookieval is not None:
        try:
            session_id = signed_deserialize(cookieval, secret)
            return session_id
        except ValueError:
            pass

    return None

