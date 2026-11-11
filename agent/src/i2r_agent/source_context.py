"""Current Rust/source evidence selected by diagnostics and explicit realizations."""
from copy import deepcopy
import re
from pathlib import Path
from .common import Failure
from . import program_model as pm, task_context as tc
from .export_contract import polymorphic_exports, check_exports
from .rust_index import build as rust_index, select


def source_view(bundle, focus=None, expand=False):
    model=bundle['source_model']; entities=model['entities']
    roots=set(focus or model['entries'])
    selected=set(roots)
    for n in roots:
        e=entities.get(n,{})
        selected.update(e.get('dependencies',[]));selected.update(e.get('callers',[]))
        selected.update(e.get('type_dependencies',[]));selected.update(e.get('class_dependencies',[]))
    if expand:
        for n in list(selected): selected.update(entities.get(n,{}).get('dependencies',[]))
    return {'kind':model['kind'],'entries':model['entries'],'focus':sorted(roots),
        'entities':[pm.readable(entities[n]) for n in sorted(selected) if n in entities],
        'uses':[u for u in model['uses'] if u['caller'] in selected],
        'recursive_groups':[g for g in model['recursive_groups'] if selected.intersection(g)],
        'catalog':[{'id':n,'kind':e['kind']} for n,e in entities.items()],
        'unknown_entities':sorted(selected-entities.keys()),
        'selection':'Complete equations of roots, direct dependencies/callers and types. Remaining entities are explicitly catalogued and requestable, never assumed implemented.',
        'provenance':model['provenance']}


def material(bundle, extra=None):
    return {'entries':bundle['source_model']['entries'], 'program_model':source_view(bundle),
        'numeric_policy':bundle['numeric_policy'],'polymorphic_exports':polymorphic_exports(bundle),
        'project_sources':{n:t for n,t in bundle['sources'].items() if not Path(n).is_absolute()},
        'source_catalog':bundle['source_catalog'],'analysis':bundle.get('semantic_analysis'),
        'requested_material':extra or {},'reference_catalog':[r for r in tc.reference_catalog() if not r['path'].endswith('isabelle-syntax.md')]}


def coverage(bundle, files, mapping):
    """Check explicit implementation frontiers, without pretending to prove them."""
    model=bundle['source_model']; rows={r['source']:r for r in mapping}
    unknown=set(rows)-model['entities'].keys()
    if unknown: raise Failure('plan_contract_failed','Unknown source IDs; remove invalid records with remove_mapping (omitting entries from mapping does not delete them)',
        {'unknown':sorted(unknown),'repair':{'remove_mapping':sorted(unknown)}})
    todo=list(model['entries']);visited=set();missing=[];boundaries=[]
    index=rust_index(files)
    for row in mapping:
        item=row.get('rust_item')
        if item and not any(r.get('name')==item.split('::')[-1] for r in index['items']):
            raise Failure('plan_contract_failed','rust_item must identify a real Rust item',row)
    while todo:
        n=todo.pop()
        if n in visited: continue
        visited.add(n);row=rows.get(n)
        if not row:
            missing.append(n);continue
        if row.get('kind') in {'replacement','inlined','native','trait'}:
            if not row.get('basis') or not row.get('conditions') or not row.get('rust_item'):
                raise Failure('plan_contract_failed','An implementation boundary needs rust_item, basis and conditions',row)
            boundaries.append(row)
        else: todo.extend(model['entities'].get(n,{}).get('dependencies',[]))
    if missing: raise Failure('plan_contract_failed','Describe actual realizations at this source frontier; merged/inline/native realizations need basis, conditions and a real owning rust_item',{'missing':sorted(missing)})
    check_exports(bundle,files,mapping)
    return {'status':'passed','frontier_entities':len(visited),'boundaries':boundaries,
        'scope':'Declared coverage and existing Rust item/generic syntax checks, not semantic proof. Boundaries retain their entire source closure for review.'}


def payload(branch, cfg, work):
    bundle=branch['bundle'];versions=tc.register(bundle,Path(work)/'context/materials',branch['files'])
    mode=branch['mode'];feedback=branch.get('feedback')
    index=rust_index(branch['files'])
    expanded=branch.get('repeat_count',0)>0
    chosen=select(index,feedback,expanded) if mode=='repair' else index['items']
    names={r['name'] for r in chosen if r['name']}
    related=[r for r in branch['mapping'] if (r.get('rust_item') or '').split('::')[-1] in names]
    focus=set(bundle['source_model']['entries'])|{r['source'] for r in related}
    focus.update(row['id'] for row in branch.get('extra',{}).get('entities',[]) if row.get('id'))
    if mode=='repair':
        for e in bundle['source_model']['entities'].values():
            short=e['name'].rsplit('.',1)[-1]
            if len(short)>2 and re.search(r'\b'+re.escape(short)+r'\b',str(feedback)):focus.add(e['id'])
    program=material(bundle,branch.get('pending_material',{}))
    program['retained_references']=branch.get('extra',{}).get('references',{})
    program['program_model']=source_view(bundle,focus,expanded)
    files=branch['files']
    # Preserve every whole relevant file; no fixed character cut through a body.
    selected={r['file'] for r in chosen}|set(index['parse_error_files'])
    current={n:t for n,t in files.items() if n in selected or mode!='repair'}
    session=tc.Conversation(Path(work)/'context/source-conversation.json',cfg)
    session.archive=tc.Archive(bundle['_context_archive']);session.enter(mode)
    out={'task':{'generate':'Generate a complete Rust library from the source graph and revisable analysis.',
        'quick_refine':'Review this first complete implementation BEFORE compilation. Return accept if sound, or a concrete quality patch. Do not invent compiler success.',
        'repair':'Repair the existing implementation using the current diagnostic and source evidence. Explain and patch in the same response when sufficient.',
        'review':'Review quality affected by repairs and the test connection. Accept if no concrete changes are needed.'}[mode],
        'controller_state':{'phase':mode,'repeat_count':branch.get('repeat_count',0)},
        'program':program,'current_files':current,'current_mapping':branch['mapping'],
        'dependencies':branch['plan']['dependencies'],'build_dependencies':branch['plan'].get('build_dependencies',{}),
        'code_version':versions['code_version'],'material_versions':versions,
        'read_material_version':tc.Archive(bundle['_context_archive']).put('reads',branch.get('extra',{})),
        'rust_index':{**index,'items':[{k:v for k,v in r.items() if k!='text'} for r in index['items']]},
        'related_rust_items':[{k:v for k,v in row.items() if k!='text'} for row in chosen], 'program_state':pm.context_record(branch),
        'feedback':feedback,'original_issue':deepcopy(branch.get('repair_issue')),
        'recent_attempts':branch.get('repair_history',[])[-5:],
        'available_actions':['generate','accept (quality phases)','request_entities','request_files','request_sources','request_references','request_diagnostics','repair_connection'],
        '_conversation':session}
    from .repair_actions import EditController
    controller=EditController(Path(work)/'context/algorithm-actions','algorithm',session.archive)
    out['edit_protocol']=controller.protocol(files)
    out['edit_protocol']['mapping']='mapping merges records by source ID. remove_mapping:[source_id] explicitly removes existing records. Original source/export coverage is always rechecked; deleting required coverage does not bypass validation.'
    out['repair_execution']=controller.context(files)
    if out['repair_execution']['recovery']:
        out['current_files']=deepcopy(files)
    if mode in {'quick_refine','review'}:
        from .code_quality import findings
        out['quality_findings']=findings(files)
    return out
