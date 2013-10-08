Advanced Usage
==============

Adjusting Timeouts Dynamically
------------------------------
It's useful to think of a session as a way to manage online loitering. If you
had a brick and mortar store, you wouldn't want people sitting around for hours
at a time not shopping. The session timeout is the physical world equivalent of
some tough looking security folk that politely escort loiterers from the
building.

But one day the loiterers might be the store owners, or your grandparents,
or people you don't want thrown out after a couple of minutes of not shopping.
In the physical world you'd need to spend time training the security team to
treat those people specially. In `pyramid_redis_sessions`, you only need to
identify one of these users and call the following method::

    request.session.adjust_timeout_for_session(timeout_in_seconds)


This will permanently change the timeout setting for that user's session for
the duration of the session.


Supplying Your Own Redis Client
-------------------------------

`pyramid_redis_sessions` makes things easy for most developers by creating a
Redis client from settings and storing the client in Pyramid's
`registry` for later use. However, you may find yourself wanting extra control
over how the client is created.

Here are some reasons you might want to build your own client callable:

* you want to use your own wrapper or redis-py's Redis instead of StrictRedis
* you want to choose from multiple Redis instances or modify connection
  settings based on the current request

To this or other ends, you can specify a dotted python path to a custom
Redis client callable::

    redis.sessions.client_callable = app.module.my_connection_getter

If you instantiate the session factory with includeme, Pyramid's `config`
machinery will follow the dotted path and attempt to return the callable.

However, if you instantiate the session factory in code (even by passing in a
settings dict), you must supply the actual python callable rather than a dotted
string.

Either way, the python object must be a callable that takes a Pyramid request
and the keyword arguments accepted by StrictRedis (you don't *have* to use
StrictRedis, but those are the Redis-specific settings that will be passed to
your callable).

Example::

    def get_redis_client(request, **redis_options):
        redis = get_redis_instance_from_somewhere()
        if not redis:
            redis = StrictRedis(**redis_options)
            set_redis_instance_somewhere(redis)
        return redis


Special thanks to raydeo on #pyramid for the idea.


Overriding cPickle
------------------
By default, `pyramid_redis_sessions` uses `cPickle` for serializing and
deserializing sessions to and from Redis. `cPickle` is very fast, stable, and
widely used, so I recommend sticking with it unless you have a specific
reason not to.

However, because you may very well have a specific reason not to, you can
specify the following settings in your config::

    redis.sessions.serialize = my_module.my_serializer
    redis.sessions.deserialize = my_module.my_deserializer

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


Overriding the id_generator
---------------------------
`pyramid_redis_sessions` has a sensible and recommended default for quickly
generating unique session keys. You don't need to specify anything to use it.

However, if you'd like to prefix the keys (typically for visual inspection in
redis) you can use::

    redis.sessions.prefix = mycoolprefix

And if for any reason you want to generate unique IDs on your own or using a
particular UID function, you can specify a callable with::

    redis.sessions.id_generator = some_library.some_uid_generating_function

This is useful when you want to increase security at the cost of performance,
reduce integrity for greater speed on a small internal app, or any other
specialized tradeoff. But again, unless you have highly specialized
requirements, please use the default.
