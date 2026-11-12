"""Dependency-first, transactional source translation with independent final gates."""
from copy import deepcopy
from pathlib import Path
import json
import re
import shutil
import difflib
from .common import Failure, read, save, now
from . import task_context as tc, test_connector
from .knowledge import requested, merge_mapping, apply_files
from .segmentation import partition, next_unit, consumers, project_functions
from .segmented_context import pages, ask, read_pages, reading_notes, code_pages
from .segmented_config import rust_config, materialize, cargo_command, cargo_text
from .segmented_contract import coverage, items, resolve, validate_item, probes, canonical
from .repair_diagnostics import compiler_messages, runtime
from .validation import check_suite, add_regressions
from .suites import input_bits, in_numeric_domain, scoped_performance_input
from .code_quality import findings


def version(state):
    return tc.fingerprint({k:state[k] for k in ['files','mapping','rust_config','partition']})


def compile_crate(crate,rc,cfg,executor,library=True):
    args=['--release','--message-format=json']
    if library:args+=['--lib']
    result=executor.run(cargo_command(rc,cfg,'build',crate,*args),timeout=cfg['budgets']['build_seconds'],check=False)
    out={'status':'passed' if result['status']=='passed' else 'compile_failed',
         'checks':{'build':result},'diagnostics':compiler_messages(result),
         'raw_diagnostic':Path(result['stderr']).read_text() if result['status']!='passed' else ''}
    if not library and out['status']=='passed':
        root=Path(crate)/'target'
        if rc['target']:root/=rc['target']
        out['binary']=str(root/'release/i2r_harness')
    if library and result['status']=='passed' and cfg['testing'].get('clippy') not in {None,'off'}:
        lint=executor.run(cargo_command(rc,cfg,'clippy',crate,'--lib','--release'),timeout=cfg['budgets']['build_seconds'],check=False)
        out['advisory_clippy']=lint
    return out


def connection(crate,files,rc,cfg):
    # Use the same edition/toolchain/dependency/feature/config contract as algorithm.
    target=Path(crate)/'harness';target.mkdir(exist_ok=True)
    desired={**files,'src/main.rs':test_connector.driver(cfg['testing']['transport'],timing=not cfg.get('translation',{}).get('correctness_only'))}
    old=read(target/'.managed-files.json') if (target/'.managed-files.json').exists() else []
    for name in set(old)-desired.keys():
        p=target/name
        if p.exists():p.unlink()
    for name,text in desired.items():
        p=target/name;p.parent.mkdir(parents=True,exist_ok=True)
        if name in {'src/lib.rs','src/main.rs'}:text='#![forbid(unsafe_code)]\n'+text
        if not p.exists() or p.read_text()!=text:p.write_text(text)
    text=cargo_text(rc,package='i2r_harness',transport=cfg['testing']['transport'])
    dependency='i2r_candidate = { path = "..", default-features = '+str(rc['default_features']).lower()+', features = '+json.dumps(rc['enabled_features'])+' }\n'
    text=text.replace('[dependencies]\n','[dependencies]\n'+dependency)
    (target/'Cargo.toml').write_text(text);save(target/'.managed-files.json',sorted(desired))
    return target


def review_required(state, phase, cfg):
    if phase in {'whole_review'} or state.get('unit') is None:
        ids={n for u in state['partition']['units'].values() for n in u['members']}
        ids|={r['source'] for r in state['mapping']}
    else:
        u=state['partition']['units'][state['unit']]
        ids=set(u['members'])|set(u['boundary_sources'])
        for n in u['members']:
            e=state['bundle']['source_model']['entities'][n]
            ids.update(e.get('callers',[]))
            ids.update(d for d in e.get('dependencies',[]) if d in state['partition']['owner'])
    ps=pages(state['bundle']['source_model'],ids,cfg['segmented']['source_page_characters'])
    return ids,ps


def required_routes(state,cfg):
    ids,_=review_required(state,state['phase'],cfg)
    return sorted(ids & project_functions(state['bundle']['source_model']) & {r['source'] for r in state['mapping']})


def validate_routes(state,reply,cfg):
    routes=reply.get('algorithm_routes',[])
    if not isinstance(routes,list) or any(not isinstance(r,dict) for r in routes):
        raise Failure('incomplete_algorithm_review','algorithm_routes must be a list of source-to-Rust route comparisons')
    rows={r.get('source'):r for r in routes}
    for n in required_routes(state,cfg):
        r=rows.get(n,{})
        if not all(isinstance(r.get(k),str) and r[k].strip() for k in ['source_route','rust_route','transformation','reason']):
            raise Failure('incomplete_algorithm_review','Compare the actual source computation route with the actual Rust body for each mandatory function',n)
        if r.get('classification') not in {'preserved','implementation_only'}:
            raise Failure('algorithm_route_changed','The user chose to preserve source algorithms. Restore source recurrence/traversal; equivalent closed forms or alternate algorithms are not authorized.',r)


