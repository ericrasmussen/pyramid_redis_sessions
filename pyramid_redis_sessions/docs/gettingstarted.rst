Getting Started
===============

Installation
------------
It is recommended that you add pyramid_redis_sessions to your pyramid app's
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

Or if you prefer::

    $ pip install pyramid_redis_sessions


For Redis installation notes see :doc:`redis`.


Configuration
-------------
Next, configure `pyramid_redis_sessions` via your Paste config file. Only
`redis.sessions.secret` is required. All other settings are optional.

For complete documentation on the `RedisSessionFactory` that uses
these settings, see :doc:`api`. Otherwise, keep reading for the quick list::


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

    # additional options can be supplied to redis-py's StrictRedis
    redis.sessions.socket_timeout =
    redis.sessions.connection_pool =
    redis.sessions.charset = utf-8
    redis.sessions.errors = strict
    redis.sessions.unix_socket_path =

    # in the advanced section we'll cover how to instantiate your own client
    redis.sessions.client_callable = my.dotted.python.callable

    # along with defining your own serialize and deserialize methods
    redis.sessions.serialize = cPickle.dumps
    redis.sessions.deserialize = cPickle.loads


Initialization
--------------
Lastly, you need to tell Pyramid to use `pyramid_redis_sessions` as your
session factory. The preferred way is adding it with `config.include`, like
this::

    def main(global_config, **settings):
        config = Configurator(settings=settings)
        config.include('pyramid_redis_sessions')


The above method is recommended because it's simpler, idiomatic, and still fully
configurable. It even has the added benefit of automatically resolving dotted
python paths used in the advanced options (see :doc:`advanced`).

However, you can also explicitly pass a `settings` dict to the
`session_factory_from_settings` function. This can be helpful if you configure
or modify your settings in code::

    from pyramid_redis_sessions import session_factory_from_settings

    def main(global_config, **settings):
        config = Configurator(settings=settings)
        session_factory = session_factory_from_settings(settings)
        config.set_session_factory(session_factory)

