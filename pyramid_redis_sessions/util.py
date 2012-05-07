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
            encoded_time = encoder(time.time())
            pipe.set(session_id, encoded_time)
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
    """ Convenience function to collect settings prefixed by 'redis.session'.
    Coerces 'true' and 'false' (case insensitive) to bools.
    """
    keys = filter(
        lambda s: s.startswith('redis.session.'),
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

def session_factory_from_settings(settings): # pragma no cover
    """ Return a Pyramid session factory using Redis session settings from
    a Paste config file.
    """
    options = _parse_settings(settings)
    return RedisSessionFactory(**options)

def refresh(wrapped):
    """Decorator to refresh the timeout on all keys for a given session.
    Expects underlying session to have the attributes:
      ``redis``  : Redis connection object
      ``key``    : a unique Redis key for this session
      ``timeout``: time in seconds to keep the Redis key alive
    """
    def reset_timeout(session, *arg, **kw):
        result = wrapped(session, *arg, **kw)
        session.redis.expire(session.session_id, session.timeout)
        return result

    return reset_timeout
