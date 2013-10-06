# -*- coding: utf-8 -*-

import os
import time


import binascii
from pyramid.compat import text_
from zope.interface import implementer

from .compat import cPickle

from .util import (
    persist,
    refresh,
    to_unicode,
    )

from pyramid.interfaces import ISession

@implementer(ISession)
class RedisSession(object):
    """
    Implements the Pyramid ISession and IDict interfaces and is returned by
    the ``RedisSessionFactory``.

    Methods that modify the ``dict`` (get, set, update, etc.) are decorated
    with ``@persist`` to update the persisted copy in Redis and reset the
    timeout.

    Methods that are read-only (items, keys, values, etc.) are decorated
    with ``@refresh`` to reset the session's expire time in Redis.

    Session methods make use of the dict methods that already communicate with
    Redis, so they are not decorated.

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

    ``delete_cookie``
    A function that takes no arguments and returns nothing, but should have the
    side effect of deleting the session cookie from the ``response`` object.

    ``serialize``
    A function to serialize pickleable Python objects. Default:
    ``cPickle.dumps``.

    ``deserialize``
    The dual of ``serialize``, to convert serialized strings back to Python
    objects. Default: ``cPickle.loads``.
    """

    def __init__(
        self,
        redis,
        session_id,
        timeout,
        delete_cookie,
        serialize=cPickle.dumps,
        deserialize=cPickle.loads
        ):

        self.session_id = session_id
        self.redis = redis
        self.serialize = serialize
        self.deserialize = deserialize
        self.delete_cookie = delete_cookie
        self.created = time.time()
        self.managed_dict = self.from_redis()
        self.default_timeout = timeout

    @property
    def timeout(self):
        return self.managed_dict.get('_rs_timeout', self.default_timeout)

    def to_redis(self):
        """ Serialize this session's ``managed_dict`` for storage in Redis.
        Primarily used by the ``@persist`` decorator to save the current session
        state to Redis.
        """
        return self.serialize(self.managed_dict)

    def from_redis(self):
        """ Get this session's pickled/serialized ``dict`` from Redis."""
        persisted = self.redis.get(self.session_id)
        deserialized = self.deserialize(persisted)
        return deserialized

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
        return key in self.managed_dict

    @refresh
    def values(self):
        return self.managed_dict.values()

    @refresh
    def itervalues(self):
        try:
            values = self.managed_dict.itervalues()
        except AttributeError: # pragma: no cover
            values = self.managed_dict.values()
        return values

    @refresh
    def iteritems(self):
        try:
            items = self.managed_dict.iteritems()
        except AttributeError: # pragma: no cover
            items = self.managed_dict.items()
        return items

    @refresh
    def iterkeys(self):
        try:
            keys = self.managed_dict.iterkeys()
        except AttributeError: # pragma: no cover
            keys = self.managed_dict.keys()
        return keys

    @persist
    def changed(self):
        """ Persists the working dict immediately with ``@persist``."""
        pass

    # session methods persist or refresh using above dict methods
    @property
    def new(self):
        return getattr(self, '_rs_new', False)

    def invalidate(self):
        """ Delete all keys unique to this session and expire cookie."""
        self.clear()
        self.delete_cookie()

    def new_csrf_token(self):
        token = text_(binascii.hexlify(os.urandom(20)))
        self['_csrft_'] = token
        return token

    def get_csrf_token(self):
        token = self.get('_csrft_', None)
        if token is None:
            token = self.new_csrf_token()
        else:
            token = to_unicode(token)
        return token

    def flash(self, msg, queue='', allow_duplicate=True):
        storage = self.setdefault('_f_' + queue, [])
        if allow_duplicate or (msg not in storage):
            storage.append(msg)
            self.changed()  # notify redis of change to ``storage`` mutable

    def peek_flash(self, queue=''):
        storage = self.get('_f_' + queue, [])
        return storage

    def pop_flash(self, queue=''):
        storage = self.pop('_f_' + queue, [])
        return storage

    # RedisSession extra methods
    def adjust_timeout_for_session(self, timeout_seconds):
        """
        Permanently adjusts the timeout for this session to ``timeout_seconds``
        for as long as this session is active. Useful in situations where you
        want to change the expire time for a session dynamically.
        """
        self['_rs_timeout'] = timeout_seconds
