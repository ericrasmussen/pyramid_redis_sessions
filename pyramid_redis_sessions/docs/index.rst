.. index::
   single: Installation
   single: Configuration
   single: Initialization
   single: Advanced Usage
   single: API
   single: Installing Redis
   single: Why Redis?
   single: Notes on Testing

.. _front:

======================
pyramid_redis_sessions
======================
This package provides a fast and stable implementation of Pyramid's `ISession
interface <http://docs.pylonsproject.org/projects/pyramid/en/latest/api/interfaces.html#pyramid.interfaces.ISession>`_
, using Redis as its backend (see `Why Redis?`_ for more information on Redis).

Special thanks to Chris McDonough for the original idea, inspiration, and some
borrowed code.


Installation
============
It is recommended that add pyramid_redis_sessions to your pyramid app's
setup.py file so that it will be automatically installed and managed. For
instance, in the `setup` call in your setup.py you can add
`pyramid_redis_sessions` to the `requires` list::

    requires = [
        'pyramid',
        'pyramid_redis_sessions',
    ]
    setup(
      # all your package metadata
      install_requires = requires,
    )


But for a quick start, you can also get the package from PyPI with either::

    $ easy_install pyramid_redis_sessions

Or::

    $ pip install pyramid_redis_sessions


For redis installation notes see `Installing Redis`_.


Configuration
=============
Next, configure `pyramid_redis_sessions` via your Paste config file. Only
`redis.sessions.secret` is required. All other settings are optional. 

For complete documentation on the `RedisSessionFactory` that uses
these settings, see `API`_. Otherwise, keep reading for the quick list::


    # session settings
    redis.sessions.secret = your_cookie_signing_secret
    redis.sessions.timeout = 1200
    
    # session cookie settings
    redis.sessions.cookie_name = session
    redis.sessions.cookie_max_age = max_age_in_seconds
    redis.sessions.cookie_path = /
    redis.sessions.cookie_domain =
    redis.sessions.cookie_secure = False
    redis.sessions.cookie_httponly = False
    redis.sessions.cookie_on_exception = True

    # you can supply a redis connection string as a URL
    redis.sessions.url = redis://username:password@localhost:6379/0

    # or as individual settings (note: the URL gets preference if you do both)
    redis.sessions.host = localhost
    redis.sessions.port = 6379
    redis.sessions.db = 0
    redis.sessions.password = None

    # additional options can be supplied to redis-py's `StrictRedis`
    redis.sessions.socket_timeout =
    redis.sessions.connection_pool =
    redis.sessions.charset = utf-8
    redis.sessions.errors = strict
    redis.sessions.unix_socket_path =

    # in the advanced section we'll cover extra control over the connection
    redis.sessions.custom_connect = my.dotted.python.callable

    # along with defining your own methods to encode and decode session data
    redis.sessions.encode = cPickle.dumps
    redis.sessions.decode = cPickle.loads


Initialization
==============
Lastly, you need to tell Pyramid to use `pyramid_redis_sessions` as your
session factory. The preferred way is adding it with `config.include`, like
this::

    def main(global_config, **settings):
        config = Configurator(settings=settings)
        config.include('pyramid_redis_sessions')


The above method is recommended because it's simpler, idiomatic, and no less
configurable than the alternatives. It even has the added benefit of
automatically resolving dotted python paths for the advanced options (see 
`Advanced Usage`_).

However, you can also explicitly pass a `settings` dict to the
`session_factory_from_settings` function. This can be helpful if you configure
or modify your settings in code::

    from pyramid_redis_sessions import session_factory_from_settings

    def main(global_config, **settings):
        config = Configurator(settings=settings)
        session_factory = session_factory_from_settings(settings)
        config.set_session_factory(session_factory)




Advanced Usage
==============
This section documents advanced configuration options and any session methods
that are specific to `pyramid_redis_sessions`.


Permanently adjusting the timeout setting for a session
------------------------------------------------------
It's useful to think of a session as a way to manage online loitering. If you
had a brick and mortar store, you wouldn't want people sitting around for hours
at a time not shopping. The session timeout is the physical world equivalent of
some tough looking security folk that politely escort loiterers from the
building.

But... one day one of the loiterers might be the store owner, or your grandma,
or someone you don't want thrown out after a couple of minutes of not shopping.
In the physical world you'd need to spend time training the security team to
treat those people specially. In `pyramid_redis_sessions`, you only need to
identify one of these users and call the following method::

    request.session.adjust_timeout_for_session(timeout_in_seconds)