def payload(state,cfg,work):
    phase=state['phase'];ids,ps=review_required(state,phase,cfg)
    scope=phase+':'+str(state.get('unit'))+':'+version(state)
    if state.get('read_scope')!=scope:
        state['read_scope']=scope;state['seen_pages']=[];state['seen_code_pages']=[];state['reading_notes']={}
    supplied=[];chars=0
    for p in ps:
        if chars+len(p['text'])>cfg['segmented']['initial_source_characters']:break
        supplied.append(p);chars+=len(p['text'])
    catalog=items(state['files']);current=state['files']
    # Whole files are never truncated. If oversized, provide identities and let
    # explicit versioned file/range reads fetch the exact necessary definitions.
    if sum(map(len,current.values()))>cfg['segmented']['initial_code_characters']:
        owners={r['rust_item'] for r in state['mapping'] if r['source'] in ids and r.get('rust_item')}
        selected={validate_item(catalog,r)['file'] for r in state['mapping'] if r['source'] in ids and r.get('rust_item')}
        current={n:t for n,t in current.items() if n in selected and len(t)<=cfg['segmented']['initial_code_characters']}
    cps=code_pages(state['files'],cfg['segmented']['source_page_characters']);code_supplied=[]
    code_size=sum(len(t) for t in current.values())
    for p in cps:
        if p['file'] in current:continue
        if code_size+len(p['text'])>cfg['segmented']['initial_code_characters']:break
        code_supplied.append(p);code_size+=len(p['text'])
    versions=tc.register(state['bundle'],Path(work)/'context/materials',state['files'])
    out={'controller_state':{'phase':phase,'unit':state.get('unit'),'state_version':version(state),
            'completed_units':sorted(state['completed']),'transaction_rule':'Reply is bound to this exact files/mapping/config/partition snapshot'},
        'task':'Implement/review only current unit and required affected dependencies' if phase not in {'whole_review'} else 'Review the complete assembled program',
        'unit':state['partition']['units'].get(state.get('unit')),
        'partition':{k:v for k,v in state['partition'].items() if k!='original_graph'},
        'program':{'entries':state['bundle']['source_model']['entries'],'numeric_policy':state['bundle']['numeric_policy'],
            'global_analysis':state['bundle']['semantic_analysis'],'source_pages':supplied},
        'page_catalog':[{k:v for k,v in p.items() if k!='text'} for p in ps],
        'required_review_sources':sorted(ids),
        'algorithm_policy':cfg['segmented']['algorithm_policy'],'required_algorithm_routes':required_routes(state,cfg),
        'reading_protocol':'request_pages:[id,...] retrieves exact pages; request_files uses the current code_version and exact paths. All required pages must be read before review acceptance.',
        'seen_pages':state['seen_pages'],'current_files':current,'current_mapping':state['mapping'],
        'code_pages':code_supplied,'code_page_catalog':[{k:v for k,v in p.items() if k!='text'} for p in cps],
        'reading_notes':state['reading_notes'],
        'rust_config':state['rust_config'],'code_version':versions['code_version'],
        'rust_items':{n:[{k:v for k,v in row.items() if k not in {'text','references'}} for row in rs] for n,rs in catalog.items()},
        'material_versions':versions,'requested_material':state.get('extra',{}),
        'feedback':state.get('feedback'),'open_failures':state['failures'],
        'quality_findings':findings(state['files']), 'development_performance':state.get('development_performance'),
        'recent_transactions':state['transactions'][-5:],'static_feedback':state.get('static_feedback')}
    # Bound initial views, never the archived facts. Dropped pages/files remain
    # catalogued and must actually be read before a review can complete.
    cap=cfg['segmented']['max_request_characters']-20000
    while len(json.dumps(out,ensure_ascii=False))>cap:
        if out['program']['source_pages']:out['program']['source_pages'].pop()
        elif out['code_pages']:out['code_pages'].pop()
        elif out['current_files']:
            if out['current_files'] is state['files']:out['current_files']=dict(out['current_files'])
            del out['current_files'][max(out['current_files'],key=lambda n:len(out['current_files'][n]))]
        else:break
    if len(json.dumps(out,ensure_ascii=False))<=cap:
        state['seen_pages']=sorted(set(state['seen_pages'])|{p['id'] for p in out['program']['source_pages']+out['requested_material'].get('pages',[])})
        state['seen_code_pages']=sorted(set(state['seen_code_pages'])|{p['id'] for p in cps if p['file'] in out['current_files']}|{p['id'] for p in out['code_pages']+out['requested_material'].get('code_pages',[])})
    out['seen_pages']=state['seen_pages'];out['seen_code_pages']=state['seen_code_pages']
    return out,{p['id']:p for p in ps}


