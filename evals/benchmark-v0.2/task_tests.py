"""Canonical held-out contracts, also exposed as task checks before each phase."""
import threading,time,unittest
from cachetools import Cache,LRUCache,cached,cachedmethod

class DebugTests(unittest.TestCase):
    def exercise(self,info,method,hot=False):
        entered=threading.Event();release=threading.Event();other=threading.Event()
        calls=[];cache=LRUCache(128);cond=threading.Condition();errors=[]
        def body(key):
            calls.append(key)
            if key=='held':entered.set();release.wait(4)
            if key=='other':other.set()
            return key
        if method:
            class Owner:
                def __init__(self):self.cache=cache;self.cond=cond
                @cachedmethod(lambda self:self.cache,condition=lambda self:self.cond,info=info)
                def run(self,key):return body(key)
            f=Owner().run
        else:f=cached(cache,condition=cond,info=info)(body)
        if hot:f('other');other.clear()
        def call(key):
            try:f(key)
            except Exception as e:errors.append(repr(e))
        first=threading.Thread(target=call,args=('held',));second=threading.Thread(target=call,args=('other',))
        try:
            first.start();self.assertTrue(entered.wait(2));second.start()
            if hot:
                second.join(1);self.assertFalse(second.is_alive(),'cached unrelated key blocked although no eviction occurs')
            else:self.assertTrue(other.wait(1),'unrelated cache miss blocked although no eviction occurs')
        finally:
            release.set();first.join(5);second.join(5)
        self.assertFalse(errors,errors)
        self.assertFalse(first.is_alive() or second.is_alive())
        self.assertEqual(calls.count('held'),1)
    def test_independent_keys_and_cached_hits(self):
        for info in [False,True]:
            for method in [False,True]:
                for hot in [False,True]:
                    with self.subTest(info=info,method=method,hot=hot):self.exercise(info,method,hot)
    def test_same_key_suppression_and_exception_cleanup(self):
        for info in [False,True]:
            calls=[];cond=threading.Condition();start=threading.Event();release=threading.Event()
            @cached(Cache(20),condition=cond,info=info)
            def f(k):calls.append(k);start.set();release.wait(2);return k
            workers=[threading.Thread(target=lambda:f(4)) for _ in range(5)]
            try:
                for w in workers:w.start()
                self.assertTrue(start.wait(1));time.sleep(.03)
            finally:
                release.set()
                for w in workers:w.join(3)
            self.assertEqual(calls,[4]);self.assertTrue(all(not w.is_alive() for w in workers))
            if info:self.assertEqual(f.cache_info().misses,1)
            attempts=[]
            @cached(Cache(20),condition=threading.Condition(),info=info)
            def g(k):
                attempts.append(k)
                if len(attempts)==1:raise ValueError('original failure')
                return k
            with self.assertRaises(ValueError):g(3)
            self.assertEqual(g(3),3)

class EnvironmentTests(unittest.TestCase):
    def test_existing_product_contract(self):
        c=LRUCache(3);c['a']=1;c['b']=2;c['c']=3
        self.assertEqual(c['a'],1);c['d']=4
        self.assertNotIn('b',c);self.assertEqual(c.currsize,3)
        self.assertEqual(c.pop('missing',99),99)
        c.clear();self.assertEqual(len(c),0)

class FreshStageOne(unittest.TestCase):
    def test_bulk_removal(self):
        c=Cache(20,getsizeof=len);a=[];c['a']='AA';c['b']='BBB';c['c']='C'
        result=c.pop_many(iter(['b','missing','b','a']))
        self.assertEqual(result,[('b','BBB'),('a','AA')]);self.assertEqual(list(c.items()),[('c','C')]);self.assertEqual(c.currsize,1)
    def test_no_missing_side_effect(self):
        class Auto(Cache):
            def __missing__(self,k):raise AssertionError('must not trigger __missing__')
        c=Auto(5);self.assertEqual(c.pop_many(['x','x']),[])
        self.assertEqual(c.pop_many([]),[])

