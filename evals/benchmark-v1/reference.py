"""Offline grader validation only. Never copied to an agent workspace."""
from pathlib import Path

def replace_function(root,name,function,new_body):
    p=root/name;text=p.read_text();start=text.index('def '+function+'(')
    end=text.find('\ndef ',start+1)
    if end<0:end=len(text)
    p.write_text(text[:start]+new_body.strip()+'\n\n'+text[end:])

SIGNED_PARSER='''
def parse_int_list(range_string, delim=',', range_delim='-'):
    """Parse signed inclusive ranges, preserving duplicate entries."""
    import re
    pattern=re.compile(r'^([+-]?\\d+)\\s*(?:'+re.escape(range_delim)+r'\\s*([+-]?\\d+))?$')
    out=[]
    for token in range_string.split(delim):
        token=token.strip()
        if not token:continue
        match=pattern.fullmatch(token)
        if not match:raise ValueError('Malformed integer range')
        a=int(match.group(1))
        if match.group(2) is None:out.append(a)
        else:
            b=int(match.group(2));out.extend(range(min(a,b),max(a,b)+1))
    return sorted(out)
'''

def add_public(root,name,body):
    p=root/'more_itertools/more.py';text=p.read_text()
    text=text.replace('__all__ = [',"__all__ = [\n    '"+name+"',",1)
    p.write_text(text+'\n\n'+body.strip()+'\n')