def preserve_readings(state,reply,request,page_map):
    cp={p['id']:p for p in request['code_page_catalog']}
    extra=request['requested_material']
    if set(page_map)-set(state['seen_pages']) or set(cp)-set(state['seen_code_pages']) or extra.get('pages') or extra.get('code_pages'):
        supplied={p['id'] for p in request['program']['source_pages']+request['code_pages']+extra.get('pages',[])+extra.get('code_pages',[])}
        state['reading_notes']=reading_notes(state.get('reading_notes',{}),reply,supplied,{**page_map,**cp})


def validate_review(state,reply,page_map,cfg):
    ids,_=review_required(state,state['phase'],cfg)
    missing=ids-set(reply.get('reviewed_sources',[]))
    missing_pages=set(page_map)-set(state['seen_pages'])
    if missing or missing_pages:
        raise Failure('incomplete_quality_review','Review all required source entities/pages',{'sources':sorted(missing),'unread_pages':sorted(missing_pages)})
    if set(page_map)-set(reply.get('reviewed_pages',[])):
        raise Failure('incomplete_quality_review','Acknowledge every required source page in reviewed_pages',sorted(page_map))
    required_code={p['id'] for p in code_pages(state['files'],cfg['segmented']['source_page_characters'])}
    if required_code-set(state.get('seen_code_pages',[])) or required_code-set(reply.get('reviewed_code_pages',[])):
        raise Failure('incomplete_quality_review','Read and acknowledge every current Rust code page; signatures are not function bodies',{'unread_code_pages':sorted(required_code-set(state.get('seen_code_pages',[]))),'required_code_pages':sorted(required_code)})
    checks=reply.get('review_checks',{})
    if not reply.get('quality_review') or any(not checks.get(k) for k in cfg['segmented']['review_categories']):
        raise Failure('incomplete_quality_review','Supply specific findings for every review category',cfg['segmented']['review_categories'])
    validate_routes(state,reply,cfg)
    # No twenty-finding truncation inherited from the legacy review validator.
    structural={'front_shift','front_insert','tail_copy','iterator_collect','list_cons','owned_copy'}
    answers={r.get('id'):r for r in reply.get('quality_resolutions',[]) if isinstance(r,dict)}
    required=[r for r in findings(state['files']) if r['kind'] in structural]
    missed=[r for r in required if not all(answers.get(r['id'],{}).get(k) for k in ['source_operation','source_cost','rust_cost','reason'])]
    if missed:raise Failure('incomplete_quality_review','Resolve all structural findings or patch actual defects',missed)


def declaration_context(files):
    """Conservative Rust context beyond function bodies, including local impls/macros.

    Import/module/attribute/impl changes can alter existing bodies without editing
    their text. This is a syntax safeguard, not a resolved Rust dependency graph.
    """
    from tree_sitter import Language, Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()))
    result={}
    for path,text in files.items():
        if not path.endswith('.rs'):continue
        data=text.encode();tokens=[]
        def local_effects(node):
            if node.type in {'impl_item','macro_definition','macro_invocation'}:
                tokens.append((node.type,data[node.start_byte:node.end_byte].decode()))
            else:
                for child in node.children:local_effects(child)
        def visit(node):
            if node.type=='attribute_item':
                following=node.next_named_sibling
                while following is not None and following.type in {'attribute_item','line_comment','block_comment'}:
                    following=following.next_named_sibling
                attribute=data[node.start_byte:node.end_byte].decode()
                if (following is not None and following.type=='function_item' and
                        re.fullmatch(r'#\s*\[\s*inline\s*(?:\(\s*(?:always|never)\s*\))?\s*\]',attribute)):
                    # Existing function attributes are compared with their item.
                    # Adding an unused inline helper cannot change other bodies.
                    return
            if node.type=='function_item':
                local_effects(node);return
            if node.type in {'line_comment','block_comment'}:return
            if not node.children:
                tokens.append((node.type,data[node.start_byte:node.end_byte].decode()));return
            for child in node.children:visit(child)
        visit(parser.parse(data).root_node);result[path]=tokens
    return result


