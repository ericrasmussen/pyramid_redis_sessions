.. _front:

======================
pyramid_redis_sessions
======================
This package provides a fast and stable implementation of Pyramid's `ISession
interface <http://docs.pylonsproject.org/projects/pyramid/en/latest/api/interfaces.html#pyramid.interfaces.ISession>`_,
using Redis as its backend.

Special thanks to Chris McDonough for the original idea, inspiration, and some
borrowed code.


When to Use Redis for Sessions
==============================

One of the main benefits of using a persistent store to serve session data is
separation of concerns. You can tell it what you want it do, ask for what you
want, and let it work out the details. In particular, Redis has several
benefits:

* built-in key expiration to automatically clean up expired session data
* no need for complicated/unpredictable lock handling in our python code
* a lightweight alternative to full transactions (the watch mechanism)


When Not to Use Redis for Sessions
==================================

Redis makes a compelling case for session data, but as with any technology
decision it's important to be aware of the trade-offs. Adding Redis to your
stack can mean:

* additional installation/configuration/maintenance (for the Redis server)
* speed before consistency (Redis is fast at the cost of syncing *eventually*)
* the entirety of your session data must fit in memory

Typically these aren't concerns for sessions, because critical data doesn't
usually belong in a session store. However, in specialized cases where you need
consistency at the cost of speed, you may consider database-backed
sessions. Alternatively, if you only ever store less than ~4kb of non-sensitive
data, cookie-based sessions work nicely without requiring you to add complexity
to your stack.


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
