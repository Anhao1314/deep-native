"""Independent hidden contract tests. Executed in a separate candidate copy.

No model response or Deep Native receipt influences these assertions.
"""
import ast
import json
import random
import subprocess
import sys
from pathlib import Path

def raises(kind, call):
    try:
        call()
    except kind:
        return
    raise AssertionError('Expected ' + kind.__name__)

def check(task_id, phase=2):
    rng = random.Random(80921)
    if task_id == 'T01':
        from boltons.strutils import ordinalize
        for i in range(-220, 340):
            suffix = 'th' if abs(i) % 100 in (11, 12, 13) else {1:'st',2:'nd',3:'rd'}.get(abs(i)%10,'th')
            assert ordinalize(i) == str(i)+suffix
            assert ordinalize(str(i), ext_only=True) == suffix
        for value in ['', 'hi', 'abc!', 'x1']:
            if value == 'x1': assert ordinalize(value) == 'x1st'
            else: assert ordinalize(value) == value
    elif task_id == 'T02':
        from more_itertools import chunked
        seen=[]
        def source():
            seen.append(True)
            yield 1
        for n in [True, False, 2.0, '2', object()]:
            raises(TypeError, lambda: chunked(source(), n))
            assert not seen
        raises(ValueError, lambda: chunked(source(), -1))
        assert not seen
        assert list(chunked(range(4),0)) == []
        assert list(chunked(range(4),None)) == [[0,1,2,3]]
        raises(ValueError, lambda: list(chunked(range(3),2,strict=True)))
        for length in range(23):
            for n in [1,2,7]:
                seq=list(range(length))
                assert list(chunked(iter(seq),n)) == [seq[i:i+n] for i in range(0,length,n)]
    elif task_id == 'T03':
        from more_itertools import windowed_complete
        from more_itertools.more import windowed_complete as direct
        for length in range(9):
            seq=tuple(range(length))
            for width in range(length+1):
                expected=[(seq[:i],seq[i:i+width],seq[i+width:]) for i in range(length-width+1)]
                for function in [windowed_complete,direct]:
                    assert list(function(iter(seq),width)) == expected
        raises(ValueError, lambda: list(windowed_complete([],1)))
        raises(ValueError, lambda: list(direct([1],-1)))
    elif task_id in ['T04','T08']:
        from boltons.strutils import parse_int_list, format_int_list
        assert parse_int_list('') == []
        assert parse_int_list('1,1,3-1') == [1,1,1,2,3]
        assert parse_int_list(' -3 - -1 , +2 - +4 , -7 ') == [-7,-3,-2,-1,2,3,4]
        assert parse_int_list('-3:-1;2',delim=';',range_delim=':') == [-3,-2,-1,2]
        assert parse_int_list('1..3|5',delim='|',range_delim='..') == [1,2,3,5]
        for text in ['1-2-3', 'x', '--3', '3-', '-']:
            raises(ValueError,lambda:parse_int_list(text))
        for _ in range(40):
            a,b=rng.randrange(-40,40),rng.randrange(-40,40)
            assert parse_int_list(f'{a}-{b}') == list(range(min(a,b),max(a,b)+1))
        if task_id == 'T08':
            from boltons.rangeutils import parse_ranges,format_ranges
            for _ in range(40):
                vals=[rng.randrange(-15,15) for _ in range(30)]
                assert parse_ranges(format_ranges(vals)) == sorted(set(vals))
                assert format_ranges(vals) == format_int_list(sorted(set(vals)))
            assert format_ranges([]) == ''
            assert parse_ranges('2,2,3-1') == [1,2,3]
            assert format_ranges([-3,-2,-1,1,3,4]) == '-3--1,1,3-4'
            def cli(*args):
                return subprocess.run([sys.executable,'-m','boltons.rangeutils',*args],capture_output=True,text=True,timeout=10)
            out=cli('expand','-3--1,2,2')
            assert out.returncode==0,(out.stdout,out.stderr)
            assert json.loads(out.stdout) == [-3,-2,-1,2]
            out=cli('compact','-3,-1,-2,2,2')
            assert out.returncode==0 and out.stdout.strip() == '-3--1,2'
            out=cli('expand','1-bad')
            assert out.returncode!=0 and 'Traceback' not in out.stderr
    elif task_id == 'T05':
        from more_itertools import map_reduce
        events=[]
        def key(v): events.append(('key',v));return v%2
        def value(v): events.append(('value',v));return v*3
        out=map_reduce(iter(range(7)),key,value,sum)
        assert out=={0:36,1:27} and out.default_factory is None
        assert events==[e for v in range(7) for e in [('key',v),('value',v)]]
        assert list(out)==[0,1]
        assert map_reduce([],key)=={}
        raises(KeyError,lambda:out[5])
        raises(RuntimeError,lambda:map_reduce([1],lambda _:(_ for _ in ()).throw(RuntimeError())))
        tree=ast.parse(Path('more_itertools/more.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='map_reduce')
        # Two loops total: one accumulation and one reduction, never two accumulation branches.
        assert sum(isinstance(n,(ast.For,ast.AsyncFor)) for n in ast.walk(fn)) == 2
        assert any(Path('agent_tests').glob('test*.py')), 'Required new regression protection absent'
    elif task_id == 'T06':
        from boltons.iterutils import get_path,PathAccessError
        root={'a':{'b':[[3],[7]]},'b':'decoy'}
        assert get_path(root,('a','b',1,0))==7
        assert get_path(root,'a.b.0.0')==3
        assert get_path(root,()) is root
        sentinel=object()
        assert get_path(root,('a','bad'),sentinel) is sentinel
        try:get_path(root,('a','b',8))
        except PathAccessError as e:
            assert e.seg==8 and tuple(e.path)==('a','b',8)
        else:raise AssertionError('Missing PathAccessError')
        raises(PathAccessError,lambda:get_path({'a':1},'a.b'))
    elif task_id == 'T07':
        from more_itertools import take_until_inclusive
        seen=[];calls=[]
        def source():
            for i in range(10):seen.append(i);yield i
        it=take_until_inclusive(source(),lambda x:calls.append(x) or x==4)
        assert not seen and not calls
        assert list(it)==[0,1,2,3,4]
        assert seen==calls==list(range(5))
        assert list(take_until_inclusive([],bool))==[]
        assert list(take_until_inclusive([1,2],lambda _:False))==[1,2]
        raises(RuntimeError,lambda:list(take_until_inclusive([1],lambda _:(_ for _ in ()).throw(RuntimeError()))))
    elif task_id == 'T09':
        from more_itertools import chunked_padded
        fill=object()
        for length in range(13):
            for n in [1,2,5]:
                seq=list(range(length))
                chunks=[seq[i:i+n] for i in range(0,length,n)]
                padded=[c+[fill]*(n-len(c)) for c in chunks]
                assert list(chunked_padded(iter(seq),n,fill))==padded
                if phase==2:
                    assert list(chunked_padded(iter(seq),n,fill,pad=False))==chunks
        for n in [0,-2]:raises(ValueError,lambda:list(chunked_padded([],n)))
        for n in [True,False,2.0,'2']:raises(TypeError,lambda:list(chunked_padded([],n)))
        seen=[]
        def source():
            for i in range(10):seen.append(i);yield i
        it=chunked_padded(source(),3)
        assert not seen
        assert next(it)==[0,1,2] and seen==[0,1,2]
    elif task_id == 'T10':
        from more_itertools import partition_runs
        calls=[]
        objs=[{'k':1},{'k':1},{'k':2},{'k':1}]
        out=list(partition_runs(iter(objs),lambda x:calls.append(id(x)) or x['k']))
        assert out==[(1,tuple(objs[:2])),(2,(objs[2],)),(1,(objs[3],))]
        assert calls==list(map(id,objs)) and out[0][1][0] is objs[0]
        for length in range(12):
            for cap in [1,2,5,None]:
                seq='a'*length
                expected=[] if not seq else [('a',tuple(seq[i:i+(cap or length)])) for i in range(0,length,cap or length)]
                assert list(partition_runs(seq,max_run=cap))==expected
        for bad in [True,False,1.0,'2']:raises(TypeError,lambda:list(partition_runs([],max_run=bad)))
        for bad in [0,-1]:raises(ValueError,lambda:list(partition_runs([],max_run=bad)))
        assert list(partition_runs([]))==[]
        raises(RuntimeError,lambda:list(partition_runs([1],lambda _:(_ for _ in ()).throw(RuntimeError()))))
    else:
        raise ValueError(task_id)
    print('Independent contract checks passed:',task_id,'phase',phase)

if __name__=='__main__':
    sys.path.insert(0,str(Path.cwd()))
    check(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 2)
