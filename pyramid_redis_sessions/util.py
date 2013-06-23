import os
import time
import random
import sys
from hashlib import sha1
from pyramid.settings import asbool
from redis.exceptions import WatchError
from pyramid.exceptions import ConfigurationError

PY3 = sys.version_info[0] == 3

def to_binary(value, enc="UTF-8"):
    if PY3 and isinstance(value, str): # pragma: no cover
        value = value.encode(enc)
    return value

def to_unicode(value): # pragma: no cover
    if not PY3:
        value = unicode(value)
    return value

def iterkeys(d, **kw): # pragma: no cover
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw): # pragma: no cover
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw): # pragma: no cover
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw): # pragma: no cover
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))

pid = os.getpid()
_CURRENT_PERIOD = None

def _generate_session_id():
    """
    Returns opaque 40-character session id
    An example is: e193a01ecf8d30ad0affefd332ce934e32ffce72
    """
    when = time.time()
    period = 1
    this_period = int(when - (when % period))
    rand = random.randint(0, 99999999)
    global _CURRENT_PERIOD
    if this_period != _CURRENT_PERIOD:
        _CURRENT_PERIOD = this_period
    source = to_binary('%s%s%s' % (rand, when, pid))
    session_id = sha1(source).hexdigest()
    return session_id

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
    """ Attempt to insert a given ``session_id`` and return the succesful id or
    ``None``."""
    with redis.pipeline() as pipe:
        try:
            pipe.watch(session_id)
            value = pipe.get(session_id)
            if value is not None:
                return None
            pipe.multi()
            empty_session = serialize({})
            pipe.set(session_id, empty_session)
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
    keys = filter(
        lambda s: s.startswith('redis.sessions.'),
        settings
        )

    options = {}

    for k in keys:
        param = k.split('.')[-1]
        value = settings[k]
        options[param] = value

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

    # only required setting
    if 'secret' not in options:
        raise ConfigurationError('redis.sessions.secret is a required setting')

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
    Decorator to persist the working session copy in Redis and reset the
    expire time.
    """
    def wrapped_persist(session, *arg, **kw):
        result = wrapped(session, *arg, **kw)
        with session.redis.pipeline() as pipe:
            pipe.set(session.session_id, session.to_redis())
            pipe.expire(session.session_id, session.timeout)
            pipe.execute()
        return result

    return wrapped_persist
