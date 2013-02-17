Contributing
============

Feature Additions/Requests
--------------------------
I'm very interested in discussing use cases that `pyramid_redis_sessions`
doesn't cover but that you'd like to see in your session library.

If you have an idea you want to discuss further, ping me (erasmas) on freenode
in #pyramid, or you're also welcome to submit a pull request.

However, I do ask that you make the request on a new feature.<your feature>
branch so that I can spend some time testing the code before merging to master.


Notes on Testing
----------------
The test suite is written in a way that may be unusual to some, so if you submit
a patch I only ask that you follow the testing methodology employed here. On a
technical level it boils down to:

#. Parameterizing classes or functions that connect to outside systems
#. In tests, supplying dummy instances of those classes


In practice this means never hardcoding a redis-py `StrictRedis` instance in
`pyramid_redis_sessions`, and always passing in instances of `DummyRedis` in
tests.

On a philosophical level I see outside processes as swappable strategies, and
the purpose of my code is to control how those strategies are employed. For
this reason tests in `pyramid_redis_session` should never need to use `Mock`.

