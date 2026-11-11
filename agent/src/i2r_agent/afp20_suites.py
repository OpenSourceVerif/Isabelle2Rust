"""Independent workloads/properties for the additional AFP checked experiment.

Sampling bounds control execution cost; they do not authorize narrower generated
numeric representations or establish intermediate bounds for arbitrary callers.
"""
import heapq
import math
import random

KINDS={
    'afp-inversions':'inversions', 'afp-maximum-segment-sum':'mss',
    'afp-efficient-mergesort':'sort', 'afp-natural-mergesort':'sort',
    'afp-selection-sort':'sort', 'afp-braun-heap-sort':'sort',
    'afp-pairing-heap':'sort', 'afp-binomial-heap':'sort',
    'afp-hood-melville-queue':'queue', 'afp-trie-map':'trie',
    'afp-binary-search-tree':'set_tree', 'afp-huffman':'huffman',
    'afp-list-power':'power', 'afp-catalan':'catalan',
    'afp-stern-brocot-path':'stern', 'afp-avl-tree':'set_tree',
    'afp-digits-eval':'digits', 'afp-tailrec-sort':'sort',
    'afp-move-to-front':'mtf', 'afp-binary-exponentiation':'binary_power',
}

def domain(case,x):
    kind=KINDS[case]
    if kind=='binary_power':return not x or len(x)==2 and all(0<=n<=15 for n in x)
    if kind=='power':return not x or x[0]<=16
    if kind=='catalan':return len(x)<=8 and all(n<=10 for n in x)
    if kind=='stern':return len(x)==2 and all(1<=n<=256 for n in x)
    return True

def fixed(case):
    kind=KINDS[case]
    if kind=='binary_power':return [[],[0,0],[0,1],[1,0],[1,15],[2,3],[3,4],[15,15]]
    if kind=='stern':return [[1,1],[1,8],[8,1],[2,4],[4,2],[13,21],[21,13],[17,31],[256,255]]
    if kind=='power':return [[],[0],[1],[0,1,2],[1,1,2],[3,1,2],[16,0],[2,2**128-1,0]]
    if kind=='catalan':return [[],[0],[1],[2],[3],[4],[5],[6],[7],[8],[9],[10],[0,1,2,3]]
    if kind=='digits':return [[],[0],[1],[2],[10,1,2,3],[2,1,0,1],[0,4,5],[1,4,5],[16,15,0,15]]
    if kind=='mss':return [[],[0],[1],[2],[1,3,5],[4,5,8,1],[2**64,2**64-1],[10,11,2,4,3]]
    if kind=='queue':return [[],[0],[0,0],[1],[1,2,0],[1,2,3,4,0,5,0,0,6],list(range(1,40))+[0]*40]
    if kind=='huffman':return [[],[0],[1],[0,0],[1,1],[1,2,3,4],[0,1,0,2],[5]*8,list(range(1,17))]
    values=[[],[0],[1],[0,0],[3,2,1],[1,2,3],[2,1,2,0,1],[2**128-1,0,2**127,2**128-1]]
    if kind in {'trie','set_tree','mtf'}:values += [[2,1,2,3],[5,1,2,3],[0,0,0],[4,0,1,2,3,4,5,6,7]]
    return values

def generate(case,count,seed):
    rng=random.Random(seed);kind=KINDS[case];out=[]
    for _ in range(count):
        n=rng.randrange(33)
        def value():
            return rng.randrange(16) if rng.random()<.85 else rng.getrandbits(rng.choice([32,64,127,128]))
        if kind=='binary_power':x=[rng.randrange(16),rng.randrange(16)]
        elif kind=='catalan':x=[rng.randrange(11) for _ in range(rng.randrange(1,4))]
        elif kind=='stern':x=[rng.randrange(1,129),rng.randrange(1,129)]
        elif kind=='digits':
            b=rng.randrange(2,17);x=[b]+[rng.randrange(b) for _ in range(rng.randrange(21))]
        elif kind=='power':x=[rng.randrange(9)]+[value() for _ in range(rng.randrange(13))]
        elif kind in {'mss','huffman','queue'}:x=[rng.randrange(64) for _ in range(n)]
        elif kind in {'trie','set_tree','mtf'}:
            xs=[value() for _ in range(n)];q=rng.choice(xs) if xs and rng.random()<.6 else value();x=[q]+xs
        else:x=[value() for _ in range(n)]
        assert domain(case,x)
        out.append(x)
    return out

