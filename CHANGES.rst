=========
Changelog
=========

-Initial Release

-09/24/2012: 0.9 beta release

-11/12/2012: raise ConfigurationError if required redis.sessions.secret setting
             is missing.

-02/17/2013: New API method: adjust_timeout_for_session. This method allows you
             to permanently alter the timeout setting for a given session for
             the duration of the session.

             Note: on a development branch this was known as
             "reset_timeout_for_session" but was renamed to avoid confusion
             with the internal act of resetting timeouts each time the session
             is accessed.

             Additional changes include:

                 1) Removing the unused "period" setting
                 2) Fixing an error with the cookie_on_exception setting
                 3) Using asbool for boolean settings
                 4) Adding documentation
                 5) Adding new configuration options (see the docs for details)


              Internal (non-API) changes include:

                 * renamed the new session flag from "_v_new" to "_rs_new"
                 * remove util module's dependency on cPickle
                 * always cast the timeout setting as an int
                 * removing unused imports
                 * many updates and additions to docstrings/comments
                 * moving the redis connection/client logic to a new module

-06/30/2013: New configuration options:

                * redis.sessions.client_callable (supply your own redis client)
                * redis.sessions.serialize (use your own pickling function)
                * redis.sessions.deserialize (use your own unpickling function)
                * redis.sessions.id_generator (callable to generate session IDs)
                * redis.sessions.prefix (add a prefix to session IDs in redis)

             BREAKING CHANGE: cookie_httponly now defaults to True. If you are
               currently relying on outside scripts being able to access the
               session cookie (a bad idea to begin with), you will need to
               explicitly set::

                   redis.sessions.cookie_httponly = False

               For most (likely all) users, you will not notice any difference.

               Reference: https://www.owasp.org/index.php/HttpOnly


             Session ID generation: session IDs are now generated with an
               initial value from os.urandom, which (according to the offical
               python docs) is "suitable for cryptographic use". The previous
               implementation was concerned primarily with integrity. This
               update improves on integrity but also adds a greater level of
               security.
