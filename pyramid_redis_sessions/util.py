import os
import time
import random
import cPickle
from hashlib import sha1
from redis.exceptions import WatchError

pid = os.getpid()
_CURRENT_PERIOD = None

def _generate_session_id():
    """ Returns opaque 40-character session id
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
    """ Attempt to insert a given ``session_id`` and return the succesful id or
    ``None``."""
    with redis.pipeline() as pipe:
        try:
            pipe.watch(session_id)
            value = pipe.get(session_id)
            if value is not None:
                return None
            pipe.multi()
            empty_session = encoder({})
            pipe.set(session_id, empty_session)
            pipe.expire(session_id, timeout)
            pipe.execute()
            return session_id
        except WatchError:
            return None

def get_unique_session_id(redis, timeout, generator=_generate_session_id):
    """ Returns a unique session id after inserting it successfully in Redis."""
    while 1:
        session_id = generator()
        attempt = _insert_session_id_if_unique(redis, timeout, session_id)
        if attempt is not None:
            return attempt


def _parse_settings(settings):
    """ Convenience function to collect settings prefixed by 'redis.sessions'.
    Coerces 'true' and 'false' (case insensitive) to bools.
    """
    keys = filter(
        lambda s: s.startswith('redis.sessions.'),
        settings
        )
    options = {}
    for k in keys:
        param = k.split('.')[-1]
        value = settings[k]
        # coerce bools
        if hasattr(value, 'lower') and value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        options[param] = value

    # coerce ints
    for i in ('port', 'db'):
        if i in options:
            options[i] = int(options[i])

    return options

def refresh(wrapped):
    """Decorator to reset the expire time for this session's key in Redis.
    """
    def wrapped_refresh(session, *arg, **kw):
        result = wrapped(session, *arg, **kw)
        session.redis.expire(session.session_id, session.timeout)
        return result

    return wrapped_refresh

def persist(wrapped):
    """ Decorator to persist the working session copy in Redis and reset the
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
