"""Regression tests: condition-based wrappers block only identical cache keys.

While one cached computation is held, callers for a *different* key must
proceed immediately, whether that key is a miss or an already-cached hit.
Same-key stampede suppression, hit/miss accounting, and pending-set cleanup
on exceptions must remain intact, for both @cached and @cachedmethod, with
info enabled and disabled.
"""

import threading
import time
import unittest

from cachetools import Cache, LRUCache, cached, cachedmethod

PROGRESS_TIMEOUT = 1.0  # generous bound; fixed code progresses in ~0s


class _Harness:
    """A condition-guarded function whose 'held' key blocks inside func."""

    def __init__(self, cache, info, method, blocked=("held",)):
        self.cache = cache
        self.cond = threading.Condition()
        self.entered = {}
        self.release = threading.Event()
        self.calls = []
        self._blocked = set(blocked)

        def body(key):
            self.calls.append(key)
            self.entered.setdefault(key, threading.Event()).set()
            if key in self._blocked:
                assert self.release.wait(5), "test never released held computation"
            return f"value:{key}"

        if method:

            class Owner:
                def __init__(self, cache, cond):
                    self.cache = cache
                    self.cond = cond

                @cachedmethod(
                    lambda self: self.cache,
                    condition=lambda self: self.cond,
                    info=info,
                )
                def run(self, key):
                    return body(key)

            self.f = Owner(cache, self.cond).run
        else:
            self.f = cached(cache, condition=self.cond, info=info)(body)

    def start(self, key):
        t = threading.Thread(target=self.f, args=(key,))
        t.start()
        assert self.entered.setdefault(key, threading.Event()).wait(2), (
            f"computation for {key!r} never started"
        )
        return t

    def finish(self, *threads):
        self.release.set()
        for t in threads:
            t.join(5)


class IndependentKeyTests(unittest.TestCase):
    def _exercise(self, info, method, cache_factory, hot):
        h = _Harness(cache_factory(), info, method)
        if hot:
            h.f("other")
        baseline = h.calls.count("other")
        holder = h.start("held")
        result = {}

        def call_other():
            result["value"] = h.f("other")

        other = threading.Thread(target=call_other)
        other.start()
        try:
            other.join(PROGRESS_TIMEOUT)
            self.assertFalse(
                other.is_alive(),
                f"unrelated {'hit' if hot else 'miss'} blocked behind held key "
                f"(info={info}, method={method})",
            )
            self.assertEqual(result.get("value"), "value:other")
            # a hit must not call the wrapped function for an unrelated key
            self.assertEqual(h.calls.count("other"), baseline + (0 if hot else 1))
        finally:
            h.finish(holder, other)
        self.assertFalse(holder.is_alive() or other.is_alive())
        self.assertEqual(h.calls.count("held"), 1)

        # the held key itself is memoized once it completes
        self.assertEqual(h.f("held"), "value:held")
        self.assertEqual(h.calls.count("held"), 1)

    def test_unrelated_key_progresses(self):
        for info in (False, True):
            for method in (False, True):
                for hot in (False, True):
                    for cache_factory in (lambda: LRUCache(128), dict):
                        with self.subTest(
                            info=info,
                            method=method,
                            hot=hot,
                            cache=type(cache_factory()).__name__,
                        ):
                            self._exercise(info, method, cache_factory, hot)

    def test_unrelated_key_progresses_under_eviction_pressure(self):
        # LRUCache(1): only one entry can be resident, so a stall here cannot
        # be blamed on a populated cache either.
        for info in (False, True):
            for method in (False, True):
                with self.subTest(info=info, method=method):
                    h = _Harness(LRUCache(1), info, method)
                    holder = h.start("held")
                    other = threading.Thread(target=lambda: h.f("other"))
                    other.start()
                    try:
                        other.join(PROGRESS_TIMEOUT)
                        self.assertFalse(
                            other.is_alive(),
                            "unrelated key blocked under eviction pressure",
                        )
                    finally:
                        h.finish(holder, other)


