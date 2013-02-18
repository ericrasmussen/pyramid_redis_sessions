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
