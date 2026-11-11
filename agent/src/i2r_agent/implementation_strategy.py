"""Versioned advisory choices, separate from authoritative structured state.

Adoption records current implementation intent, never proof or test coverage.
History is retained outside the active projection and cache identities.
"""
from copy import deepcopy
from .common import Failure
from .task_context import fingerprint

FIELDS=('id','kind','sources','choice','conditions','status','links','test_focus')

def initialize(analysis):
    rows=[]
    for field,kind in [('semantic_obligations','representation'),('interface_guidance','interface'),
                       ('opportunities','library'),('boundaries','library'),('decisions','ownership')]:
        for i,value in enumerate(analysis.get(field,[]) or []):
            row=value if isinstance(value,dict) else {'choice':value}
            rows.append({'id':f'initial:{field}:{i}','revision':1,'kind':kind,
                'sources':[row['source']] if row.get('source') else deepcopy(row.get('sources',[])),
                'choice':deepcopy(row.get('choice',row.get('rust_representation',row))),
                'conditions':deepcopy(row.get('conditions',[])), 'reason':'Initial analysis suggestion',
                'status':'proposed','links':['mapping','rust_config','partition'],
                'test_focus':deepcopy(row.get('boundary_cases',[]))})
    return {'schema':1,'revision':0,'decisions':rows,'history':[]}

def current(state):
    return state.get('implementation_strategy',{'schema':1,'revision':0,'decisions':[],'history':[]})

def project(state,sources=None,binding=False,testing=False):
    rows=[]
    for r in current(state)['decisions']:
        if r['status']=='superseded' or (sources is not None and r['sources'] and not set(r['sources'])&set(sources)):continue
        if testing:
            rows.append({k:deepcopy(r[k]) for k in ('id','sources','conditions','test_focus','status')})
        else:rows.append({k:deepcopy(v) for k,v in r.items() if not binding or k in FIELDS})
    return rows

def revise(state,reply,files,mapping,config,partition):
    strategy=deepcopy(current(state));updates=reply.get('strategy_updates',[])
    if updates and reply.get('strategy_version')!=fingerprint(current(state)):
        raise Failure('stale_strategy','Supply the exact current strategy_version')
    by_id={r['id']:r for r in strategy['decisions']};touched=set()
    entities=state['bundle']['source_model']['entities']
    for patch in updates:
        if not isinstance(patch,dict) or not isinstance(patch.get('id'),str) or not patch['id'].strip() or not isinstance(patch.get('reason'),str) or not patch['reason'].strip():
            raise Failure('invalid_strategy','Each revision requires id and reason')
        key=patch['id']
        if key in touched:raise Failure('invalid_strategy','Duplicate revision',key)
        touched.add(key);old=by_id.get(key)
        if patch.get('expected_revision')!=(old['revision'] if old else 0):
            raise Failure('stale_strategy','Decision revision mismatch',key)
        allowed=set(FIELDS)|{'reason','expected_revision','supersedes'}
        if set(patch)-allowed:raise Failure('invalid_strategy','Unknown strategy fields',sorted(set(patch)-allowed))
        row={**deepcopy(old or {}),**{k:deepcopy(v) for k,v in patch.items() if k!='expected_revision'}}
        row.setdefault('conditions',[]);row.setdefault('test_focus',[]);row.setdefault('links',['mapping','rust_config','partition'])
        if (row.get('kind') not in {'representation','interface','ownership','library'} or
            row.get('status') not in {'proposed','adopted','needs_review','superseded'} or
            not isinstance(row.get('sources'),list) or any(not isinstance(n,str) or n not in entities for n in row['sources']) or
            not row.get('choice') or not isinstance(row['links'],list) or
            any(not isinstance(n,str) or n not in {'mapping','rust_config','partition'} for n in row['links'])):
            raise Failure('invalid_strategy','Invalid choice, sources, status or state references',key)
        if row['status']=='adopted' and row['sources'] and not set(row['sources'])<={r['source'] for r in mapping}:
            raise Failure('invalid_strategy','Adopted choice requires current source mappings',key)
        if old and old['status']=='superseded':
            raise Failure('invalid_strategy','Superseded IDs cannot be revived; create a new decision',key)
        row['revision']=(old['revision'] if old else 0)+1
        if old:strategy['history'].append(deepcopy(old))
        by_id[key]=row
        if not isinstance(patch.get('supersedes',[]),list) or any(not isinstance(t,str) for t in patch.get('supersedes',[])):
            raise Failure('invalid_strategy','supersedes must list decision IDs')
        for target in patch.get('supersedes',[]):
            if target==key or target not in by_id:raise Failure('invalid_strategy','Unknown superseded decision',target)
            strategy['history'].append(deepcopy(by_id[target]))
            by_id[target]={**by_id[target],'status':'superseded','superseded_by':key,'revision':by_id[target]['revision']+1}
    from .v8_identity import interfaces_for_cache
    # Apply the same conservative independent-addition exemption as review
    # invalidation. Adding an unreferenced free function does not revise an
    # already implemented dependency's interface or representation choice.
    from .v8_review_scope import independent_additions_removed
    interface_context,_=independent_additions_removed(state['files'],files)
    api_changed=interfaces_for_cache(interface_context)!=interfaces_for_cache(state['files'])
    oldmap={r['source']:r for r in state['mapping']};newmap={r['source']:r for r in mapping}
    for key,row in by_id.items():
        changed=(api_changed or ('rust_config' in row['links'] and config!=state['rust_config']) or
                 ('partition' in row['links'] and partition!=state['partition']) or
                 ('mapping' in row['links'] and any(oldmap.get(n)!=newmap.get(n) for n in row['sources'] or set(oldmap)|set(newmap))))
        if changed and key not in touched and row['status'] not in {'superseded','needs_review'}:
            strategy['history'].append(deepcopy(row));row.update(status='needs_review',revision=row['revision']+1)
    strategy['decisions']=list(by_id.values())
    if strategy!=current(state):strategy['revision']+=1
    return strategy


def affected(state,new):
    result=set();all_sources=set(state['partition']['owner'])
    for n in all_sources:
        if project(state,{n},binding=True)!=project(new,{n},binding=True):result.add(n)
    edges=state['partition'].get('source_edges',{})
    while True:
        more={n for n,ds in edges.items() if set(ds)&result}
        if more<=result:return result
        result|=more


def restore_check(state):
    s=state.get('implementation_strategy')
    if 'strategy_digest' in state and state['strategy_digest']!=fingerprint(s):
        raise Failure('stale_snapshot','Current strategy digest mismatch')
    if not isinstance(s,dict) or s.get('schema')!=1 or not all(k in s for k in ('revision','decisions','history')):
        raise Failure('stale_snapshot','Checkpoint lacks recoverable current implementation strategy; explicit migration required')
    if not isinstance(s['decisions'],list) or not isinstance(s['history'],list) or any(not isinstance(r,dict) or not set(FIELDS)<=r.keys() or type(r.get('revision')) is not int for r in s['decisions']):
        raise Failure('stale_snapshot','Malformed current strategy records')
    if state.get('optimization_parent'):
        restore_check(state['optimization_parent'])


def test_identity(state,sources=None):
    """Only actual representation conditions bind independent test reuse."""
    return [{'sources':r['sources'],'conditions':r['conditions']}
            for r in project(state,sources,testing=True) if r['conditions']]
