Redis Notes
===========

Installing Redis
----------------
The best place to start is the Redis `quick start guide <http://redis.io/topics/quickstart>`_.

If you need automated deployment with your application, you can find guides
online for Redis deployment via buildout, puppet, chef, etc. If anyone would
like to compile a list of recipes for these deployment options, I wholly
encourage pull requests with links.

Discussions of Redis security are outside the purview of these docs, but it's
worth noting that Redis will listen on all interfaces by default, potentially
exposing your data to the world. You can avoid this with a bind declaration in
your redis.conf file such as::

    bind 127.0.0.1


You can read more in a blog post discussing this issue `here
<http://blog.liftsecurity.io/post/32770744557/that-thing-where-you-didnt-change-the-redis-default>`_.
