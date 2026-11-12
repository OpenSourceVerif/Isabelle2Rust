"""Semantic translation batches over an unchanged, fine-grained source graph."""
from copy import deepcopy
import json
from .common import Failure
from .segmentation import partition,dependencies,INTRINSICS
from .program_model import components as strongly_connected,walk,readable
from .task_context import fingerprint


def enabled(cfg):
    return cfg.get('translation',{}).get('unit_policy')=='semantic-components'


def catalog(model,boundaries):
    atomic=partition(model,boundaries)
    adapted={r['source']:r for r in atomic['boundaries']}
    required=set(atomic['owner'])|{n for u in atomic['units'].values() for n in u['boundary_sources']}
    # Closing an implementation boundary must not lose its actual type/class
    # interface dependencies. Give every retained helper/type one explicit owner.
    edges={};todo=sorted(required)
    while todo:
        n=todo.pop()
        if n in edges:continue
        if n not in model['entities']:
            raise Failure('invalid_component_plan','Scheduled adaptations need source entities',n)
        if n in adapted:
            deps=set()
            entity=model['entities'][n]
            signature=[entity.get('source_type',{}),entity.get('type_variables',[])]
            for _,node in walk(signature):
                if node.get('kind')=='type' and 'args' in node:deps.add('type:'+node['name'])
                deps.update('class:'+c for c in node.get('sort',[]))
        else:deps=set(dependencies(model['entities'][n]))
        deps-=INTRINSICS|{n}
        edges[n]=sorted(deps);todo.extend(sorted(deps-set(edges)))
    edges={n:edges[n] for n in sorted(edges)}
    return atomic,edges


def compose(model,boundaries,groups):
    atomic,edges=catalog(model,boundaries)
    if not isinstance(groups,list) or not groups:
        raise Failure('invalid_component_plan','Return nonempty components:[{name,purpose,members:[exact source IDs]}]',sorted(edges))
    owner={};units={};names=set()
    for group in groups:
        if (not isinstance(group,dict) or not isinstance(group.get('name'),str) or not group['name'].strip()
                or not isinstance(group.get('purpose'),str) or not group['purpose'].strip()
                or not isinstance(group.get('members'),list) or not group['members']
                or any(not isinstance(n,str) for n in group['members'])):
            raise Failure('invalid_component_plan','Every component needs name, purpose and nonempty members',group)
        if group['name'] in names:raise Failure('invalid_component_plan','Component names must be unique',group['name'])
        names.add(group['name']);members=sorted(group['members']);uid='component-'+fingerprint(members)[:12]
        for n in members:
            if n not in model['entities']:raise Failure('invalid_component_plan','Component member is not an exact source entity ID',n)
            if n not in edges:raise Failure('invalid_component_plan','Known source entity is outside the closure retained by these effective adaptations',n)
            if n in owner:raise Failure('invalid_component_plan','Required entity has duplicate component ownership',n)
            owner[n]=uid
        units[uid]={'id':uid,'name':group['name'],'purpose':group['purpose'],'members':members,
                    'exports':sorted(set(members)&set(model['entries'])),
                    'adaptations':[r for r in atomic['boundaries'] if r['source'] in members],
                    'source_characters':sum(len(json.dumps(model['entities'][n],ensure_ascii=False)) for n in members)}
    if set(owner)!=set(edges):raise Failure('invalid_component_plan','Every required entity needs exactly one owner',{'missing':sorted(set(edges)-set(owner))})
    for group in strongly_connected(edges):
        if len({owner[n] for n in group})>1:
            raise Failure('invalid_component_plan','Do not split a recursive/type-instance cycle',sorted(group))
    for uid,u in units.items():
        u['dependencies']=sorted({owner[d] for n in u['members'] for d in edges[n] if owner[d]!=uid})
        # These operations now have explicit owners; they are no longer silently
        # implemented again in each consuming component.
        u['boundary_sources']=[]
    order=[];done=set()
    while len(done)<len(units):
        ready=sorted(u for u,row in units.items() if u not in done and set(row['dependencies'])<=done)
        if not ready:raise Failure('invalid_component_plan','Grouping introduced a dependency cycle; merge related groups or split across the intervening dependency',
                                   {u:units[u] for u in units if u not in done})
        order+=ready;done.update(ready)
    return {**atomic,'policy':'semantic-components','source_edges':edges,'atomic_units':atomic['units'],
            'components':deepcopy(groups),'units':units,'owner':owner,'order':order,
            'version':fingerprint({'edges':edges,'boundaries':atomic['boundaries'],'components':groups})}


SMALL_PROGRAM_DEFAULTS={'small_program_max_entities':12,'small_program_max_source_characters':16000}


def grouping_policy(cfg):
    values={key:cfg.get('translation',{}).get(key,default) for key,default in SMALL_PROGRAM_DEFAULTS.items()}
    if any(type(v) is not int or v<=0 for v in values.values()):
        raise Failure('invalid_translation_config','Small-program limits must be positive integers',values)
    return values


