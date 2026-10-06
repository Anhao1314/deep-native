"""Frozen, curated maintenance tasks on two real upstream repositories.

Seeded regressions and injected infrastructure failures are explicitly labelled.
These are not historical issue-resolution tasks or a population sample.
"""
import json
from pathlib import Path

REPOS = {
    'boltons': {'url': 'https://github.com/mahmoud/boltons.git',
                'commit': '4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d'},
    'more': {'url': 'https://github.com/more-itertools/more-itertools.git',
             'commit': '1ea82a711c69f590054987b5cb194157f8ce8ac4'},
}
SUFFIX = '''
Work only on the requested functionality, its documentation, and new regression tests under agent_tests/. Do not change or remove existing tests, benchmark_check.py, benchmark_tests.py, or repository configuration; do not skip tests, hard-code examples, or fetch benchmark answers. You may inspect the repository and use its local tools. The available check command is python3 benchmark_check.py. End your final response with STATUS: DONE if you consider the requested work complete, or STATUS: BLOCKED otherwise.
'''

TASKS = [
 dict(id='T01', category='simple_bug_fix', repo='boltons', seeded=True,
      files=['boltons/strutils.py'],
      prompt='Fix ordinalize in boltons.strutils. A regression gives the wrong English ordinal suffix for teen numbers and numbers ending in the twenties. Preserve its existing string and ext_only behavior.'),
 dict(id='T02', category='edge_case_validation', repo='more', seeded=False,
      files=['more_itertools/more.py'],
      prompt='Tighten chunked size validation: n may be an integer or None, but bool and non-integer values must raise TypeError before consuming the input iterable. Preserve n=0, n=None, negative-integer ValueError, strict behavior, and existing valid outputs. Document the accepted types.'),
 dict(id='T03', category='cross_file_bug', repo='more', seeded=True,
      files=['more_itertools/more.py', 'more_itertools/__init__.py'],
      prompt='Fix windowed_complete: its public package import produces the wrong tuple structure, and the implementation drops an item from each suffix. The public and module imports must both yield (prefix, window, suffix) tuples whose concatenation is the original sequence. Preserve zero-width windows and validation.'),
 dict(id='T04', category='feature_implementation', repo='boltons', seeded=False,
      files=['boltons/strutils.py'],
      prompt='Extend parse_int_list to signed integers and signed inclusive ranges, including -3--1, +2-+4, reversed endpoints, and whitespace around tokens and endpoints. Preserve sorting, duplicate entries, empty input and custom literal delimiters. Malformed ranges must raise ValueError. Update its docstring.'),
 dict(id='T05', category='refactor_regression', repo='more', seeded=False,
      files=['more_itertools/more.py'],
      prompt='Refactor map_reduce to remove the duplicated accumulation loops for valuefunc being None versus supplied: use one accumulation loop, then the existing optional reduction phase. Preserve callback order, single-pass iterator consumption, insertion order, exception propagation, and the defaultdict with default_factory None. Add regression protection under agent_tests/.'),
 dict(id='T06', category='unfamiliar_repository', repo='boltons', seeded=True,
      files=['boltons/iterutils.py'],
      prompt='Investigate why get_path on nested mappings unexpectedly looks up later path segments at the outer root. Repair the lookup while preserving dotted list-index paths, tuple paths, defaults and PathAccessError details. Keep the fix focused.'),
 dict(id='T07', category='error_recovery', repo='more', seeded=False,
      files=['more_itertools/more.py'], transient_failure=True,
      prompt='Start by running python3 benchmark_check.py. Then add a public take_until_inclusive(iterable, pred) iterator: yield through the first item whose predicate is true, including that item, and stop without consuming any later items. Empty input stays empty; predicate is evaluated once per encountered item. Export it from the package and document it. The check environment may have a transient startup failure; complete the task using the available local tools.'),
 dict(id='T08', category='multi_step_long_horizon', repo='boltons', seeded=False,
      files=['boltons/strutils.py', 'boltons/rangeutils.py'],
      prompt='Build boltons.rangeutils with parse_ranges(text) and format_ranges(values), supporting signed integers, comma-separated inclusive ranges (including -3--1 and reversed endpoints), sorted unique results, and canonical compact formatting. Reuse and extend strutils.parse_int_list / format_int_list rather than duplicating the parser. Add a CLI: python3 -m boltons.rangeutils expand TEXT outputs a JSON integer list; compact TEXT (a comma-separated integer list) outputs canonical range text. Malformed input must exit nonzero without a traceback. Document and add regression tests for the API and CLI.'),
 dict(id='T09', category='verification_staleness', repo='more', seeded=False,
      files=['more_itertools/more.py'], phases=True,
      prompt='Add and export chunked_padded(iterable, n, fillvalue=None): yield lists of length n, padding only the final nonempty chunk with fillvalue. Empty input yields nothing; n must be a positive integer and bool/non-integer values raise TypeError. Preserve fillvalue object identity and laziness. Document the API.',
      continuation='Now extend the same chunked_padded API with keyword-only pad=True. With pad=False, yield a short final chunk without padding; the default behavior remains padded. This changes the requested code after the first stage. Document the option and complete the updated task. End with STATUS: DONE or STATUS: BLOCKED.'),
 dict(id='T10', category='interruption_recovery', repo='more', seeded=False,
      files=['more_itertools/more.py'], recovery=True,
      prompt='Add and export partition_runs(iterable, key=None, *, max_run=None): yield (key_value, tuple_of_items) for contiguous equal-key runs. Default key is identity. Evaluate key exactly once per input item and consume the iterable once. If max_run is a positive integer, split long runs into groups of at most that size; None means unlimited. Reject bool/non-integer max_run with TypeError and nonpositive integers with ValueError before consuming input. Preserve item identity, empty input, and callback exception propagation. Document and add regression tests under agent_tests/.'),
]
for task in TASKS:
    task['prompt'] += SUFFIX

