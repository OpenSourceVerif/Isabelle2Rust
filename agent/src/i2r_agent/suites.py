"""Fresh case-specific inputs and independent properties; no old experiment data."""
from __future__ import annotations

import math
import random
from .common import Failure
from . import afp20_suites, fpp_suites


def input_bits(cfg):
    bits=cfg.get('testing',{}).get('max_input_bits',0)
    if bits=='auto':return 128 if cfg.get('preprocessing',{}).get('numeric_mode','checked')=='checked' else 0
    if not isinstance(bits,int) or isinstance(bits,bool) or bits<0:
        raise Failure('invalid_config','testing.max_input_bits must be auto, 0 (unbounded), or a positive integer')
    return bits


def in_numeric_domain(x,bits):
    return not bits or all(abs(v).bit_length()<=bits for v in x)


def scoped_inputs(case,count,seed,bits):
    if not bits:return generate(case,count,seed)
    # Deterministic rejection sampling preserves case structure and properties.
    result=[];batch=0
    while len(result)<count:
        candidates=generate(case,max(count,32),seed+batch)
        result.extend(x for x in candidates if in_numeric_domain(x,bits));batch+=1
        if batch>=1000 and len(result)<count:
            raise Failure('input_domain_too_small','Unable to sample requested case inputs within the explicit numeric domain')
    return result[:count]


def scoped_fixed(case,bits):
    original=fixed(case);included=[x for x in original if in_numeric_domain(x,bits)]
    # Keep boundary values inside a bounded domain; do not rewrite old cases.
    if bits:
        maximum=(1<<bits)-1
        extra={'list-index':[[maximum,maximum,0]],'skew-heap':[[1,maximum,0]],
               'splay-tree':[[maximum,0,maximum]],'shear-sort':[[1,maximum]],
               'karatsuba-sqrt':[[maximum-1,maximum]]}.get(case,[])
        included.extend(x for x in extra if domain(case,x) and x not in included)
    return included


def scoped_performance_input(case,bits):
    values=performance_input(case)
    if bits and case=='karatsuba-sqrt':values=[min(values[0],(1<<bits)-1)]
    if not in_numeric_domain(values,bits):
        raise Failure('performance_outside_input_domain','Benchmark input exceeds testing.max_input_bits; choose a compatible explicit domain')
    return values


def domain(case, x):
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in x):
        return False
    if case in fpp_suites.KINDS:return fpp_suites.domain(case,x)
    if case in afp20_suites.KINDS:return afp20_suites.domain(case,x)
    if case == "ackermann":
        return len(x) == 2 and x[0] <= 3 and x[1] <= 6
    if case == "shear-sort":
        return bool(x) and len(x) == 1 + x[0] ** 2
    if case == "transitive-closure":
        return len(x) >= 2 and len(x) == 2 + x[0] ** 2 and all(v in (0, 1) for v in x[2:])
    if case == "list-interleaving":
        return len(x) >= 3 and x[2] <= 2 and x[0] + x[1] <= len(x) - 3
    return True


def fixed(case):
    if case in fpp_suites.KINDS:return fpp_suites.fixed(case)
    if case in afp20_suites.KINDS:return afp20_suites.fixed(case)
    return {
        "native-word-u64": [[],[0],[0,0],[1,0],[0,1],[2**64-1,1],[2**63,3],[2**128+7,2**64],[2**64-1,2**63+1]],
        "collections-hashcode": [[],[0],[1],[0,0],[1,2,3],[3,2,1],[2**32-1],[2**128+7,0,2**32]],
        "list-index": [[], [0], [0,0], [1,0], [2,2,0,2], [9,1,2,3], [0,2**128,0], [2**130,2**130]],
        "skew-heap": [[],[0],[0,1],[1,1],[1,1,2],[2,5,5,1,0],[9,3,2,1],[1,2**130,0],
                      [2**64+1,3,1,2,4],[2**130+1,3,1,2,4]],
        "splay-tree": [[],[0],[0,0],[2,1,2,3],[0,1,2,3],[4,3,2,1],[2,2,2,2],[2**130,0,2**130]],
        "karatsuba-sqrt": [[],[0],[1],[2],[3],[4],[15,16,17],[2**128-1,2**128,2**128+1],[2**1024+1]],
        "shear-sort": [[0],[1,0],[1,2**130],[2,4,3,2,1],[2,1,1,1,1],[3,5,8,2,9,1,7,3,6,4]],
        "list-interleaving": [[0,0,0],[1,1,0,2,2],[1,0,0,1,1],[1,1,0,1,1],
            [2,1,0,2,1,2,1],[2,1,0,1,2,2,1],[2,1,1,1,2,1,2],[2,1,2,1,2,1,2]],
        "ackermann": [[m,n] for m in range(4) for n in range(4)],
        "transitive-closure": [[0,0],[1,0,0],[1,0,1],[1,1,1],[2,0,0,1,1,0],[2,0,0,0,0,0],
            [3,0,0,1,1,0,0,1,1,0,0]],
    }[case]