class FreshStageTwo(FreshStageOne):
    def test_strict_is_atomic(self):
        c=Cache(10,getsizeof=len);c['a']='AAA';c['b']='BB';before=tuple(c.items())
        with self.assertRaises(KeyError):c.pop_many(['a','missing','b'],strict=True)
        self.assertEqual(tuple(c.items()),before);self.assertEqual(c.currsize,5)
        self.assertEqual(c.pop_many(['a','a'],strict=True),[('a','AAA')]);self.assertEqual(c.currsize,2)
    def test_iterator_failure_does_not_partially_remove(self):
        c=Cache(5);c['a']=1
        def keys():yield 'a';raise RuntimeError('input failed')
        with self.assertRaises(RuntimeError):c.pop_many(keys(),strict=True)
        self.assertEqual(c['a'],1)
    def test_keyword_signature(self):
        import inspect
        p=inspect.signature(Cache.pop_many).parameters['strict']
        self.assertEqual(p.kind,inspect.Parameter.KEYWORD_ONLY);self.assertIs(p.default,False)

class RecoveryStageOne(unittest.TestCase):
    def test_snapshot_is_shallow_immutable_and_non_mutating(self):
        c=Cache(10,getsizeof=len);v=['a','b'];c['x']=v;c['z']=[3]
        before=c.currsize;result=c.snapshot()
        self.assertIsInstance(result,tuple);self.assertEqual(result,(('x',v),('z',[3])))
        self.assertIs(result[0][1],v);self.assertEqual(c.currsize,before)
        c['later']=[];self.assertEqual(len(result),2)
    def test_empty_and_order(self):
        c=Cache(4);self.assertEqual(c.snapshot(),())
        for k in [2,1,3]:c[k]=k
        self.assertEqual(c.snapshot(),((2,2),(1,1),(3,3)))

class RecoveryStageTwo(RecoveryStageOne):
    def test_restore_replaces_and_preserves_identity_and_size(self):
        c=Cache(9,getsizeof=len);c['old']=[0];v=[1,2,3]
        self.assertIsNone(c.restore(iter([('new',v),('x',[8])])) )
        self.assertEqual(tuple(c.items()),(('new',v),('x',[8])));self.assertIs(c['new'],v);self.assertEqual(c.currsize,4)
        c.restore([]);self.assertEqual(len(c),0);self.assertEqual(c.currsize,0)
    def test_invalid_snapshots_are_atomic(self):
        invalid=[ [('a','x'),('a','y')], [('x',)], ['xy'], [([],1)], [('huge','x'*20)] ]
        for value in invalid:
            c=Cache(5,getsizeof=len);c['before']='AA';old=c.snapshot()
            with self.assertRaises((TypeError,ValueError)):c.restore(value)
            self.assertEqual(c.snapshot(),old);self.assertEqual(c.currsize,2)
        c=Cache(8);c['before']=1
        def broken():yield ('x',3);raise RuntimeError('source failure')
        with self.assertRaises(RuntimeError):c.restore(broken())
        self.assertEqual(c.snapshot(),(('before',1),))
    def test_getsizeof_failure_before_any_mutation(self):
        def size(v):
            if v=='BAD':raise ValueError('rejected')
            return len(v)
        c=Cache(8,getsizeof=size);c['before']='AA'
        with self.assertRaises(ValueError):c.restore([('x','A'),('y','BAD')])
        self.assertEqual(c.snapshot(),(('before','AA'),));self.assertEqual(c.currsize,2)

CLASSES={'D1':{1:DebugTests,2:DebugTests},'E1':{1:EnvironmentTests,2:EnvironmentTests},
         'F1':{1:FreshStageOne,2:FreshStageTwo},'R1':{1:RecoveryStageOne,2:RecoveryStageTwo}}

def run(task,phase):
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CLASSES[task][int(phase)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful(),result.testsRun

if __name__=='__main__':
    import sys
    ok,n=run(sys.argv[1],sys.argv[2]);sys.exit(0 if ok else 1)
