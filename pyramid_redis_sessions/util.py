# -*- coding: utf-8 -*-

from functools import partial
from hashlib import sha256
import os
import sys
import time

from pyramid.exceptions import ConfigurationError
from pyramid.settings import asbool
from redis.exceptions import WatchError


PY3 = sys.version_info[0] == 3

def to_binary(value, enc="UTF-8"): # pragma: no cover
    if PY3 and isinstance(value, str):
        value = value.encode(enc)
    return value

def to_unicode(value): # pragma: no cover
    if not PY3:
        value = unicode(value)
    return value

def _generate_session_id():
    """
    Produces a random 64 character hex-encoded string. The implementation of
    `os.urandom` varies by system, but you can always supply your own function
    in your ini file with:

        redis.sessions.id_generator = my_random_id_generator
    """
    rand = os.urandom(20)
    return sha256(sha256(rand).digest()).hexdigest()

def prefixed_id(prefix='session:'):
    """
    Adds a prefix to the unique session id, for cases where you want to
    visually distinguish keys in redis.
    """
    session_id = _generate_session_id()
    prefixed_id = prefix + session_id
    return prefixed_id

def _insert_session_id_if_unique(
    redis,
    timeout,
    session_id,
    serialize,
    ):
    """ Attempt to insert a given ``session_id`` and return the successful id
    or ``None``."""
    with redis.pipeline() as pipe:
        try:
            pipe.watch(session_id)
            value = pipe.get(session_id)
            if value is not None:
                return None
            pipe.multi()
            pipe.set(session_id, serialize({
                'managed_dict': {},
                'created': time.time(),
                'timeout': timeout,
                }))
            pipe.expire(session_id, timeout)
            pipe.execute()
            return session_id
        except WatchError:
            return None

def get_unique_session_id(
    redis,
    timeout,
    serialize,
    generator=_generate_session_id,
    ):
    """
    Returns a unique session id after inserting it successfully in Redis.
    """
    while 1:
        session_id = generator()
        attempt = _insert_session_id_if_unique(
            redis,
            timeout,
            session_id,
            serialize,
            )
        if attempt is not None:
            return attempt

def _parse_settings(settings):
    """
    Convenience function to collect settings prefixed by 'redis.sessions' and
    coerce settings to ``int``, ``float``, and ``bool`` as needed.
    """
    keys = [s for s in settings if s.startswith('redis.sessions.')]

    options = {}

    for k in keys:
        param = k.split('.')[-1]
        value = settings[k]
        options[param] = value

    # only required setting
    if 'secret' not in options:
        raise ConfigurationError('redis.sessions.secret is a required setting')

    # coerce bools
    for b in ('cookie_secure', 'cookie_httponly', 'cookie_on_exception'):
        if b in options:
            options[b] = asbool(options[b])

    # coerce ints
    for i in ('timeout', 'port', 'db', 'cookie_max_age'):
        if i in options:
            options[i] = int(options[i])

    # coerce float
    if 'socket_timeout' in options:
        options['socket_timeout'] = float(options['socket_timeout'])

    # check for settings conflict
    if 'prefix' in options and 'id_generator' in options:
        err = 'cannot specify custom id_generator and a key prefix'
        raise ConfigurationError(err)

    # convenience setting for overriding key prefixes
    if 'prefix' in options:
        prefix = options.pop('prefix')
        options['id_generator'] = partial(prefixed_id, prefix=prefix)

    return options

def refresh(wrapped):
    """
    Decorator to reset the expire time for this session's key in Redis.
    """
    def wrapped_refresh(session, *arg, **kw):
        result = wrapped(session, *arg, **kw)
        session.redis.expire(session.session_id, session.timeout)
        return result

    return wrapped_refresh

def persist(wrapped):
    """
    Decorator to persist in Redis all the data that needs to be persisted for
    this session and reset the expire time.
    """
    def wrapped_persist(session, *arg, **kw):
        result = wrapped(session, *arg, **kw)
        with session.redis.pipeline() as pipe:
            pipe.set(session.session_id, session.to_redis())
            pipe.expire(session.session_id, session.timeout)
            pipe.execute()
        return result

    return wrapped_persist