This will permanently change the timeout setting for that user's session for
the duration of the session.


Custom Connection Handler
-------------------------
`pyramid_redis_sessions` makes things easy for most developers by creating a
redis connection from settings and storing the connection in pyramid's
`registry` for later use. However, you may find yourself wanting to share a
connection across multiple applications, customizing connection settings
dynamically, or any number of other things I haven't thought of. To this end,
you can specify a dotted python path to a custom redis connection handler::

    redis.sessions.custom_connect = app.module.my_connection_thingy


If you instantiate the session factory with includeme, pyramid's `config`
machinery will follow the dotted path and attempt to return the callable.

However, if you instantiate the session factory in code (even by passing in a
settings dict), you must supply the actual python callable rather than a dotted
string.

Either way, the python object must be a callable that takes a pyramid request
and the keyword arguments accepted by StrictRedis (you don't *have* to use
StrictRedis, but those are the redis-specific settings that will be passed to
your callable).

Example::

    def my_connection_thingy(request, **redis_options):
        redis = get_redis_instance_from_somewhere()
        if not redis:
            redis = StrictRedis(**redis_options)
            set_redis_instance_somewhere(redis)
        return redis


Special thanks to raydeo on #pyramid for the idea.


Custom Encoders and Decoders
----------------------------
By default, pyramid_redis_sessions uses `cPickle` for serializing and
deserializing sessions to and from Redis. `cPickle` is very fast, stable, and
widely used, so I recommend sticking with it unless you have a specific
reason not to.

However, because you may very well have a specific reason not to, you can
specify the following settings in your config::

    redis.sessions.encode = my_module.my_encoder
    redis.sessions.decode = my_module.my_decoder

If you do change the defaults you're on your own, and it's assumed that the
following holds::

    decode(encode(data)) == data

Where `data` is, at minimum, a python dict of session data.

One possible use case (given that redis does not support encryption or
decryption) is supplying an encode function that serializes
then encrypts, and a decode function that decrypts then deserializes. However,
there will be a performance penalty for encrypting and decrypting all session
data all the time. If you only need to encrypt some sensitive data, a simpler
solution would be adding the encrypted data to the session and decrypting it
when you retrieve it from the session.


API
===

.. automodule:: pyramid_redis_sessions
    :members:


.. automethod:: pyramid_redis_sessions.session.RedisSession.adjust_timeout_for_session



Installing Redis
================
The best place to start is the redis `quick start guide <http://redis.io/topics/quickstart>`_.

If you need automated deployment with your application, you can find guides
online for redis deployment via buildout, puppet, chef, etc. If anyone would
like to compile a list of recipes for these deployment options, I wholly
encourage pull requests with links.

Discussions of redis security are outside the purview of these docs, but it's
worth noting that redis will listen on all interfaces by default, potentially
exposing all your session data to the world. You can avoid this with a bind
declaration in your redis.conf file such as::

    bind 127.0.0.1


You can read more in a blog post discussing this issue `here
<http://blog.liftsecurity.io/post/32770744557/that-thing-where-you-didnt-change-the-redis-default>`_.


Why Redis?
==========
Redis is fast, widely deployed, and stable. It works best when your data can
fit in memory, but is configurable and still quite fast when you need to sync
to disk. There are plenty of existing benchmarks, opinion pieces, and articles
if you want to learn about its use cases. But for `pyramid_redis_sessions` I'm
interested in it specifically for these reasons:

* it really is <expletive of your choice> fast
* it has a very handy built-in mechanism for setting expirations on keys
* the watch mechanism is a nice, lightweight alternative to full transactions
* session data tends to be important but not mission critical, but if it is...
* redis has configurable `persistence <http://redis.io/topics/persistence>`_


Notes on Testing
================
The test suite is written in a way that may be unusual to some, so if you submit
a patch I only ask that you follow the testing methodology employed here. On a
technical level it boils down to:

#. Parameterizing classes or functions that connect to outside systems
#. In tests, supplying dummy instances of those classes


In practice this means never hardcoding a redis-py `StrictRedis` instance in
`pyramid_redis_sessions`, and always passing in instances of `DummyRedis` in
tests.

On a philosophical level I see outside processes as swappable strategies, and
the purpose of my code is to control how those strategies are employed. For
this reason tests in `pyramid_redis_session` should never need to use `Mock`.



Contents:

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