def apply_transaction(state,reply,cfg,path):
    proposed=deepcopy(state)
    if reply.get('state_version') not in {None,version(state)}:raise Failure('stale_patch','State has changed; reread')
    files=apply_files(state['files'],reply)
    for name in reply.get('remove_files',[]):
        if name not in files:raise Failure('unknown_edit_file',name)
        del files[name]
    if 'src/lib.rs' not in files:raise Failure('invalid_candidate','Cumulative crate requires src/lib.rs')
    incoming=reply.get('mapping') or []
    pending={n for u,r in state['partition']['units'].items() if u not in state['completed'] and u!=state.get('unit') for n in r['members']}
    if state.get('phase')=='generate' and pending & {r.get('source') for r in incoming}:
        raise Failure('future_unit_generation','Translate current unit before future consumers',sorted(pending & {r.get('source') for r in incoming}))
    mapping=merge_mapping(state['mapping'],reply.get('mapping'),reply.get('remove_mapping'))
    rc=rust_config({**state['rust_config'],**reply.get('rust_config',{})},cfg)
    new_plan=partition(state['bundle']['source_model'],reply['boundaries']) if 'boundaries' in reply else state['partition']
    # Validate all present mapping identities atomically; completeness is checked
    # only when the unit declares completion, permitting staged large edits.
    index=items(files)
    for row in mapping:
        if row['source'] not in state['bundle']['source_model']['entities']:raise Failure('invalid_mapping','Unknown source ID',row)
        if row.get('rust_item'):validate_item(index,row)
    changed=[];old_index=items(state['files'])
    for uid in state['completed']:
        for n in state['partition']['units'][uid]['members']:
            old=next((r for r in state['mapping'] if r['source']==n),None)
            new=next((r for r in mapping if r['source']==n),None)
            if old!=new or (old and any(validate_item(old_index,old).get(k)!=validate_item(index,new).get(k) for k in ['text','attributes'])):
                changed.append(uid);break
    changed_items={name for name,rows in old_index.items() if name not in index or
                   [(r['text'],r.get('attributes')) for r in rows]!=[(r['text'],r.get('attributes')) for r in index[name]]}
    completed_sources={n for uid in state['completed'] for n in state['partition']['units'][uid]['members']}
    completed_items={canonical(row['rust_item']) for row in state['mapping']
                     if row['source'] in completed_sources and row.get('rust_item')}
    # Source dependency edges cover mapped business items. An additional changed
    # helper/type/impl may affect another branch even when one business item also
    # changed. Conservatively invalidate every completed unit for such changes.
    added_names={name.rsplit('::',1)[-1] for name in set(index)-set(old_index)}
    old_references={name for rows in old_index.values() for row in rows for name in row.get('references',[])}
    old_references|={name for rows in old_index.values() for row in rows
                     for name in re.findall(r'\.\s*([A-Za-z_]\w*)',row['text'])}
    # Added declarations can shadow glob imports or change method resolution.
    # Existing named items and the remaining declaration context are both checked.
    if (changed_items-completed_items or added_names & old_references or
            declaration_context(state['files'])!=declaration_context(files)):
        changed=list(state['completed'])
    if rc!=state['rust_config'] or new_plan['version']!=state['partition']['version']:changed=list(state['completed'])
    affected=consumers(state['partition'],changed)
    proposed.update(files=files,mapping=mapping,rust_config=rc,partition=new_plan,
                    completed=[u for u in state['completed'] if u not in affected and u in new_plan['units']])
    proposed['reviews']={u:v for u,v in state['reviews'].items() if u not in affected}
    proposed.pop('behavior_version',None);proposed.pop('whole_review_version',None)
    if version(proposed)==version(state):raise Failure('unchanged_repair','No actual code/config/mapping/partition change')
    diff=''.join(''.join(difflib.unified_diff(state['files'].get(n,'').splitlines(True),files.get(n,'').splitlines(True),fromfile=n,tofile=n)) for n in sorted(set(state['files'])|set(files)))
    (Path(path)/'changes.diff').write_text(diff)
    event={'before':version(state),'after':version(proposed),'invalidated':sorted(affected),'path':str(path)}
    proposed['transactions'].append(event)
    save(Path(path)/'transaction.json',{'event':event,'before':{k:state[k] for k in ['files','mapping','rust_config','partition']},
                                     'after':{k:proposed[k] for k in ['files','mapping','rust_config','partition']}})
    return proposed
