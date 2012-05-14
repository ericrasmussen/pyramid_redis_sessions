This is the second draft for Redis-backed sessions in the Pyramid Web Application Development Framework.

This is not yet ready for production use, but you are welcome to test/profile/submit patches.

The package implements the Pyramid ISession interface (http://docs.pylonsproject.org/projects/pyramid/en/1.3-branch/api/interfaces.html#pyramid.interfaces.ISession), and that portion of the API will not change. However, any other implementation-specific methods on the ``PyramidRedis`` session object are likely to undergo major changes.

Warnings before use:

  * This is an early alpha and not yet intended for production use

Usage (this will improve after release on pypi):

  * Add this package to your Python path or distribute/install egg
  * In your Pyramid config file (typically development.ini or production.ini), configure the settings (see below)
  * In your Pyramid application main function, use either:

      1) pyramid.include('pyramid_redis_sessions')
      2) from pyramid_redis_sessions import session_factory_from_settings
         session_factory = session_Factory_from_settings(settings)
         config.set_session_factory(session_factory)

In your Pyramid app's INI file you can configure the following settings:

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