def repair(root,task):
    tid=task['id']
    if tid=='T01':
        p=root/'boltons/strutils.py';p.write_text(p.read_text().replace("if numstr[-2] == '2':","if numstr[-2] == '1':",1))
    elif tid=='T02':
        p=root/'more_itertools/more.py';p.write_text(p.read_text().replace('    if n is not None and n < 0:',"    if n is not None and (isinstance(n, bool) or not isinstance(n, int)):\n        raise TypeError('n must be an integer or None')\n    if n is not None and n < 0:",1))
    elif tid=='T03':
        p=root/'more_itertools/more.py';p.write_text(p.read_text().replace('end = seq[i + n + 1 :]','end = seq[i + n :]'))
        p=root/'more_itertools/__init__.py';p.write_text(p.read_text().replace('\nfrom .more import windowed as windowed_complete\n','\n'))
    elif tid in ['T04','T08']:
        replace_function(root,'boltons/strutils.py','parse_int_list',SIGNED_PARSER)
        if tid=='T08':
            (root/'boltons/rangeutils.py').write_text('''"""Signed integer-range APIs and CLI."""
import json
import sys
from .strutils import parse_int_list, format_int_list
def parse_ranges(text):
    """Parse signed inclusive ranges into a sorted list of unique integers."""
    return sorted(set(parse_int_list(text)))
def format_ranges(values):
    """Format unique integers as canonical compact inclusive ranges."""
    return format_int_list(sorted(set(values)))
def main():
    try:
        if len(sys.argv)!=3:raise ValueError('Expected expand or compact and one argument')
        op,text=sys.argv[1:]
        if op=='expand':print(json.dumps(parse_ranges(text)))
        elif op=='compact':print(format_ranges([int(v.strip()) for v in text.split(',') if v.strip()]))
        else:raise ValueError('Unknown command')
    except ValueError as exc:
        print(str(exc),file=sys.stderr);return 2
    return 0
if __name__=='__main__':sys.exit(main())
''')
            tests=root/'agent_tests';tests.mkdir(exist_ok=True)
            (tests/'test_rangeutils.py').write_text('''import json
import subprocess
import sys
from boltons.rangeutils import parse_ranges, format_ranges

def test_api_roundtrip():
    values = [-3, -1, -2, 2, 2]
    assert format_ranges(values) == '-3--1,2'
    assert parse_ranges(format_ranges(values)) == [-3, -2, -1, 2]

def test_cli_roundtrip_and_malformed_input():
    good = subprocess.run([sys.executable, '-m', 'boltons.rangeutils', 'expand', '-3--1,2'], capture_output=True, text=True)
    assert good.returncode == 0
    assert json.loads(good.stdout) == [-3, -2, -1, 2]
    compact = subprocess.run([sys.executable, '-m', 'boltons.rangeutils', 'compact', '-3,-1,-2,2,2'], capture_output=True, text=True)
    assert compact.returncode == 0 and compact.stdout.strip() == '-3--1,2'
    bad = subprocess.run([sys.executable, '-m', 'boltons.rangeutils', 'expand', '1-bad'], capture_output=True, text=True)
    assert bad.returncode != 0 and 'Traceback' not in bad.stderr
''')
    elif tid=='T05':
        replace_function(root,'more_itertools/more.py','map_reduce','''
def map_reduce(iterable, keyfunc, valuefunc=None, reducefunc=None):
    """Accumulate once in input order, transform values, then optionally reduce."""
    ret=defaultdict(list)
    for item in iterable:
        key=keyfunc(item)
        ret[key].append(item if valuefunc is None else valuefunc(item))
    if reducefunc is not None:
        for key, values in ret.items():ret[key]=reducefunc(values)
    ret.default_factory=None
    return ret
''')
        tests=root/'agent_tests';tests.mkdir(exist_ok=True)
        (tests/'test_map_reduce.py').write_text('''import unittest
from more_itertools import map_reduce
class Regression(unittest.TestCase):
    def test_transform(self):
        self.assertEqual(map_reduce([1,2,3],lambda x:x%2,lambda x:x*2,sum),{1:8,0:4})
''')
    elif tid=='T06':
        p=root/'boltons/iterutils.py';p.write_text(p.read_text().replace('cur = root[seg]','cur = cur[seg]',1))
    elif tid=='T07':
        add_public(root,'take_until_inclusive','''
def take_until_inclusive(iterable,pred):
    """Yield through the first matching item without consuming later items."""
    for item in iterable:
        stop=pred(item)
        yield item
        if stop:return
''')
    elif tid=='T09':
        add_public(root,'chunked_padded','''
def chunked_padded(iterable,n,fillvalue=None,*,pad=True):
    """Yield positive-sized chunks, optionally padding the final nonempty one."""
    if isinstance(n,bool) or not isinstance(n,int):raise TypeError('n must be integer')
    if n<=0:raise ValueError('n must be positive')
    for chunk in chunked(iterable,n):
        yield chunk+[fillvalue]*(n-len(chunk)) if pad else chunk
''')
    elif tid=='T10':
        add_public(root,'partition_runs','''
def partition_runs(iterable,key=None,*,max_run=None):
    """Group contiguous equal keys; validate an optional positive run cap first."""
    if max_run is not None:
        if isinstance(max_run,bool) or not isinstance(max_run,int):raise TypeError('max_run must be integer')
        if max_run<=0:raise ValueError('max_run must be positive')
    buf=[];current=None
    for item in iterable:
        k=item if key is None else key(item)
        if buf and (k!=current or (max_run is not None and len(buf)==max_run)):
            yield current,tuple(buf);buf=[]
        current=k;buf.append(item)
    if buf:yield current,tuple(buf)
''')
        tests=root/'agent_tests';tests.mkdir(exist_ok=True)
        (tests/'test_partition_runs.py').write_text('''import unittest
from more_itertools import partition_runs

class Regression(unittest.TestCase):
    def test_cap_and_identity(self):
        objects = [object(), object(), object()]
        chunks = list(partition_runs(objects, lambda _: 1, max_run=2))
        self.assertEqual(chunks, [(1, tuple(objects[:2])), (1, (objects[2],))])
        self.assertIs(chunks[0][1][0], objects[0])

    def test_validation_before_consumption(self):
        consumed = []
        def source():
            consumed.append(True)
            yield 1
        with self.assertRaises(TypeError):
            list(partition_runs(source(), max_run=True))
        self.assertEqual(consumed, [])
''')