def seed(root, task):
    """Deterministic faults; applied before the identical fixture commit."""
    changes = {
      'T01': ('boltons/strutils.py', "if numstr[-2] == '1':", "if numstr[-2] == '2':"),
      'T03': ('more_itertools/more.py', 'end = seq[i + n :]', 'end = seq[i + n + 1 :]'),
      'T06': ('boltons/iterutils.py', 'cur = cur[seg]', 'cur = root[seg]'),
    }
    if task['id'] in changes:
        name, old, new = changes[task['id']]
        p = root / name
        text = p.read_text()
        assert old in text
        p.write_text(text.replace(old, new, 1))
    if task['id'] == 'T03':
        p = root / 'more_itertools/__init__.py'
        p.write_text(p.read_text() + '\nfrom .more import windowed as windowed_complete\n')

def check_script(task):
    transient = '''
marker = Path('.check-started')
if not marker.exists():
    marker.touch()
    print('Transient check-service startup failure. Retry this same command.', file=sys.stderr)
    sys.exit(69)
''' if task.get('transient_failure') else ''
    return '''import subprocess, sys
from pathlib import Path
''' + transient + '''
commands = [[sys.executable, 'benchmark_tests.py']]
''' + ("commands.append([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'])\n"
       if task['repo'] == 'more' else
       "commands.append([sys.executable, '-m', 'pytest', '-q', 'tests/test_strutils.py', 'tests/test_iterutils.py'])\n") + '''
if Path('agent_tests').exists():
    commands.append([sys.executable, '-m', 'unittest', 'discover', '-s', 'agent_tests'])
for command in commands:
    code = subprocess.call(command)
    if code: sys.exit(code)
'''

def visible_tests(task):
    snippets = {
    'T01': "from boltons.strutils import ordinalize\nassert ordinalize(11) == '11th'\nassert ordinalize(22) == '22nd'\nassert ordinalize('hi') == 'hi'",
    'T02': "from more_itertools import chunked\ntry: chunked(iter([1]), True)\nexcept TypeError: pass\nelse: raise AssertionError('bool size accepted')\nassert list(chunked(range(5), 2)) == [[0,1],[2,3],[4]]",
    'T03': "from more_itertools import windowed_complete\nassert list(windowed_complete(range(3), 1)) == [((),(0,),(1,2)),((0,),(1,),(2,)),((0,1),(2,),())]",
    'T04': "from boltons.strutils import parse_int_list\nassert parse_int_list('-3--1,+2-+4') == [-3,-2,-1,2,3,4]",
    'T05': "from more_itertools import map_reduce\nassert map_reduce('abb', str.upper, reducefunc=len) == {'A':1,'B':2}",
    'T06': "from boltons.iterutils import get_path\nassert get_path({'a':{'b':7}}, ('a','b')) == 7",
    'T07': "from more_itertools import take_until_inclusive\nassert list(take_until_inclusive(range(6), lambda x:x==2)) == [0,1,2]",
    'T08': "from boltons.rangeutils import parse_ranges, format_ranges\nassert parse_ranges('-3--1,2,2') == [-3,-2,-1,2]\nassert format_ranges([-3,-2,-1,2,2]) == '-3--1,2'",
    'T09': "from more_itertools import chunked_padded\nassert list(chunked_padded(range(5),3)) == [[0,1,2],[3,4,None]]",
    'T10': "from more_itertools import partition_runs\nassert list(partition_runs('aab')) == [('a',('a','a')),('b',('b',))]\nassert list(partition_runs('aaaa',max_run=3)) == [('a',('a','a','a')),('a',('a',))]",
    }
    return snippets[task['id']] + "\nprint('Visible acceptance checks passed')\n"

def manifest():
    return {'schema': 1, 'repositories': REPOS, 'tasks': TASKS,
            'planned_runs': 60, 'repeats': 3, 'seed': 20261006,
            'budget': {'wall_seconds': 480, 'assistant_turns': 24},
            'treatment_activation': 'Use the installed deep-native skill for this task.'}

if __name__ == '__main__':
    Path(__file__).with_name('tasks.json').write_text(json.dumps(manifest(), indent=2) + '\n')
