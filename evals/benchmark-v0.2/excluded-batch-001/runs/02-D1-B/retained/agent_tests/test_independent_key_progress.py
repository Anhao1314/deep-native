"""Regression tests for independent-key progress with condition-based caching.

The ``condition`` argument of ``@cached``/``@cachedmethod`` suppresses
concurrent execution of the wrapped function or method with *identical*
parameters, i.e. cache keys (see docs/index.rst).  A regression made the
wrappers wait for *any* pending computation (``wait_for(lambda: not pending)``),
which serialized unrelated keys and even stalled callers of already cached
values.

These tests pin the documented behavior for both decorators, with ``info``
enabled and disabled, without weakening the same-key stampede suppression,
hit/miss accounting, or exception cleanup.
"""

import threading
import time
import unittest

from cachetools import LRUCache, cached, cachedmethod


def make_cached(body, info, cond, cache=None):
    if cache is None:
        cache = LRUCache(128)
    return cached(cache, condition=cond, info=info)(body), cache


def make_cachedmethod(body, info, cond, cache=None):
    if cache is None:
        cache = LRUCache(128)

    class Owner:
        def __init__(self):
            self.cache = cache
            self.cond = cond

        @cachedmethod(
            lambda self: self.cache,
            condition=lambda self: self.cond,
            info=info,
        )
        def run(self, key):
            return body(key)

    return Owner().run, cache


