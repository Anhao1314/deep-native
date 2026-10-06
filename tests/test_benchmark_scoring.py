"""Offline scoring regressions; never calls a model or modifies Deep Native."""
import ast
import contextlib
import io
import json
import sys
import textwrap
import types
import unittest
from pathlib import Path
from unittest.mock import patch

BENCH = Path(__file__).resolve().parents[1] / 'evals/benchmark-v1'
sys.path.insert(0, str(BENCH))
import acceptance
from fixtures import TASKS, check_script, manifest


def padded(iterable, n, fillvalue=None, *, pad=True):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError('n must be an integer')
    if n <= 0:
        raise ValueError('n must be positive')
    source = iter(iterable)
    while True:
        chunk = []
        for _ in range(n):
            try:
                chunk.append(next(source))
            except StopIteration:
                break
        if not chunk:
            return
        yield chunk + [fillvalue] * (n - len(chunk)) if pad else chunk


def runs(iterable, key=None, *, max_run=None):
    if max_run is not None:
        if isinstance(max_run, bool) or not isinstance(max_run, int):
            raise TypeError('max_run must be an integer')
        if max_run <= 0:
            raise ValueError('max_run must be positive')
    group = []
    current = None
    for item in iterable:
        value = item if key is None else key(item)
        if group and (value != current or (max_run is not None and len(group) == max_run)):
            yield current, tuple(group)
            group = []
        current = value
        group.append(item)
    if group:
        yield current, tuple(group)


class ScoringContracts(unittest.TestCase):
    def test_manifest_matches_source_and_declares_allowed_files(self):
        self.assertEqual(json.loads((BENCH / 'tasks.json').read_text()), manifest())
        expected = {'more_itertools/more.py', 'more_itertools/more.pyi',
                    'more_itertools/__init__.py', 'more_itertools/__init__.pyi'}
        for task in TASKS:
            with self.subTest(task=task['id']):
                for name in task['files']:
                    self.assertIn(name, task['prompt'])
                if task['repo'] == 'more':
                    self.assertEqual(set(task['files']), expected)
        self.assertEqual({t['id'] for t in TASKS if t.get('regression_tests_required')},
                         {'T05', 'T08', 'T10'})

    def test_visible_runner_supports_pytest_and_unittest_regressions(self):
        for task in TASKS:
            script = check_script(task)
            self.assertIn("[sys.executable, '-m', 'pytest', '-q', 'agent_tests']", script)
            self.assertNotIn("'discover', '-s', 'agent_tests'", script)

    def test_one_input_loop_allows_reduction_comprehension_and_alias(self):
        source = '''
            def map_reduce(iterable, keyfunc, valuefunc=None, reducefunc=None):
                source = iter(iterable)
                ret = defaultdict(list)
                for item in source:
                    ret[keyfunc(item)].append(item if valuefunc is None else valuefunc(item))
                if reducefunc is not None:
                    ret = defaultdict(None, {key: reducefunc(values) for key, values in ret.items()})
                ret.default_factory = None
                return ret
        '''
        fn = ast.parse(textwrap.dedent(source)).body[0]
        self.assertEqual(acceptance.input_accumulation_loops(fn), 1)

    def test_duplicated_input_accumulation_is_rejected(self):
        source = '''
            def map_reduce(iterable, keyfunc, valuefunc=None, reducefunc=None):
                ret = defaultdict(list)
                if valuefunc is None:
                    for item in iterable:
                        ret[keyfunc(item)].append(item)
                else:
                    for item in iterable:
                        ret[keyfunc(item)].append(valuefunc(item))
                if reducefunc is not None:
                    for key, values in ret.items():
                        ret[key] = reducefunc(values)
                return ret
        '''
        fn = ast.parse(textwrap.dedent(source)).body[0]
        self.assertEqual(acceptance.input_accumulation_loops(fn), 2)

    def check_with_api(self, task_id, name, function, phase=2):
        module = types.ModuleType('more_itertools')
        setattr(module, name, function)
        with patch.dict(sys.modules, {'more_itertools': module}), contextlib.redirect_stdout(io.StringIO()):
            acceptance.check(task_id, phase)

    def test_keyword_only_pad_is_required_only_in_second_stage(self):
        def positional(iterable, n, fillvalue=None, pad=True):
            return padded(iterable, n, fillvalue, pad=pad)
        self.check_with_api('T09', 'chunked_padded', positional, phase=1)
        with self.assertRaises(AssertionError):
            self.check_with_api('T09', 'chunked_padded', positional, phase=2)
        self.check_with_api('T09', 'chunked_padded', padded, phase=2)

    def test_validation_after_consumption_is_rejected(self):
        def eager(iterable, key=None, *, max_run=None):
            values = list(iterable)
            return runs(values, key, max_run=max_run)
        with self.assertRaisesRegex(AssertionError, 'consumed input before validation'):
            self.check_with_api('T10', 'partition_runs', eager)
        self.check_with_api('T10', 'partition_runs', runs)


if __name__ == '__main__':
    unittest.main()
