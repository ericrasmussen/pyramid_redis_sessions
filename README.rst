pyramid_redis_sessions gives you Redis-backed sessions for the Pyramid Web Application Development Framework.

The package implements the Pyramid ISession interface (http://docs.pylonsproject.org/projects/pyramid/en/latest/api/interfaces.html#pyramid.interfaces.ISession), and that portion of the API will not change. However, any other implementation-specific methods on the ``RedisSession`` object are subject to change.

Patches and feature requests are welcome.

Usage:

  * $ easy_install pyramid_redis_sessions
  * In your Pyramid config file (typically development.ini or production.ini), configure the settings (see below)
  * In your Pyramid application ``main`` function, use either:

      * pyramid.include('pyramid_redis_sessions')

  * Or:

      * from pyramid_redis_sessions import session_factory_from_settings
      * session_factory = session_factory_from_settings(settings)
      * config.set_session_factory(session_factory)

You can configure the following settings in your ini file:

 * redis.sessions.secret = your_secret
 * redis.sessions.timeout = 1200
 * redis.sessions.period = 300
 * redis.sessions.cookie_name = session
 * redis.sessions.cookie_max_age =
 * redis.sessions.cookie_path = /
 * redis.sessions.cookie_domain =
 * redis.sessions.cookie_secure = False
 * redis.sessions.cookie_httponly = False
 * redis.sessions.cookie_on_exception = True
 * redis.sessions.host = localhost
 * redis.sessions.port = 6379
 * redis.sessions.db = 0
 * redis.sessions.password = None
 * redis.sessions.socket_timeout =
 * redis.sessions.connection_pool =
 * redis.sessions.charset = utf-8
 * redis.sessions.errors = strict
 * redis.sessions.unix_socket_path =

Only redis.sessions.secret is required. All other parameters have sensible defaults.

Note: package assumes you have a running Redis instance at the specified host and port.