class IndependentKeyProgressTest(unittest.TestCase):
    """A held computation must not stall callers for a different key."""

    DECORATORS = (make_cached, make_cachedmethod)

    TIMEOUT = 5

    def exercise(self, factory, info, hot):
        entered = threading.Event()
        release = threading.Event()
        cond = threading.Condition()
        calls = []
        errors = []
        results = {}

        def body(key):
            calls.append(key)
            if key == "held":
                entered.set()
                release.wait(self.TIMEOUT)
            return key

        f, cache = factory(body, info, cond)
        if hot:
            self.assertEqual(f("other"), "other")
            calls.clear()

        def call(key, done):
            try:
                results[key] = f(key)
            except BaseException as exc:  # pragma: no cover - failure path
                errors.append(repr(exc))
            finally:
                done.set()

        first_done = threading.Event()
        second_done = threading.Event()
        first = threading.Thread(target=call, args=("held", first_done), daemon=True)
        second = threading.Thread(target=call, args=("other", second_done), daemon=True)
        try:
            first.start()
            self.assertTrue(entered.wait(self.TIMEOUT), "held call did not run")
            second.start()
            # An unrelated key must make progress while "held" is still pending.
            self.assertTrue(
                second_done.wait(self.TIMEOUT),
                "caller of a different key stalled behind a held computation",
            )
            self.assertTrue(
                first.is_alive(),
                "held computation finished, test did not exercise concurrency",
            )
            if hot:
                self.assertEqual(
                    calls, ["held"], "cached value was recomputed instead of returned"
                )
        finally:
            release.set()
            first.join(self.TIMEOUT)
            second.join(self.TIMEOUT)

        self.assertFalse(first.is_alive() or second.is_alive())
        self.assertFalse(errors, errors)
        self.assertEqual(results, {"held": "held", "other": "other"})
        self.assertEqual(calls.count("held"), 1)
        if hot:
            self.assertEqual(calls.count("other"), 0)
        self.assertEqual(len(cache), 2)
        if info:
            stats = f.cache_info()
            self.assertEqual(stats.misses, 2)
            self.assertEqual(stats.hits, 1 if hot else 0)

    def test_independent_key_progress(self):
        for factory in self.DECORATORS:
            for info in (False, True):
                for hot in (False, True):
                    with self.subTest(
                        decorator=factory.__name__, info=info, hot=hot
                    ):
                        self.exercise(factory, info, hot)

    def test_distinct_keys_compute_concurrently(self):
        # If unrelated keys were serialized, the two bodies could never
        # reach the barrier at the same time.
        for factory in self.DECORATORS:
            for info in (False, True):
                with self.subTest(decorator=factory.__name__, info=info):
                    barrier = threading.Barrier(2, timeout=self.TIMEOUT)
                    errors = []

                    def body(key):
                        if key in ("left", "right"):
                            barrier.wait()
                        return key

                    f, _ = factory(body, info, threading.Condition())

                    def call(key):
                        try:
                            f(key)
                        except BaseException as exc:
                            errors.append(repr(exc))

                    threads = [
                        threading.Thread(target=call, args=(key,), daemon=True)
                        for key in ("left", "right")
                    ]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join(self.TIMEOUT)
                    self.assertFalse(
                        any(thread.is_alive() for thread in threads),
                        "distinct keys were serialized",
                    )
                    self.assertFalse(errors, errors)

    def test_same_key_stampede_suppressed(self):
        for factory in self.DECORATORS:
            for info in (False, True):
                with self.subTest(decorator=factory.__name__, info=info):
                    entered = threading.Event()
                    release = threading.Event()
                    calls = []
                    errors = []

                    def body(key):
                        calls.append(key)
                        entered.set()
                        release.wait(self.TIMEOUT)
                        return key

                    f, _ = factory(body, info, threading.Condition())

                    def call():
                        try:
                            f(7)
                        except BaseException as exc:  # pragma: no cover
                            errors.append(repr(exc))

                    holder = threading.Thread(target=call, daemon=True)
                    waiters = [
                        threading.Thread(target=call, daemon=True) for _ in range(3)
                    ]
                    try:
                        holder.start()
                        self.assertTrue(entered.wait(self.TIMEOUT))
                        for waiter in waiters:
                            waiter.start()
                        time.sleep(0.3)
                        self.assertEqual(
                            calls, [7], "concurrent identical calls were not suppressed"
                        )
                    finally:
                        release.set()
                        for thread in [holder, *waiters]:
                            thread.join(self.TIMEOUT)

                    self.assertFalse(errors, errors)
                    self.assertEqual(calls, [7])
                    self.assertTrue(
                        all(not thread.is_alive() for thread in [holder, *waiters])
                    )
                    if info:
                        stats = f.cache_info()
                        self.assertEqual(stats.misses, 1)
                        self.assertEqual(stats.hits, 3)

    def test_same_key_waiter_recovers_from_failure(self):
        # A failed computation must release waiters and clean up pending
        # state so an identical call can retry instead of deadlocking.
        for factory in self.DECORATORS:
            for info in (False, True):
                with self.subTest(decorator=factory.__name__, info=info):
                    entered = threading.Event()
                    release = threading.Event()
                    attempts = []
                    errors = []
                    results = []

                    def body(key):
                        attempts.append(key)
                        if len(attempts) == 1:
                            entered.set()
                            release.wait(self.TIMEOUT)
                            raise ValueError("original failure")
                        return key

                    f, _ = factory(body, info, threading.Condition())

                    def call():
                        try:
                            results.append(f(3))
                        except BaseException as exc:
                            errors.append(repr(exc))

                    holder = threading.Thread(target=call, daemon=True)
                    waiter = threading.Thread(target=call, daemon=True)
                    try:
                        holder.start()
                        self.assertTrue(entered.wait(self.TIMEOUT))
                        waiter.start()
                        time.sleep(0.3)
                        self.assertEqual(
                            attempts, [3], "waiter ran the body while pending"
                        )
                    finally:
                        release.set()
                        holder.join(self.TIMEOUT)
                        waiter.join(self.TIMEOUT)

                    self.assertFalse(holder.is_alive() or waiter.is_alive())
                    self.assertEqual(len(errors), 1, errors)
                    self.assertIn("ValueError", errors[0])
                    self.assertEqual(results, [3])
                    self.assertEqual(attempts, [3, 3])
                    # pending state was cleaned up: the retried value is cached
                    self.assertEqual(f(3), 3)
                    self.assertEqual(attempts, [3, 3])


if __name__ == "__main__":
    unittest.main()