def grouping_context(model,boundaries,cfg):
    atomic,edges=catalog(model,boundaries)
    lengths={n:len(json.dumps(readable(model['entities'][n]),ensure_ascii=False)) for n in edges}
    limits=grouping_policy(cfg)
    measured={'entities':len(edges),'source_characters':sum(lengths.values()),
              'largest_entity_characters':max(lengths.values(),default=0)}
    small=(bool(edges) and measured['entities']<=limits['small_program_max_entities']
           and (cfg.get('translation',{}).get('correctness_only') or measured['source_characters']<=limits['small_program_max_source_characters']))
    return {'schema':1,'limits':limits,'measured':measured,'eligible_for_single_group':small,
            'metric':'actual adapted dependency closure; full readable JSON character sum without truncation',
            'adapted_catalog_identity':fingerprint({'source':model,'boundaries':atomic['boundaries'],'edges':edges}),
            'effective_boundaries':atomic['boundaries'],
            'effective_boundaries_identity':fingerprint(atomic['boundaries']),
            'required_entities':[{'source':n,'kind':model['entities'][n].get('kind'),'dependencies':edges[n],
                                  'source_characters':lengths[n]} for n in edges],
            'indivisible_groups':strongly_connected(edges)}


def from_analysis(model,boundaries,groups,cfg,default_decision=None):
    context=grouping_context(model,boundaries,cfg)
    if context['eligible_for_single_group']:
        chosen=[{'name':'whole-program','purpose':'Complete adapted closure fits both explicit small-program limits',
                 'members':[r['source'] for r in context['required_entities']]}]
        method='program_single_group';reason='Entity count permits a single complete group; source-character size is advisory, not an admission limit.' if cfg.get('translation',{}).get('correctness_only') else 'Both entity count and full readable source size are within inclusive limits.'
    else:
        chosen=groups;method='joint_analysis_components'
        reason='At least one small-program limit is exceeded; explicit components from the same analysis reply are required.'
    try:result=compose(model,boundaries,chosen)
    except Failure as error:
        if error.code!='invalid_component_plan':raise
        from collections import Counter
        members=Counter(n for g in chosen if isinstance(g,dict) for n in g.get('members',[]) if isinstance(n,str)) if isinstance(chosen,list) and all(not isinstance(g,dict) or isinstance(g.get('members'),list) for g in chosen) else Counter()
        required={r['source'] for r in context['required_entities']}
        membership={'required_ids':sorted(required),
                    'unknown_source_ids':sorted(set(members)-set(model['entities'])),
                    'known_but_pruned_by_effective_adaptation':sorted((set(members)&set(model['entities']))-required),
                    'missing_required_owners':sorted(required-set(members)),
                    'duplicate_owned_ids':sorted(n for n,count in members.items() if count>1),
                    'effective_boundaries_identity':context['effective_boundaries_identity'],
                    'adapted_catalog_identity':context['adapted_catalog_identity'],
                    'default_adaptation_decision':default_decision,
                    'instruction':'required_ids belongs only to the effective boundaries/default decision identified here. Changing use_default_adaptations, revoked defaults or explicit boundaries invalidates this list; recompute ownership for the new closure. With unchanged boundaries, own every required ID exactly once, and no other ID. Source pages/analysis_coverage classify additional entities, not owners. No plan is automatically filtered, renamed or repaired.'}
        raise Failure(error.code,str(error),{'validation':error.evidence,'membership_feedback':membership,'grouping_context':context}) from error
    decision={key:context[key] for key in ['schema','limits','measured','metric','adapted_catalog_identity']}
    decision.update(method=method,reason=reason,model_components_supplied=groups is not None,
                    model_components_used=not context['eligible_for_single_group'])
    result['grouping_decision']=decision
    result['version']=fingerprint({'composition':result['version'],'grouping_decision':decision})
    return result


def review_members(state):
    uid=state.get('unit')
    if uid is None:return set()
    members=set(state['partition']['units'][uid]['members'])
    return (members-set(state.get('source_reviews',{}))) | set(state.get('dirty_sources',{}).get(uid,[]))


def affected_sources(state,files,mapping,cfg,global_change=False):
    """Keep source-level evidence inside a translation batch after local edits."""
    from .review_scope import view,review_tokens,ambient_identity
    from .segmented_contract import items,validate_item
    plan=state['partition'];checked=set(state['completed'])|set(state.get('reviews',{}))|set(state.get('dirty_sources',{}))
    checked|={plan['owner'][n] for n in state.get('source_reviews',{}) if n in plan['owner']}
    checked_sources={n for u in checked for n in plan['units'][u]['members']}
    if global_change:return checked_sources
    old_map={r['source']:r for r in state['mapping']};new_map={r['source']:r for r in mapping}
    old_idx=items(state['files']);new_idx=items(files);changed=set()
    new={**state,'files':files,'mapping':mapping,'phase':'refine'}
    old={**state,'phase':'refine'}
    for n in checked_sources:
        a=old_map.get(n);b=new_map.get(n)
        if a!=b or (a and any(validate_item(old_idx,a).get(k)!=validate_item(new_idx,b).get(k) for k in ['text','attributes'])):
            changed.add(n);continue
        # Rust-only helpers can connect branches absent from the Isabelle graph.
        uid=plan['owner'][n]
        if review_tokens(view({**old,'unit':uid},{n},cfg)[0])!=review_tokens(view({**new,'unit':uid},{n},cfg)[0]):changed.add(n)
    # Propagate along individual source dependencies, not coarse batch edges.
    while True:
        more={n for n,ds in plan['source_edges'].items() if set(ds)&changed}
        if more<=changed:break
        changed|=more
    return changed&checked_sources