def generate(case, count, seed):
    if case in fpp_suites.KINDS:return fpp_suites.generate(case,count,seed)
    if case in afp20_suites.KINDS:return afp20_suites.generate(case,count,seed)
    rng = random.Random(seed)
    result = []
    def values(n):
        return [rng.randrange(16) if rng.random() < .9 else rng.getrandbits(130) for _ in range(n)]
    for _ in range(count):
        n = rng.randrange(0, 32)
        if case == "native-word-u64":
            x=[rng.getrandbits(rng.choice([1,32,64,65,130])) for _ in range(2)]
        elif case == "collections-hashcode":
            x=values(n)
        elif case in {"list-index", "splay-tree"}:
            xs = values(n)
            q = rng.choice(xs) if xs and rng.random() < .6 else rng.randrange(20)
            x = [q] + xs
        elif case == "skew-heap":
            x = [rng.randrange(n+3)] + values(n)
        elif case == "karatsuba-sqrt":
            k = rng.getrandbits(rng.choice([8,32,128,512,1100]))
            x = [k, k*k, max(0,k*k-1), k*k+1]
        elif case == "shear-sort":
            n = rng.randrange(0,9)
            x = [n] + values(n*n)
        elif case == "ackermann":
            x = [rng.randrange(4),rng.randrange(7)]
        elif case == "list-interleaving":
            ws = values(n)
            mode = rng.randrange(3)
            ys,zs=[],[]
            for i,v in enumerate(ws):
                select = v%2==0 if mode==0 else (len(ws)-i-1)%2==0 if mode==1 else v<=sum(ws[i+1:])
                (ys if select else zs).append(v)
            if ws and rng.random()<.45:
                ws[rng.randrange(len(ws))] += 1
            x = [len(ws),len(ys),mode]+ws+ys+zs
        else:
            n=rng.randrange(0,12)
            x=[n,rng.randrange(n+2)]+[int(rng.random()<.25) for _ in range(n*n)]
        assert domain(case,x), (case,x)
        result.append(x)
    return result


def property_error(case, x, y):
    if any(v<0 for v in y):
        return "Output violates natural-number invariant"
    if case in afp20_suites.KINDS:return afp20_suites.property_error(case,x,y)
    if case == "native-word-u64":
        if len(x)<2:expected=[]
        else:
            a,b=[v % 2**64 for v in x[:2]]
            expected=[(a+b)%2**64,(a*b)%2**64,a//b if b else 0,a%b if b else a,int(a<b)]
        if y!=expected:return "Independent 64-bit modular arithmetic property failed"
    if case == "collections-hashcode":
        h=5381
        for v in x:h=(h*33+v)%2**32
        if y!=[h]:return "Independent 32-bit AFP list hash fold property failed"
    if case == "list-index":
        if not x:
            expected=[]
        else:
            q,*xs=x; hits=[i for i,v in enumerate(xs) if v==q]
            expected=[hits[0] if hits else len(xs),hits[-1] if hits else len(xs),next((i for i,v in enumerate(xs) if v>q),len(xs))]
        return None if y==expected else f"Expected independent indices {expected}"
    if case == "karatsuba-sqrt":
        if len(y)!=2*len(x):return "Wrong number of root/remainder pairs"
        for n,s,r in zip(x,y[::2],y[1::2]):
            if s*s+r!=n or not 0<=r<2*s+1:return "Square-root remainder property failed"
    if case == "ackermann":
        m,n=x
        expected=[n+1,n+2,2*n+3,2**(n+3)-3][m]
        if y!=[expected]:return "Independent bounded Ackermann identity failed"
    if case == "shear-sort":
        xs=x[1:];n=len(xs)
        if len(y)!=2*n or sorted(y[:n])!=sorted(xs) or y[n:]!=sorted(xs):
            return "Matrix multiset or snake-order property failed"
    if case == "transitive-closure":
        n,start,*matrix=x;seen=set();todo=[start] if start<n else []
        while todo:
            u=todo.pop()
            if u in seen:continue
            seen.add(u);todo += [v for v in range(n) if matrix[u*n+v]]
        if len(y)!=len(set(y)) or set(y)!=seen:return "Independent reachable-set property failed"
    if case in {"skew-heap","splay-tree"} and x:
        offset=0 if case=="skew-heap" else 1
        def tree(i):
            if i>=len(y):raise ValueError("Truncated tree")
            if y[i]==0:return [],i+1
            if y[i]!=1 or i+1>=len(y):raise ValueError("Invalid tree tag")
            value=y[i+1];left,j=tree(i+2);right,k=tree(j)
            if case=="skew-heap" and any(v<value for v in left+right):raise ValueError("Heap order failed")
            return left+[value]+right,k
        try:
            first,j=tree(offset);second,k=tree(j)
            if k!=len(y):return "Trailing tree encoding"
            q,*xs=x
            if case=="skew-heap" and (sorted(first)!=sorted(xs) or sorted(second)!=sorted(xs)):return "Heap multiset failed"
            if case=="splay-tree" and (first!=sorted(set(xs)) or second!=sorted(set(xs)-{q}) or y[0]!=int(q in xs)):return "Search tree property failed"
        except (ValueError,RecursionError) as e:return str(e)
    return None


def performance_input(case):
    if case in afp20_suites.KINDS:return afp20_suites.performance_input(case)
    if case=="native-word-u64":return [2**64-1,2**63+1]
    if case=="collections-hashcode":return list(range(512))
    if case=="list-index":return [999]+list(range(512))
    if case=="skew-heap":return [64]+list(range(128,0,-1))
    if case=="splay-tree":return [64]+list(range(128))
    if case=="karatsuba-sqrt":return [2**2048+12345]
    if case=="shear-sort":return [16]+list(range(256,0,-1))
    if case=="ackermann":return [3,5]
    if case=="list-interleaving":return [128,64,0]+list(range(128))+list(range(0,128,2))+list(range(1,128,2))
    n=32
    return [n,0]+[int(j==(i+1)%n or j==(i+4)%n) for i in range(n) for j in range(n)]
