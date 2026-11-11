"""Predeclared FPP observation inputs; bounds constrain tests, not source semantics."""
import random
KINDS={
 'fpp-multip':'pair','fpp-bool-and':'pair','fpp-add':'pair','fpp-sub':'pair',
 'fpp-fib':'unary','fpp-sep':'list','fpp-map':'list','fpp-fof2':'pair',
 'fpp-isort':'list','fpp-msort':'list','fpp-quicksort':'list','fpp-bubblesort':'list',
 'fpp-mirror':'list','fpp-preorder':'list','fpp-push':'list','fpp-top':'nonempty',
}
from .fpp_expansion import KINDS as EXTRA_KINDS
KINDS.update(EXTRA_KINDS)

def domain(case,x):
    k=KINDS[case]
    if k=='ack':return len(x)==2 and x[0]<=2 and x[1]<=6
    return len(x)==2 if k=='pair' else len(x)==1 and x[0]<=16 if k=='unary' else bool(x) if k=='nonempty' else True

def fixed(case):
    k=KINDS[case]
    if k=='ack':return [[m,n] for m in range(3) for n in [0,1,3,6]]
    if k=='pair':return [[0,0],[0,1],[1,0],[1,1],[2,3],[7,4]]
    if k=='unary':return [[x] for x in [0,1,2,3,8,16]]
    rows=[[],[0],[1],[0,0],[0,1,0],[1,2,3],[3,2,1],[7,0,7,2]]
    return [x for x in rows if domain(case,x)]

def generate(case,count,seed):
    rng=random.Random(seed);k=KINDS[case]
    if k=='ack':return [[rng.randrange(3),rng.randrange(7)] for _ in range(count)]
    return [[rng.randrange(8) for _ in range(2 if k=='pair' else 1 if k=='unary' else rng.randrange(1 if k=='nonempty' else 0,13))] for _ in range(count)]
