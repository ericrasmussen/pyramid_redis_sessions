.. _front:

======================
pyramid_redis_sessions
======================
This package provides a fast and stable implementation of Pyramid's `ISession
interface <http://docs.pylonsproject.org/projects/pyramid/en/latest/api/interfaces.html#pyramid.interfaces.ISession>`_,
using Redis as its backend.

Special thanks to Chris McDonough for the original idea, inspiration, and some
borrowed code.


Why use Redis for your sessions
===============================
Redis is fast, widely deployed, and stable. It works best when your data can
fit in memory, but is configurable and still quite fast when you need to sync
to disk. There are plenty of existing benchmarks, opinion pieces, and articles
if you want to learn about its use cases. But for `pyramid_redis_sessions` I'm
interested in it specifically for these reasons:

* it really is bleeping fast (choose your own expletive)
* it has a very handy built-in mechanism for setting expirations on keys
* the watch mechanism is a nice, lightweight alternative to full transactions
* session data tends to be important but not mission critical, but if it is...
* it has configurable `persistence <http://redis.io/topics/persistence>`_


Why not use Redis for your sessions
===================================

While Redis is an good and proven technology there are some things to consider
before using it.

* additional complexity of upkeep of a Redis server
* if your sessions store data fast that doesn't need to be 100% consistent.
  (as Redis sync to desic "eventually")
* when you do not have enough memory to store all the session data for all your
  user. (Redis can only take as much data as it has memory available)


Narrative Documentation
=======================

.. toctree::
   :maxdepth: 2

   gettingstarted
   advanced
   api
   redis
   contributing


Support and Documentation
=========================
The official documentation is available at:
http://pyramid-redis-sessions.readthedocs.org/en/latest/index.html

You can report bugs or open support requests in the `github issue tracker
<https://github.com/ericrasmussen/pyramid_redis_sessions/issues>`_, or you can
discuss issues with me (erasmas) and other users in #pyramid on
irc.freenode.org.


Authors
=======
`Eric Rasmussen <http://github.com/ericrasmussen>`_ is the primary author, but
owes much to Chris McDonough and the fine folks from the Pyramid community. A
complete list of contributors is available in `CONTRIBUTORS.txt
<https://github.com/ericrasmussen/pyramid_redis_sessions/blob/master/CONTRIBUTORS.txt>`_.



License
=======
`pyramid_redis_sessions` is available under a FreeBSD-derived license. See
`LICENSE.txt <https://github.com/ericrasmussen/pyramid_redis_sessions/blob/master/LICENSE.txt>`_
for details.



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
