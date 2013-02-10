"""
Defines common methods for obtaining a redis connection.
"""

from redis import StrictRedis

def get_default_connection(request, **settings):
    """
    Default redis connection handler. Once a connection is established it is
    saved in `request.registry`.

    Parameters:

    ``request``
    The current pyramid request object

    ``settings``
    A dict of keyword args to be passed straight to `StrictRedis`

    Returns:

    An instance of `StrictRedis`
    """
    # use the connection from the registry if possible
    redis = getattr(request.registry, '_redis_sessions', None)

    # otherwise create a new connection and add it to the registry
    if redis is None:
        redis = StrictRedis(**settings)
        setattr(request.registry, '_redis_sessions', redis)

    return redis

def get_connection_from_url(request, url, **settings):
    """
    """
    redis = getattr(request.registry, '_redis_sessions', None)

    if redis is None:
        # check how dogpile does it
        redis = StrictRedis.from_url(url, **settings)
        setattr(request.registry, '_redis_sessions', None)

    return redis