class SameKeySemanticsTests(unittest.TestCase):
    def test_same_key_stampede_suppression(self):
        for info in (False, True):
            with self.subTest(info=info):
                calls = []
                cond = threading.Condition()
                start = threading.Event()
                release = threading.Event()

                @cached(Cache(20), condition=cond, info=info)
                def f(k):
                    calls.append(k)
                    start.set()
                    release.wait(5)
                    return k

                workers = [threading.Thread(target=lambda: f(4)) for _ in range(5)]
                try:
                    for w in workers:
                        w.start()
                    self.assertTrue(start.wait(2))
                    time.sleep(0.05)
                finally:
                    release.set()
                    for w in workers:
                        w.join(5)
                self.assertEqual(calls, [4])
                self.assertTrue(all(not w.is_alive() for w in workers))
                if info:
                    self.assertEqual(f.cache_info().misses, 1)
                    self.assertEqual(f.cache_info().hits, 4)

    def test_same_key_method_stampede_suppression(self):
        for info in (False, True):
            with self.subTest(info=info):
                calls = []
                cond = threading.Condition()
                start = threading.Event()
                release = threading.Event()

                class Owner:
                    def __init__(self):
                        self.cache = Cache(20)
                        self.cond = cond

                    @cachedmethod(
                        lambda self: self.cache,
                        condition=lambda self: self.cond,
                        info=info,
                    )
                    def run(self, k):
                        calls.append(k)
                        start.set()
                        release.wait(5)
                        return k

                owner = Owner()
                workers = [
                    threading.Thread(target=lambda: owner.run(4)) for _ in range(5)
                ]
                try:
                    for w in workers:
                        w.start()
                    self.assertTrue(start.wait(2))
                    time.sleep(0.05)
                finally:
                    release.set()
                    for w in workers:
                        w.join(5)
                self.assertEqual(calls, [4])
                self.assertTrue(all(not w.is_alive() for w in workers))

    def test_exception_cleanup(self):
        for info in (False, True):
            for method in (False, True):
                with self.subTest(info=info, method=method):
                    attempts = []
                    cond = threading.Condition()
                    if method:

                        class Owner:
                            def __init__(self):
                                self.cache = Cache(20)
                                self.cond = cond

                            @cachedmethod(
                                lambda self: self.cache,
                                condition=lambda self: self.cond,
                                info=info,
                            )
                            def run(self, k):
                                attempts.append(k)
                                if len(attempts) == 1:
                                    raise ValueError("original failure")
                                return k

                        f = Owner().run
                    else:

                        @cached(Cache(20), condition=cond, info=info)
                        def f(k):
                            attempts.append(k)
                            if len(attempts) == 1:
                                raise ValueError("original failure")
                            return k

                    with self.assertRaises(ValueError):
                        f(3)
                    # no deadlock, and the failed attempt did not poison the key
                    self.assertEqual(f(3), 3)
                    self.assertEqual(attempts, [3, 3])


class DistinctKeyConcurrencyTests(unittest.TestCase):
    def test_distinct_misses_compute_concurrently(self):
        for info in (False, True):
            for method in (False, True):
                with self.subTest(info=info, method=method):
                    h = _Harness(LRUCache(128), info, method, blocked=("a", "b"))
                    ta = h.start("a")
                    tb = h.start("b")  # must start while 'a' is still held
                    self.assertEqual(sorted(h.calls[:2]), ["a", "b"])
                    h.finish(ta, tb)
                    self.assertFalse(ta.is_alive() or tb.is_alive())

    def test_interleaved_hit_while_pending(self):
        h = _Harness(LRUCache(128), info=False, method=False)
        h.f("other")  # warm the cache
        holder = h.start("held")
        try:

            def hit():
                h.f("other")

            t = threading.Thread(target=hit)
            t.start()
            t.join(PROGRESS_TIMEOUT)
            self.assertFalse(t.is_alive(), "cached key blocked while held")
            self.assertEqual(h.calls.count("other"), 1)  # warm-up call only
        finally:
            h.finish(holder)


if __name__ == "__main__":
    unittest.main()
