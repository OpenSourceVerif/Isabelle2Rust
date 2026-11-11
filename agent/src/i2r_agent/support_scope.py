"""Disjoint author responsibilities over validated components, with exact lazy source pages."""
import json
from .common import Failure
from .program_model import readable
from .segmented_context import pages
from .task_context import fingerprint

POLICY='component-owned-batched-author-groups-scoped-context-v2'


def plan(state,cfg):
    model=state['bundle']['source_model']
    ids=set(model['entries'])|{r['source'] for r in state['mapping']}
    entities=model['entities']
    if not ids<=entities.keys():raise Failure('unknown_support_source','Mapped source entity is unavailable',sorted(ids-entities.keys()))
    partition=state.get('partition',{});units=partition.get('units',{});order=partition.get('order',[])
    owned=[];seen=set()
    for uid in order:
        group=sorted(set(units[uid]['members'])&ids)
        if seen.intersection(group):raise Failure('invalid_support_partition','A source cannot belong to two author groups',group)
        seen.update(group)
        if group:owned.append(group)
    # Legacy/noncomponent states retain every source with deterministic ownership.
    owned.extend([[n] for n in sorted(ids-seen)])
    def operational(group):
        return any(n in model['entries'] or entities[n].get('execution_equations') for n in group)
    # Pure signatures/constructors have no stand-alone executable test. Attach
    # them to the next operational group; no source or generic constraint is lost.
    groups=[];pending=[]
    for group in owned:
        pending+=group
        if operational(group):groups.append(sorted(pending));pending=[]
    if pending:
        if groups:groups[-1]=sorted(groups[-1]+pending)
        else:groups=[sorted(pending)]
    # Batching is an output/workload planning heuristic, not a context rejection.
    # Keep validated components atomic; measure executable responsibilities and
    # required edge rows rather than verbose source JSON character count.
    from .v8_support import requirements
    def workload(group):
        operations=sum(bool(entities[n].get('execution_equations')) for n in group)
        return operations,len(requirements(state,group))
    merged=[]
    for group in groups:
        combined=(merged[-1]+group) if merged else group
        operations,required=workload(combined)
        if merged and operations<=32 and required<=64:merged[-1]+=group
        else:merged.append(group)
    groups=[sorted(g) for g in merged]
    flat=[n for group in groups for n in group]
    if set(flat)!=ids or len(flat)!=len(ids):raise Failure('invalid_support_partition','Author responsibilities must partition all original sources')
    from .v8_support import requirements
    rows=[row for group in groups for row in requirements(state,group)]
    original=requirements(state,ids)
    if sorted(rows,key=lambda r:(r['source'],r['category']))!=sorted(original,key=lambda r:(r['source'],r['category'])):
        raise Failure('invalid_support_partition','Required obligation union changed')
    return {'policy':POLICY,'groups':groups,'source_owner':{n:i for i,g in enumerate(groups) for n in g},
            'batching':{'max_executable_operations':32,'max_required_rows':64,'indivisible_components_may_exceed':True,'provider_context_admission':True},'required_obligations':original,'identity':fingerprint({'policy':POLICY,'groups':groups,'partition':partition,'source':model})}


def material(model,group,size):
    # Full exact dependency/type definitions remain fetchable; only owned pages
    # are mandatory on this author's initial read. No source text is shortened.
    source_pages=pages(model,needed(model,group),size)
    for page in source_pages:page['required_for_group']=page['source'] in group
    return source_pages


def validate_owned(proposal,group):
    outside=[row.get('source') for row in proposal.get('obligations',[]) if row.get('source') not in group]
    if outside:raise Failure('invalid_support_test','Return obligation records only for this author group; dependency pages are context, not additional ownership',{'outside_group':outside,'owned_sources':group})


def needed(model,group):
    from .source_evidence import instance_dependencies
    seen=set();todo=list(group);entities=model['entities']
    while True:
        while todo:
            n=todo.pop()
            if n in seen or n not in entities:continue
            seen.add(n);e=entities[n]
            todo.extend(e.get('dependencies',[]));todo.extend(e.get('type_dependencies',[]));todo.extend(e.get('class_dependencies',[]))
        # Generic source dependencies omit concrete instances required at typed
        # call sites. Add exact witnessed resolutions, then their ordinary facts.
        todo=list(instance_dependencies(model,seen)-seen)
        if not todo:return sorted(seen)


def scope_payload(state,group,payload,api):
    import re
    from .source_test_context import canonical_mapping
    ids=set(needed(state['bundle']['source_model'],group));mapping=[r for r in canonical_mapping(state) if r['source'] in ids];paths={r.get('rust_item') for r in mapping}
    # Include declarations needed by selected Rust signatures, including private
    # helper types and impl/trait context, without returning unrelated functions.
    selected={n for n in api if n in paths};changed=True
    while changed:
        text=str({n:api[n] for n in selected});extra={n for n,rows in api.items() if any(r['kind'] in {'struct_item','enum_item','type_item','trait_item','impl_item'} for r in rows) and re.search(r'\b'+re.escape(n.rsplit('::',1)[-1])+r'\b',text)}
        changed=bool(extra-selected);selected|=extra
    payload['mapping']=mapping;payload['rust_interfaces']={n:api[n] for n in sorted(selected)}
    payload['rust_signatures']={n:[r['signature'] for r in api[n]] for n in sorted(selected)}
    payload['item_locations']={n:v for n,v in payload['item_locations'].items() if n in selected}
    payload['context_scope']={'policy':POLICY,'owned':group,'needed':sorted(ids),'selected_rust_items':sorted(selected),'source_graph_identity':fingerprint(state['bundle']['source_model'])}
    return payload
