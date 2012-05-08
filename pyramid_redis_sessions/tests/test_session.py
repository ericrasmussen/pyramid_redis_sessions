import unittest

from . import DummyRedis

class TestPyramidRedis(unittest.TestCase):
    def _makeOne(self, redis=None, session_id='session.id', timeout=300,
                 add_cookie=lambda sess: None, delete_cookie=lambda : None,
                 encode=lambda x: x, decode=lambda x: x):
        from ..pyramidsession import PyramidRedis
        if redis is None:
            redis = DummyRedis()
        return PyramidRedis(redis, session_id, timeout,
                            add_cookie, delete_cookie,
                            encode, decode)

    def test_created(self):
        import time
        before = time.time()
        inst = self._makeOne()
        created = inst.created
        after = time.time()
        self.assertLessEqual(before, created)
        self.assertGreaterEqual(after, created)

    def test_not_new(self):
        inst = self._makeOne()
        self.assertFalse(inst.new)

    def test_new(self):
        inst = self._makeOne()
        inst._v_new = True
        self.assertTrue(inst.new)

    def test_invalidate_dict(self):
        inst = self._makeOne()
        inst['key'] = 'val'
        inst.invalidate()
        self.assertNotIn('key', inst)

    def test_mutablevalue_changed(self):
        inst = self._makeOne()
        inst['a'] = {'1':1, '2':2}
        tmp = inst['a']
        tmp['3'] = 3
        inst.changed()
        from_redis = inst.from_redis()
        self.assertEqual(from_redis['a'], {'1':1, '2':2, '3':3})

    def test_csrf_token(self):
        inst = self._makeOne()
        new_token = inst.new_csrf_token()
        got_token = inst.get_csrf_token()
        self.assertEqual(new_token, got_token)

    def test_get_new_csrf_token(self):
        inst = self._makeOne()
        self.assertNotIn('_csrft_', inst)
        token = inst.get_csrf_token()
        self.assertEqual(inst['_csrft_'], token)

    def test_flash(self):
        inst = self._makeOne()
        inst.flash('message')
        msgs = inst.peek_flash()
        self.assertIn('message', msgs)

    def test_flash_alternate_queue(self):
        inst = self._makeOne()
        inst.flash('message', 'queue')
        default_queue = inst.peek_flash()
        self.assertNotIn('message', default_queue)
        other_queue = inst.peek_flash('queue')
        self.assertIn('message', other_queue)

    def test_pop_flash(self):
        inst = self._makeOne()
        inst.flash('message')
        popped = inst.pop_flash()
        self.assertIn('message', popped)
        msgs = inst.peek_flash()
        self.assertEqual(msgs, [])

    def test_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import ISession
        inst = self._makeOne()
        verifyObject(ISession, inst)