def property_error(case,x,y):
    kind=KINDS[case]
    if kind=='binary_power':expected=[pow(*x)] if x else []
    elif kind=='sort':expected=sorted(x)
    elif kind=='inversions':expected=[sum(a>b for i,a in enumerate(x) for b in x[i+1:])]+sorted(x)
    elif kind=='mss':
        xs=[n//2 if n%2==0 else -(n//2+1) for n in x]
        expected=[max([0]+[sum(xs[i:j]) for i in range(len(xs)) for j in range(i+1,len(xs)+1)])]
    elif kind=='queue':
        expected=[]
        for n in x:
            if n:expected.append(n-1)
            elif expected:expected.pop(0)
    elif kind=='power':expected=x[1:]*x[0] if x else []
    elif kind=='catalan':expected=[math.comb(2*n,n)//(n+1) for n in x]
    elif kind=='digits':
        if not x:expected=[]
        else:
            b,*ds=x;expected=[sum(d*b**i for i,d in enumerate(ds)),sum(d*b**i for i,d in enumerate(reversed(ds)))]
    elif kind=='trie':
        if not x:expected=[]
        else:
            q,*xs=x;expected=([1,q] if q in xs else [0])+[0]
    elif kind=='set_tree':
        if not x:expected=[]
        else:
            q,*xs=x;values=sorted(set(xs));expected=[int(q in xs),len(values)]+values+[v for v in values if v!=q]
    elif kind=='mtf':
        if not x:expected=[]
        else:
            q,*xs=x;expected=xs[:]
            if q in xs:expected.remove(q);expected.insert(0,q)
    elif kind=='huffman':
        if not x:expected=[]
        else:
            heap=x[:];heapq.heapify(heap);cost=0
            while len(heap)>1:
                w=heapq.heappop(heap)+heapq.heappop(heap);cost+=w;heapq.heappush(heap,w)
            if len(y)!=3 or y[:2]!=[cost,sum(x)]:return 'Huffman optimal merge cost/total weight mismatch'
            # AFP height uses leaf height zero; exact tie-dependent shape remains
            # checked by both source references rather than this independent bound.
            if not 0<=y[2]<=max(0,len(x)-1):return 'Huffman height bound mismatch'
            return None
    elif kind=='stern':
        if any(n not in (0,1) for n in y):return 'Invalid path direction'
        a=b=1
        for n in reversed(y):
            if n==0:b+=a
            else:a+=b
        divisor=math.gcd(*x)
        return None if [a,b]==[v//divisor for v in x] else 'Path does not reconstruct the input rational'
    else:raise AssertionError(kind)
    return None if y==expected else 'Independent '+kind+' observation mismatch'

def performance_input(case):
    kind=KINDS[case]
    if kind=='binary_power':return [13,15]
    if kind=='stern':return [89,144]
    if kind=='catalan':return [8]
    if kind=='power':return [8]+list(range(32))
    if kind=='digits':return [10]+list(range(10))*2
    if kind=='mss':return list(range(64))*2
    if kind=='huffman':return list(range(1,65))
    if kind=='queue':return list(range(1,65))+[0]*32+list(range(65,97))
    if kind in {'trie','set_tree','mtf'}:return [64]+list(range(128))
    return list(range(127,-1,-1))

def additional_workloads(case):
    kind=KINDS[case]
    if kind=='binary_power':return [[2,14],[15,8]]
    if kind=='stern':return [[1,128],[127,128]]
    if kind=='catalan':return [[6],[9]]
    if kind=='power':return [[4]+list(range(64)),[12]+list(range(16))]
    if kind=='digits':return [[2]+[1]*64,[16]+[15]*24]
    if kind=='mss':return [[63,64]*32,[2]*128]
    if kind=='huffman':return [[1]*32,list(range(1,97))]
    if kind=='queue':return [[1,0]*64,list(range(1,129))+[0]*128]
    if kind in {'trie','set_tree','mtf'}:return [[8]+[n%16 for n in range(64)],[127]+list(range(255,-1,-1))]
    return [[n%8 for n in range(64)],list(range(256))]
