"""Dependency-first, transactional source translation with independent final gates."""
from copy import deepcopy
from pathlib import Path
import json
import re
import shutil
import difflib
import time
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
from . import repair_controller as repair_controller, performance_search as performance_search
from .segmented_contract import interfaces
from .code_quality import findings
from . import review_scope as review_scope
from . import semantic_components as component_scope
from . import implementation_strategy as strategy
from . import material_progress
from . import native_numeric_contracts as native_contracts


def version(state):
    return tc.fingerprint({**{k:state[k] for k in ['files','mapping','rust_config','partition']}, 'strategy':{k:v for k,v in strategy.current(state).items() if k!='history'}})


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
    if phase in {'whole_review','performance_review'} or state.get('unit') is None:
        ids={n for u in state['partition']['units'].values() for n in u['members']}
        ids|={r['source'] for r in state['mapping']}
    else:
        u=state['partition']['units'][state['unit']]
        members=component_scope.review_members(state) if phase=='refine' else set(u['members'])
        ids=members|set(u['boundary_sources'])
        for n in members:
            e=state['bundle']['source_model']['entities'][n]
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
        state['read_scope']=scope;state['seen_pages']=[];state['seen_code_pages']=[];state['reading_notes']={};state['generation_full_files_seen']=[];state['seen_evidence_page_ids']=[];state['evidence_reading_notes']={}
    supplied=[];chars=0
    for p in ps:
        if chars+len(p['text'])>cfg['segmented']['initial_source_characters']:break
        supplied.append(p);chars+=len(p['text'])
    catalog=items(state['files'])
    review_files,cps,review_ranges=review_scope.view(state,ids,cfg)
    whole=phase in review_scope.WHOLE or state.get('unit') is None
    current=state['files'] if (whole or phase in {'generate','repair'}) and sum(map(len,state['files'].values()))<=cfg['segmented']['initial_code_characters'] else {}
    code_supplied=[];code_size=sum(map(len,current.values()))
    for p in cps:
        if p['file'] in current:continue
        if code_size+len(p['text'])>cfg['segmented']['initial_code_characters']:break
        code_supplied.append(p);code_size+=len(p['text'])
    versions=tc.register(state['bundle'],Path(work)/'context/materials',state['files'])
    out={'controller_state':{'phase':phase,'unit':state.get('unit'),'state_version':version(state),
            'strategy_version':tc.fingerprint(strategy.current(state)), 'completed_units':sorted(state['completed']),'transaction_rule':'Reply is bound to this exact files/mapping/config/partition snapshot'},
        'task':'Implement/review only current unit and required affected dependencies' if phase not in {'whole_review','performance_review'} else 'Review the complete assembled program',
        'unit':state['partition']['units'].get(state.get('unit')),
        'partition':{k:v for k,v in state['partition'].items() if k!='original_graph'},
        'program':{'entries':state['bundle']['source_model']['entries'],'numeric_policy':state['bundle']['numeric_policy'],
            'current_strategy':strategy.project(state,ids),'source_pages':supplied,'native_numeric_contracts':native_contracts.context(state)},
        'page_catalog':[{k:v for k,v in p.items() if k!='text'} for p in ps],
        'required_review_sources':sorted(ids),
        'algorithm_policy':cfg['segmented']['algorithm_policy'],'required_algorithm_routes':required_routes(state,cfg),
        'reading_protocol':'request_pages:[id,...] retrieves exact pages; request_files uses the current code_version and exact paths. All required pages must be read before review acceptance.',
        'repair_progress_feedback':({'consecutive_no_progress':state.get('no_progress',0),
            'latest_verified_progress':next((a['verified_progress'] for a in reversed(state.get('attempts',[])) if 'verified_progress' in a),None),
            'instruction':'Repeated reads have not established a repair. Compare the current compiler evidence with candidate declarations and injected test code separately: a missing candidate trait implementation is different from an incomplete or conflicting test fixture impl. Use exact diagnostic spans and current signatures; do not infer ownership from the shared src/lib.rs filename. Request only missing evidence, retain string-valued exact-page notes, then propose a permitted concrete change. Existing tests, expectations and permissions remain unchanged; the request budget does not reset.'}
            if phase=='repair' and state.get('no_progress',0)>=2 else None),
        'seen_pages':state['seen_pages'],'current_files':current,'current_mapping':state['mapping'],
        'code_pages':code_supplied,'code_page_catalog':[{k:v for k,v in p.items() if k!='text'} for p in cps],
        'reading_notes':state['reading_notes'],'evidence_reading_notes':state.get('evidence_reading_notes',{}),
        'rust_config':state['rust_config'],'code_version':versions['code_version'],
        'rust_items':{n:[{k:v for k,v in row.items() if k not in {'text','references'}} for row in rs] for n,rs in catalog.items()},
        'material_versions':versions,'requested_material':state.get('extra',{}),
        'feedback':state.get('feedback'),'open_failures':[f for f in state['failures'] if f['status']=='open'],
        'review_scope':{'kind':'whole_program' if whole else 'unit_and_dependencies','members_to_review':sorted(component_scope.review_members(state)) if phase=='refine' else [],'code_pages_are_excerpts':not whole,'instruction':'Blank lines in unit code pages omit unrelated code while preserving original line numbers. Use exact edits; request the full file before replacing it. Additional full files remain available on request. A repair may require review of only members_to_review; unchanged component members retain their recorded evidence.'},
        'quality_findings':[] if not quality_reviews_enabled(cfg) else [r for r in findings(state['files']) if review_ranges is None or r['line'] in review_ranges.get(r['file'],set())], 'development_performance':state.get('development_performance'),
        'recent_transactions':state['transactions'][-5:],'static_feedback':state.get('static_feedback'),
        'repair_issue':repair_controller.active(state),'targeted_references':repair_controller.targeted_material(state) if phase=='repair' else {},
        'optimization_attempts':state.get('optimization_attempts',[]),
        'source_optimization':{'enabled':False,'execution':'unimplemented; report source bottlenecks only'}}
    if cfg.get('translation',{}).get('correctness_only') and phase=='generate':
        from .generation_context import compact
        out=compact(out,state)
        state['generation_body_view_version']=version(state)
        state['generation_bodies_withheld']=out['generation_context']['dependency_bodies_initially_withheld']
    if phase=='repair':
        issue=repair_controller.active(state)
        if issue and issue['kind']=='support':
            out['source_api_binding_repair_contract']={
                'policy':'source-api-then-protected-binding-v1',
                'candidate_authority':'Return action=generate with candidate edits/mapping and repair_hypothesis; explicit strategy_updates may revise an earlier model-chosen interface with source evidence. Existing model strategy prose is not proof of source semantics.',
                'two_stage_execution':'A source-faithful API change may temporarily make old frozen call bindings fail compilation. This is permitted: the controller replays the original suite, then independently audits those actual binding errors against the new API. You do not need to satisfy an obsolete borrow/call form in the candidate, and must not rewrite test files yourself.',
                'binding_authority':'The independent protected binding audit may adapt ownership/call construction outside frozen assertions, preserving the exact logical input values/order/multiplicity, all expectations/assertion invocations/helpers and obligations, and non-Clone or other generic-strength test types. No derive/trait addition merely to silence a bound, test deletion, unsafe duplication, or new expectation is allowed. Unsupported changes must remain unresolved.',
                'generic_semantics':'A source operation with no element capability constraint must retain a usable unconstrained realization when ownership permits it. A documented copying requirement for a borrowing convenience path or a caller that reuses data does not authorize imposing it on every source-polymorphic path. Evaluate actual source equations and admitted adaptation conditions, not just a model-declared signature.',
                'acceptance':'After the API transaction and any protected binding correction, all original source responsibilities must actually compile and execute. Only a real semantic assertion failure invokes independent source checking; source pass then locks the candidate before differential acceptance. repair_connection never targets source-test bindings.'}
        out=repair_controller.bounded_evidence(out,state['bundle'],cfg)
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
    if cfg.get('translation',{}).get('correctness_only') or len(json.dumps(out,ensure_ascii=False))<=cap:
        state['seen_pages']=sorted(set(state['seen_pages'])|{p['id'] for p in out['program']['source_pages']+out['requested_material'].get('pages',[])})
        state['seen_code_pages']=sorted(set(state['seen_code_pages'])|{p['id'] for p in cps if p['file'] in out['current_files']}|{p['id'] for p in out['code_pages']+out['requested_material'].get('code_pages',[])})
    if phase=='generate':
        seen=set(state.get('generation_full_files_seen',[]))|set(out['current_files'])
        for row in out['requested_material'].get('files',[]):
            name=row.get('path')
            if name in state['files'] and row.get('version')==versions['code_version'] and row.get('start_line')==1 and row.get('end_line',0)>=len(state['files'][name].splitlines()):seen.add(name)
        state['generation_full_files_seen']=sorted(seen)
    out['seen_pages']=state['seen_pages'];out['seen_code_pages']=state['seen_code_pages']
    return out,{p['id']:p for p in ps}


def preserve_readings(state,reply,request,page_map):
    cp={p['id']:p for p in request['code_page_catalog']}
    extra=request['requested_material']
    # Event notes are diagnostic evidence, never source-reading or source citations.
    # Only exact IDs already actually delivered in this read scope are eligible.
    seen=state.setdefault('seen_evidence_page_ids',[])
    for p in extra.get('evidence_pages',[]):
        if p['id'] not in seen:seen.append(p['id'])
    event_notes={k:v for k,v in reply.get('reading_notes',{}).items() if k in seen} if isinstance(reply.get('reading_notes',{}),dict) else {}
    if any(not isinstance(v,str) or not v.strip() for v in event_notes.values()):
        raise Failure('invalid_reading_notes','Diagnostic notes must be nonempty strings keyed by an actually delivered exact event ID')
    source_reply={**reply,'reading_notes':{k:v for k,v in reply.get('reading_notes',{}).items() if k not in event_notes}} if isinstance(reply.get('reading_notes',{}),dict) else reply
    if set(page_map)-set(state['seen_pages']) or set(cp)-set(state['seen_code_pages']) or extra.get('pages') or extra.get('code_pages'):
        supplied={p['id'] for p in request['program']['source_pages']+request['code_pages']+extra.get('pages',[])+extra.get('code_pages',[])}
        state['reading_notes']=reading_notes(state.get('reading_notes',{}),source_reply,supplied,{**page_map,**cp})
    elif source_reply.get('reading_notes'):
        state['reading_notes']=reading_notes(state.get('reading_notes',{}),source_reply,set(),{**page_map,**cp})
    state['evidence_reading_notes']={**state.get('evidence_reading_notes',{}),**event_notes}


def validate_review(state,reply,page_map,cfg):
    ids,_=review_required(state,state['phase'],cfg)
    missing=ids-set(reply.get('reviewed_sources',[]))
    missing_pages=set(page_map)-set(state['seen_pages'])
    if missing or missing_pages:
        raise Failure('incomplete_quality_review','Review all required source entities/pages',{'sources':sorted(missing),'unread_pages':sorted(missing_pages)})
    if set(page_map)-set(reply.get('reviewed_pages',[])):
        raise Failure('incomplete_quality_review','Acknowledge every required source page in reviewed_pages',sorted(page_map))
    review_files,review_pages,review_ranges=review_scope.view(state,ids,cfg)
    required_code={p['id'] for p in review_pages}
    if required_code-set(state.get('seen_code_pages',[])) or required_code-set(reply.get('reviewed_code_pages',[])):
        raise Failure('incomplete_quality_review','Read and acknowledge every current Rust code page; signatures are not function bodies',{'unread_code_pages':sorted(required_code-set(state.get('seen_code_pages',[]))),'required_code_pages':sorted(required_code)})
    checks=reply.get('review_checks',{})
    if not reply.get('quality_review') or any(not checks.get(k) for k in cfg['segmented']['review_categories']):
        raise Failure('incomplete_quality_review','Supply specific findings for every review category',cfg['segmented']['review_categories'])
    validate_routes(state,reply,cfg)
    # No twenty-finding truncation inherited from the legacy review validator.
    structural={'front_shift','front_insert','tail_copy','iterator_collect','list_cons','owned_copy'}
    answers={r.get('id'):r for r in reply.get('quality_resolutions',[]) if isinstance(r,dict)}
    required=[] if cfg.get('translation',{}).get('correctness_only') else [r for r in findings(state['files']) if r['kind'] in structural and (review_ranges is None or r['line'] in review_ranges.get(r['file'],set()))]
    missed=[r for r in required if not all(answers.get(r['id'],{}).get(k) for k in ['source_operation','source_cost','rust_cost','reason'])]
    if missed:raise Failure('incomplete_quality_review','Resolve all structural findings or patch actual defects',missed)


def declaration_context(files,*,include_function_signatures=True):
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
                # Signature edits use conservative invalidation even if the
                # changed helper is outside a bounded review excerpt. Keep its
                # contract in the same context used by the duplicate guard.
                # Schema 3 replay explicitly omits this newly tracked context.
                if include_function_signatures:
                    body=node.child_by_field_name('body')
                    for child in node.children:
                        if child!=body:visit(child)
                local_effects(node);return
            if node.type in {'line_comment','block_comment'}:return
            if not node.children:
                tokens.append((node.type,data[node.start_byte:node.end_byte].decode()));return
            for child in node.children:visit(child)
        visit(parser.parse(data).root_node);result[path]=tokens
    return result


def apply_transaction(state,reply,cfg,path):
    from .test_order_policy import guard_edit
    guard_edit(state)
    proposed=deepcopy(state)
    if reply.get('state_version') not in {None,version(state)}:raise Failure('stale_patch','State has changed; reread')
    if (state.get('phase')=='generate' and state.get('generation_bodies_withheld')
            and state.get('generation_body_view_version')==version(state)):
        unread=(set(reply.get('files',{}))&set(state['files']))-set(state.get('generation_full_files_seen',[]))
        if unread:raise Failure('unread_file_replacement','Read exact full current files before replacing them, or use version-bound append_files',sorted(unread))
    from .generation_context import expand_append
    reply=expand_append(state,reply,version(state))
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
    new_plan=state['partition']
    if 'boundaries' in reply or 'components' in reply:
        if new_plan.get('policy')=='semantic-components':
            new_plan=component_scope.compose(state['bundle']['source_model'],reply.get('boundaries',new_plan['boundaries']),reply.get('components',new_plan['components']))
        else:new_plan=partition(state['bundle']['source_model'],reply['boundaries'])
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
    context_files,independent_additions=review_scope.independent_additions_removed(state['files'],files)
    body_changes,body_affected=review_scope.body_change_impact(state,files,mapping,cfg,changed_items)
    changed=list(set(changed)|body_affected)
    reasons=[]
    if changed:reasons.append('existing mapped item or mapping changed')
    if (changed_items-completed_items-body_changes or added_names & old_references or
            declaration_context(state['files'])!=declaration_context(context_files)):
        reasons.append('shared item, name resolution, import/impl/macro or declaration context changed')
        changed=list(state['completed'])
    if rc!=state['rust_config'] or new_plan['version']!=state['partition']['version']:
        changed=list(state['completed']);reasons.append('configuration or partition changed')
    proposed['implementation_strategy']=strategy.revise(state,reply,files,mapping,rc,new_plan)
    strategy_dirty=strategy.affected(state,proposed)
    changed=list(set(changed)|{state['partition']['owner'][n] for n in strategy_dirty})
    if strategy_dirty:reasons.append('effective implementation strategy changed')
    affected=consumers(state['partition'],changed)
    if quality_reviews_enabled(cfg) and state['partition'].get('policy')=='semantic-components':
        global_change=any(r in reasons for r in ['shared item, name resolution, import/impl/macro or declaration context changed','configuration or partition changed'])
        # Compare old evidence against the new code with proven independent
        # additions removed. Otherwise the lexical view's conservative inclusion
        # of every impl for a referenced type defeats the exemption above.
        dirty=component_scope.affected_sources(state,context_files,mapping,cfg,global_change)|strategy_dirty
        affected={state['partition']['owner'][n] for n in dirty}
        if new_plan['version']!=state['partition']['version']:
            proposed['dirty_sources']={};proposed['source_reviews']={}
        else:
            for uid in affected:
                proposed.setdefault('dirty_sources',{})[uid]=sorted(set(proposed.get('dirty_sources',{}).get(uid,[]))|{n for n in dirty if state['partition']['owner'][n]==uid})
            for n in dirty:proposed.setdefault('source_reviews',{}).pop(n,None)
    proposed.update(files=files,mapping=mapping,rust_config=rc,partition=new_plan,
                    completed=[u for u in state['completed'] if u not in affected and u in new_plan['units']])
    proposed['reviews']={u:v for u,v in state['reviews'].items() if u not in affected}
    if strategy.project(state,binding=True)!=strategy.project(proposed,binding=True) or files!=state['files'] or mapping!=state['mapping'] or rc!=state['rust_config'] or new_plan!=state['partition']:
        proposed.pop('behavior_version',None);proposed.pop('whole_review_version',None)
    elif state.get('behavior_version')==tc.fingerprint([version(state),state.get('connector',{})]):
        proposed['behavior_version']=tc.fingerprint([version(proposed),state.get('connector',{})])
    if version(proposed)==version(state):raise Failure('unchanged_repair','No actual code/config/mapping/partition change')
    diff=''.join(''.join(difflib.unified_diff(state['files'].get(n,'').splitlines(True),files.get(n,'').splitlines(True),fromfile=n,tofile=n)) for n in sorted(set(state['files'])|set(files)))
    (Path(path)/'changes.diff').write_text(diff)
    event={'before':version(state),'after':version(proposed),'invalidated':sorted(affected),'invalidated_completed':sorted(set(state['completed']) & affected),'invalidation_reasons':reasons,'body_changes':sorted(body_changes),'body_affected':sorted(body_affected),'independent_additions':independent_additions,'path':str(path)}
    proposed['transactions'].append(event)
    save(Path(path)/'transaction.json',{'event':event,'before':{**{k:state[k] for k in ['files','mapping','rust_config','partition']},'implementation_strategy':strategy.current(state),
                                     **{k:deepcopy(state.get(k,{} if k!='completed' else [])) for k in ['completed','reviews','source_reviews','dirty_sources']}},
                                     'after':{k:proposed[k] for k in ['files','mapping','rust_config','partition','implementation_strategy']}})
    return proposed


def connector_identity(state):
    from .verification_identity import interfaces_for_cache
    from .connector_templates import overflow_markers
    return tc.fingerprint([overflow_markers(state['files']),interfaces_for_cache(state['files']),state['mapping'],state['rust_config'],strategy.test_identity(state),state.get('connector_scenarios'),state.get('transport'),state.get('bundle',{}).get('numeric_policy'),state.get('observation_ownership_identity')])


def reject_source_challenge(state):
    """A model-selected action cannot initiate the final source failure checker."""
    if state.get('source_candidate_lock'):
        raise Failure('source_candidate_locked','Source validation is terminal for candidate edits; the actual assertion failure dispatcher owns its single independent check')
    raise Failure('invalid_action','challenge_support_test is not an available action. Before source validation, diagnose the active compile/differential issue. repair_connection is only for a differential driver or wire-conversion defect after the source stage, never for a frozen source-test binding. For a source-stage candidate/API defect return an explicit generate transaction and repair_hypothesis; original source compilation/execution and protected binding audit remain mandatory. Do not change reference expectations. The independent source checker is dispatched only by an actual final source assertion failure.')


def go_after_support(state,testing_project):
    from .test_order_policy import transition
    transition(state,testing_project)


def quality_reviews_enabled(cfg):
    return not cfg.get('translation',{}).get('correctness_only') and bool(cfg.get('translation',{}).get('performance_refinement',False))


def unit_check_phase(cfg):
    return 'refine' if quality_reviews_enabled(cfg) else 'compile'


def integration_phase(cfg):
    return 'whole_review' if quality_reviews_enabled(cfg) else 'final_compile'


def advance_unit(state,cfg):
    state['unit']=next_unit(state['partition'],state['completed'])
    if state['unit']:
        state['phase']=unit_check_phase(cfg) if all(any(r['source']==n for r in state['mapping']) for n in state['partition']['units'][state['unit']]['members']) else 'generate'
    else:state['phase']='final_compile' if state.get('optimization_parent') else integration_phase(cfg)


def resume_after_replay(state,cfg,issue):
    from . import test_order_policy as order_policy
    # Original reproducer success is not full differential acceptance. A locked
    # source-first candidate may only continue the unchanged acceptance suites.
    if order_policy.source_first(state) and state.get('source_candidate_lock') and issue['kind']=='behavior':
        order_policy.guard_phase(state,'test')
        state['phase']='test';state['feedback']=None
        return
    state['phase']=issue['return_phase'];state['feedback']=None
    if not quality_reviews_enabled(cfg):advance_unit(state,cfg)
    if state['phase']=='refine' and state['partition'].get('policy')=='semantic-components':
        state['unit']=next_unit(state['partition'],state['completed'])
        if state['unit'] is None:state['phase']='whole_review'
    if state['phase']=='whole_review' and len(state['completed'])<len(state['partition']['units']):
        state['unit']=next_unit(state['partition'],state['completed']);state['phase']='refine'


def revert_optimization(state,reason):
    strategy.restore_check(state['optimization_parent'])
    parent=state.pop('optimization_parent')
    state.setdefault('strategy_archives',[]).append(deepcopy(strategy.current(state)))
    state['implementation_strategy']=deepcopy(parent['implementation_strategy'])
    for key in ['files','mapping','rust_config','partition','connector','completed','reviews']:
        state[key]=deepcopy(parent[key])
    state['optimization_attempts'][-1].update(status='reverted',reason=reason)
    state['optimization_no_gain']=state.get('optimization_no_gain',0)+1
    state['behavior_version']=tc.fingerprint([version(state),state['connector']])
    state['connector_identity']=connector_identity(state)
    state['unit']=None;state['phase']='performance_review';state['feedback']=None
    state['binary']=parent['binary']
    state['harness']=parent['harness']
    from .verification_identity import VERIFIED_STATE_FIELDS
    for key in VERIFIED_STATE_FIELDS:state.pop(key,None)
    state.update(deepcopy(parent['verification_state']))
    state['development_performance']=parent['development_performance']
    for issue in state['repair_issues']:
        if issue['status']=='open':issue['status']='reverted_candidate'
    # Revert restores a previously verified snapshot; failed trial evidence is
    # retained separately, never allowed to invalidate the parent's validity.
    for f in state['failures']:
        if f['status']=='open':f.update(status='reverted_candidate',reason=reason)


def checkpoint_identity(bundle,cfg,connector_scenarios):
    from .repair_knowledge import manifest as knowledge_manifest
    fields={'native_numeric_contracts':native_contracts.context({'bundle':bundle}),'knowledge':knowledge_manifest(),'workflow_schema':'compile-integration-v5',
            'source':bundle['source_model'],'config':cfg,'analysis':bundle['semantic_analysis'],
            'connector_scenarios':connector_scenarios}
    if bundle.get('prepared_identity'):fields['prepared_identity']=bundle['prepared_identity']
    return tc.fingerprint(fields)


def search(bundle,testing_project,cfg,provider,work,executor,refs,fixed_inputs,random_inputs,regressions,update):
    work=Path(work);checkpoint=work/'segmented-checkpoint.json'
    from .common import digest
    from .observation_helpers import scenario_identity
    connector_scenarios=scenario_identity(testing_project) if testing_project else {}
    identity=checkpoint_identity(bundle,cfg,connector_scenarios)
    if checkpoint.exists():
        state=read(checkpoint)
        legacy_phases=[state.get(k) for k in ['phase','repair_return','support_return']]+[r.get('return_phase') for r in state.get('repair_issues',[])]
        if 'early_support' in legacy_phases or state.get('early_pending') or state.get('early_verified'):
            raise Failure('removed_checkpoint_stage','This checkpoint uses removed early semantic testing. Preserve it and start a fresh run identity.')
        strategy.restore_check(state)
        if state['identity']!=identity:raise Failure('stale_snapshot','Source/config/analysis changed since checkpoint')
    else:
        plan=bundle['segmentation']
        state={'identity':identity,'id':'candidate-1','bundle':deepcopy(bundle),'partition':plan,
            'files':{'src/lib.rs':''},'mapping':[],'rust_config':bundle['rust_config'],
            'unit':next_unit(plan,[]),'phase':'generate','completed':[],'reviews':{},'attempts':[],
            'transactions':[],'failures':[],'connector':{},'feedback':None,'extra':{},'status':'active',
            'seen_versions':{},'no_progress':0,'decisions':[], 'transport':cfg['testing']['transport'],
            'repair_issues':[],'connector_scenarios':connector_scenarios,'optimization_attempts':[],'optimization_no_gain':0}
    if 'implementation_strategy' not in state:
        state['implementation_strategy']=deepcopy(bundle.get('implementation_strategy',strategy.initialize(bundle['semantic_analysis'])))
    from . import test_order_policy as order_policy
    order_policy.configure(state,cfg)
    state['source_suite_review_required']=False
    state['source_failure_review_policy']='failure-responsibility-independent-source-check-v1'
    attempts=state['attempts'];crate=work/'cumulative'
    while state['status']=='active':
        previous_numbers=[int(p.name.rsplit('-',1)[-1]) for p in work.glob('segment-step-[0-9]*') if p.is_dir()]
        num=max([len(attempts)]+previous_numbers)+1;path=work/f'segment-step-{num:04d}';path.mkdir(parents=True,exist_ok=False)
        phase=state['phase'];before=version(state)
        progress_before=material_progress.snapshot(state)
        from .source_failure_check import enforce_lock
        enforce_lock(state)
        order_policy.guard_phase(state,phase)
        if phase not in {'generate','refine','whole_review','compile','final_compile','support','source_test_check','support_execute','support_audit','support_check','connect','test','repair','repair_replay','repair_diagnose','performance','performance_review','finish'}:
            raise Failure('removed_checkpoint_stage','Unknown/removed phase; preserve the checkpoint and start a fresh run identity',phase)
        if phase in {'refine','whole_review','performance_review'} and not quality_reviews_enabled(cfg):
            raise Failure('invalid_workflow_phase','Quality review requires optimization enabled',phase)
        phase_started=time.monotonic();calls_before=provider.calls;usage_before=deepcopy(provider.usage)
        attempt={'attempt':num,'action_phase':phase,'unit':state.get('unit'),'started_at':now(),'state_version':before}
        attempts.append(attempt);state['attempts']=attempts
        update({'phase':phase,'units_completed':len(state['completed']),'units_total':len(state['partition']['units']),
                'active_unit':state.get('unit'),'attempts':attempts,'model_calls':provider.calls})
        try:
            if state['no_progress']>=cfg['segmented']['no_progress_limit']:
                raise Failure('repair_stalled','Repeated actions without verified advancement',state.get('feedback'))
            issue=repair_controller.active(state)
            if issue and issue.get('recurred_after_resolution',0)>=cfg['translation']['repair_stall_limit']:
                raise Failure('repair_stalled','Same resolved issue repeatedly regressed across different versions',issue)
            if phase in {'compile','final_compile'}:
                roots=[n for u in state['completed'] for n in state['partition']['units'][u]['members']]
                if phase=='compile':roots+=state['partition']['units'][state['unit']]['members']
                else:roots=[n for u in state['partition']['units'].values() for n in u['members']]
                last_cumulative=(phase=='compile' and (set(state['completed'])|{state['unit']})==set(state['partition']['units']))
                complete_coverage=(phase=='final_compile' or (cfg.get('translation',{}).get('correctness_only') and last_cumulative))
                attempt['coverage']=coverage(bundle,state['files'],state['mapping'],roots,state['partition'],complete_coverage)
                attempt['native_primitive_structure']=native_contracts.check_realization(state)
                attempt['compilation_scope']='complete_program' if complete_coverage else 'cumulative_units'
                for f in state['failures']:
                    if f['kind']=='contract':f.update(status='closed',verified_version=before)
                materialize(crate,{**state['files'],'src/lib.rs':state['files']['src/lib.rs']+probes(state['mapping'])},state['rust_config'])
                result=compile_crate(crate,state['rust_config'],cfg,executor);attempt['compilation']=result
                if result['status']!='passed':
                    state['feedback']=result;state['repair_return']=unit_check_phase(cfg) if phase=='compile' else integration_phase(cfg);state['phase']='repair'
                    state['failures'].append({'kind':'compile','version':before,'evidence':str(path/'attempt.json'),'status':'open'})
                    repair_controller.register(state,'compile',result,{'roots':roots,'library':True,'final_coverage':complete_coverage},state['repair_return'],state['failures'][-1])
                    if state.get('optimization_parent'):revert_optimization(state,{'kind':'compile_failure','evidence':result})
                else:
                    for f in state['failures']:
                        if f['kind']=='compile':f.update(status='closed',verified_version=before)
                    for issue in state['repair_issues']:
                        if issue['status']=='open' and issue['kind']=='compile' and set(issue['reproducer']['roots'])<=set(roots):issue['status']='verified_passed'
                    state['feedback']=None
                    lint=result.get('advisory_clippy')
                    if lint:state['static_feedback']={'status':lint['status'],'text':Path(lint['stderr']).read_text(),'scope':'Advisory lint, not a correctness verdict'}
                    if phase=='compile':
                        if quality_reviews_enabled(cfg) and state['partition'].get('policy')=='semantic-components':
                            missing=set(state['partition']['units'][state['unit']]['members'])-set(state.get('source_reviews',{}))
                            if missing:raise Failure('incomplete_component_evidence','Every component member needs valid review evidence',sorted(missing))
                            state.setdefault('dirty_sources',{}).pop(state['unit'],None)
                        if state['unit'] not in state['completed']:state['completed'].append(state['unit'])
                        advance_unit(state,cfg)
                        # This exact successful cumulative build already contains every
                        # unit, export check and probe. Only the direct correctness
                        # transition reuses it; repair/rollback/restored final_compile
                        # paths still execute their own compilation.
                        if complete_coverage and cfg.get('translation',{}).get('correctness_only') and state['unit'] is None and not state.get('optimization_parent'):
                            go_after_support(state,testing_project)
                    else:go_after_support(state,testing_project)
            elif phase=='support':
                order_policy.enter_source(state)
                from .segmented_support import prepare,execute
                materialize(crate,{**state['files'],'src/lib.rs':state['files']['src/lib.rs']+probes(state['mapping'])},state['rust_config'])
                pending=next((f for f in state['failures'] if f['kind']=='support' and f['status']=='open'),None)
                frozen=read(work/'support-tests'/(pending['frozen_identity']+'.json')) if pending else read(work/'support-tests'/(state['replay_frozen_identity']+'.json')) if state.get('replay_frozen_identity') else prepare(state,cfg,provider,work/'support-tests')
                # One immutable suite survives candidate repair and issue closure.
                # API changes still invalidate the checker scope and face compile binding guards.
                state['replay_frozen_identity']=frozen['identity']
                result=execute(frozen,crate,state['rust_config'],cfg,executor,compile_only=True)
                attempt['support_precompile']=result;state['support_pending_identity']=frozen['identity'];state['support_evidence']=result
                if result['status']=='support_compiled':
                    if frozen.get('source_check') and not state.get('source_oracle_revision_review'):
                        from .source_failure_review import require_revision
                        try:require_revision(frozen,state,cfg,state.get('source_oracle_revision_accepted'))
                        except Failure:
                            previous=state.get('source_oracle_revision_accepted',{}).get('revision')
                            if not previous:raise
                            state['source_oracle_revision_review']={**previous,'suite_identity':frozen['identity']}
                    state['phase']='support_check' if state.get('source_oracle_revision_review') else 'support_execute';state['feedback']=None
                else:
                    state['support_evidence']=result;state['feedback']=result;state['repair_return']=integration_phase(cfg);state['phase']='support_audit';state['support_return']='support'
                    state['failures'].append({'kind':'support','version':before,'status':'open','evidence':str(path/'attempt.json'),'frozen_identity':frozen['identity']})
                    repair_controller.register(state,'support',result,{'frozen_identity':frozen['identity']},integration_phase(cfg),state['failures'][-1])
            elif phase=='source_test_check':
                raise Failure('redundant_review_schedule','Failure-only policy forbids routine whole-suite semantic review')
            elif phase=='support_execute':
                from .source_failure_check import lock
                from .segmented_support import execute
                frozen=read(work/'support-tests'/(state['support_pending_identity']+'.json'))
                materialize(crate,{**state['files'],'src/lib.rs':state['files']['src/lib.rs']+probes(state['mapping'])},state['rust_config'])
                if frozen.get('source_check'):
                    from .source_failure_review import require_revision
                    require_revision(frozen,state,cfg,state.get('source_oracle_revision_accepted'))
                result=execute(frozen,crate,state['rust_config'],cfg,executor)
                from .support_issue_lineage import execution_proof,close as close_support_issues
                execution_proof(state,frozen,result);attempt['support']=result;state['support_evidence']=result
                if result['status']!='passed':
                    state['feedback']=result;state['repair_return']=integration_phase(cfg)
                    if result['status'] in {'support_test_compile_failed','support_test_binding_failed'}:state['phase']='support_audit'
                    elif result['status']=='support_contract_failed' and order_policy.source_first(state) and not state.get('source_candidate_lock'):state['phase']='support_check'
                    else:raise Failure('source_check_unresolved','Source suite did not fully execute/pass; missing or unknown test evidence is not waived',result)
                    state['failures'].append({'kind':'support','version':before,'status':'open','evidence':str(path/'attempt.json'),'frozen_identity':frozen['identity']})
                    state['support_return']='support'
                    repair_controller.register(state,'support',result,{'frozen_identity':frozen['identity']},integration_phase(cfg),state['failures'][-1])
                    if state.get('optimization_parent'):
                        revert_optimization(state,{'kind':'support_failure','evidence':result})
                else:
                    state['feedback']=None
                    for f in state['failures']:
                        if f['kind']=='support' and f['frozen_identity']==frozen['identity']:f.update(status='closed',verified_version=before)
                    close_support_issues(state,frozen,result,path/'attempt.json')
                    state['support_pass_candidate']=lock(state)
                    from .source_failure_review import require_state
                    require_state(state,cfg,work)
                    go_after_support(state,testing_project)
            elif phase in {'support_audit','support_check'}:
                from .segmented_test_audit import adjudicate
                pending=next(f for f in state['failures'] if f['kind']=='support' and f['status']=='open')
                frozen=read(work/'support-tests'/(pending['frozen_identity']+'.json'))
                if phase=='support_check':
                    from .source_failure_review import check
                    revision=state.get('source_oracle_revision_review')
                    result=check(frozen,revision['original_failure'] if revision else state['support_evidence'],state,cfg,provider,work/'source-failure-check',revision=revision)
                    attempt['source_test_check']=result;state['support_review_evidence']=result
                else:
                    result=adjudicate(frozen,{**state['support_evidence'],'challenge':state.pop('support_challenge',None)},state,cfg,provider,path/'audit')
                    attempt['support_audit']=result
                if result['action']=='accept_revision':
                    state['source_oracle_revision_accepted']={'revision':state.pop('source_oracle_revision_review'),'source_check':result['source_check']};state['support_pending_identity']=frozen['identity'];state['phase']='support_execute';state['feedback']=None
                elif result['action']=='binding_fix':
                    updated=result['frozen'];save(work/'support-tests'/(updated['identity']+'.json'),updated)
                    state['replay_frozen_identity']=updated['identity']
                    from .support_issue_lineage import migrate as migrate_support_issues
                    migrate_support_issues(state,frozen,updated,result['evidence'])
                    for f in state['failures']:
                        if f['kind']=='support' and f['status']=='open' and f['frozen_identity']==frozen['identity']:
                            f.setdefault('original_frozen_identity',frozen['identity'])
                            f.setdefault('binding_revisions',[]).append({'from':frozen['identity'],'to':updated['identity'],'audit':result['evidence']})
                            f['frozen_identity']=updated['identity']
                    if result.get('revision_review'):state['source_oracle_revision_review']=result['revision_review']
                    elif state.get('source_oracle_revision_review'):state['source_oracle_revision_review']['suite_identity']=updated['identity']
                    state['phase']='support';state['feedback']=None
                elif result['action'] in {'candidate_repair','algorithm_issue'} and order_policy.source_first(state) and not state.get('source_candidate_lock'):
                    state['phase']='repair';state['feedback']={'source_check':result,'failure':state['support_evidence']}
                else:
                    raise Failure('source_candidate_locked','Source-stage API or test issue cannot repair the locked candidate',result)
            elif phase=='connect':
                if order_policy.source_first(state):
                    from .source_failure_review import require_state
                    require_state(state,cfg,work)
                materialize(crate,{**state['files'],'src/lib.rs':state['files']['src/lib.rs']+probes(state['mapping'])},state['rust_config'])
                plan={'dependencies':state['rust_config']['dependencies'],'rust_config':state['rust_config']}
                from .observation_source import acquire as observation_acquire, ownership_for
                observation_material=observation_acquire(testing_project,state['bundle']['source_model'],cfg,work/'observation-source',executor,ownership=ownership_for(state['bundle']['source_model'],state['partition']))
                state['observation_ownership_identity']=tc.fingerprint(observation_material['candidate_ownership']) if observation_material else None
                conn,notes=test_connector.connect(testing_project,crate,state['files'],state['mapping'],plan,cfg,provider,path/'connector',
                    state['connector'],state.get('connector_feedback'),context_directory=work/'connector-context',observation_material=observation_material)
                state['connector']=conn;state['connector_notes']=notes;state['phase']='test';state['connector_identity']=connector_identity(state)
                if repair_controller.active(state) and repair_controller.active(state)['kind']=='behavior':state['phase']='repair_replay'
            elif phase=='test':
                if order_policy.source_first(state):
                    from .source_failure_review import require_state
                    require_state(state,cfg,work)
                materialize(crate,{**state['files'],'src/lib.rs':state['files']['src/lib.rs']+probes(state['mapping'])},state['rust_config'])
                harness=connection(crate,state['connector'],state['rust_config'],cfg)
                compiled=compile_crate(harness,state['rust_config'],cfg,executor,False);attempt['compilation']=compiled
                if compiled['status']!='passed':
                    state['connector_feedback']=compiled;state['phase']='connect'
                    state['connector_failures']=state.get('connector_failures',0)+1
                    if state['connector_failures']>=cfg['translation']['connector_stall_limit']:raise Failure('connector_stalled','Connector repeatedly failed actual compilation',compiled)
                else:
                    state['binary']=compiled['binary'];state['harness']=str(harness)
                    history=read(regressions) if Path(regressions).exists() else []
                    specs=[('fixed',fixed_inputs),('regression',[r['input'] for r in history if in_numeric_domain(r['input'],input_bits(cfg))]),('generated_differential',random_inputs)]
                    suites=[]
                    for name,inputs in specs:
                        if not inputs:continue
                        for prefix,args in [('',()),('kernel_',('--i2r-kernel-check' if cfg['translation'].get('correctness_only') else '--i2r-benchmark',))]:
                            suite=check_suite(bundle['case'],inputs,compiled['binary'],refs,executor,cfg['testing']['process_timeout'],prefix+name,arguments=args)
                            suite['reproducer']={'inputs':deepcopy(inputs),'arguments':list(args),'timeout':cfg['testing']['process_timeout'],'kind':prefix+name}
                            suites.append(suite);add_regressions(regressions,suite['counterexamples'])
                    failed=next((s for s in suites if s['status'] not in {'passed','differential_unavailable'}),None)
                    state['differential_suites']=deepcopy(suites)
                    attempt['development']={'status':failed['status'] if failed else 'passed','suites':suites}
                    if failed:
                        state['feedback']=attempt['development'];state['phase']='repair';state['repair_return']=integration_phase(cfg)
                        state['failures'].append({'kind':'behavior','version':before,'status':'open','evidence':str(path/'attempt.json'),'failure':failed})
                        state.pop('behavior_version',None)
                        repair_controller.register(state,'behavior',failed,failed['reproducer'],integration_phase(cfg),state['failures'][-1])
                        if state.get('optimization_parent'):revert_optimization(state,{'kind':'behavior_failure','evidence':failed})
                    else:
                        state['connector_failures']=0
                        expected_suites=[prefix+name for name,inputs in specs if inputs for prefix in ('','kernel_')]
                        repair_controller.close_redirected_connector(state,before,compiled,suites,expected_suites,str(path/'attempt.json'))
                        state['behavior_version']=tc.fingerprint([before,state['connector']]);state['connector_feedback']=None;state['feedback']=None
                        for issue in state['repair_issues']:
                            if issue['status']=='open' and issue['kind']=='behavior':
                                rep=issue['reproducer']
                                if any(s.get('reproducer')==rep and s['status']=='passed' for s in suites):issue['status']='verified_passed'
                        for f in state['failures']:
                            if f['kind']=='behavior' and all(s['status']=='passed' for s in suites):f.update(status='closed',verified_version=before)
                        state['phase']='finish' if order_policy.source_first(state) else 'support'
            elif phase=='performance':
                inputs=performance_search.workloads(bundle['case'],cfg)
                state['performance_inputs']=inputs
                parent=state.get('optimization_parent')
                measured=performance_search.measure(state,cfg,executor,refs,inputs,path/'development-performance',parent)
                if parent:
                    comparison=performance_search.compare(measured,cfg)
                    state['optimization_attempts'][-1].update(comparison=comparison,measurements=str(path/'development-performance'))
                    if not comparison['accept']:
                        revert_optimization(state,comparison)
                        continue
                    state['optimization_attempts'][-1]['status']='accepted'
                    state.pop('optimization_parent');state['optimization_no_gain']=0
                hot=performance_search.profile(state,cfg,executor,refs,inputs,path/'hotspots')
                state['development_performance']={'version':before,'measurements':measured,'profile':hot,
                    'boundary_measurements':performance_search.boundaries(state,cfg,executor,refs,inputs,path/'boundaries'),
                    'scope':'Development only; paired acceptance uses uninstrumented release. Source refinement disabled.'}
                state['phase']='performance_review' if cfg['translation']['performance_refinement'] else 'finish'
            elif phase=='repair_replay':
                issue=repair_controller.active(state)
                if issue is None:raise Failure('missing_repair_issue','Cannot replay an unbound repair')
                materialize(crate,{**state['files'],'src/lib.rs':state['files']['src/lib.rs']+probes(state['mapping'])},state['rust_config'])
                if issue['kind']=='support':
                    state['replay_frozen_identity']=issue['reproducer']['frozen_identity'];state['phase']='support';continue
                elif issue['kind']=='behavior':
                    harness=connection(crate,state['connector'],state['rust_config'],cfg)
                    state['harness']=str(harness)
                    built=compile_crate(harness,state['rust_config'],cfg,executor,False)
                    if built['status']=='passed':
                        state['binary']=built['binary'];rep=issue['reproducer']
                        replay=check_suite(bundle['case'],rep['inputs'],built['binary'],refs,executor,rep['timeout'],'original_reproducer',arguments=tuple(rep['arguments']))
                    else:replay=built
                else:
                    try:
                        coverage(bundle,state['files'],state['mapping'],issue['reproducer']['roots'],state['partition'],issue['reproducer'].get('final_coverage',False))
                        replay=compile_crate(crate,state['rust_config'],cfg,executor)
                    except Failure as error:replay={'status':error.code,'message':str(error),'evidence':error.evidence}
                attempt['original_replay']=replay
                save(path/'original-replay.json',replay)
                if repair_controller.replay_result(state,replay,cfg,verified_version=before,evidence=str(path/'original-replay.json')):
                    resume_after_replay(state,cfg,issue)
                else:
                    state['feedback']={'original_issue':issue['id'],'latest_replay':replay};state['phase']='repair'
            elif phase=='repair_diagnose':
                attempt['diagnostic']=repair_controller.diagnostic(state,cfg,executor,path/'diagnostic')
                state['phase']='repair';state['feedback']={'diagnostic':attempt['diagnostic'],'instruction':'Compare failed hypotheses; new evidence or a revised explanation is required.'}
            elif phase=='finish':
                from .source_failure_review import require_state,refresh_changed_revision
                if refresh_changed_revision(state,cfg,provider,work):continue
                require_state(state,cfg,work)
                if order_policy.source_first(state) and (not state.get('differential_suites') or any(s['status']!='passed' for s in state['differential_suites'])):raise Failure('source_check_unresolved','A requires all available differential suites to pass')
                if cfg['segmented'].get('support_tests',True) and state.get('support_evidence',{}).get('status')!='passed':raise Failure('source_check_unresolved','Full source suite must pass before finish')
                if any(i['status']=='open' for i in state['repair_issues']):raise Failure('unresolved_issue','A translation original reproducer is still unresolved',state['repair_issues'])
                if any(f['status']=='open' for f in state['failures']):raise Failure('unresolved_issue','Original issues remain open',state['failures'])
                if testing_project and state.get('behavior_version')!=tc.fingerprint([before,state['connector']]):raise Failure('unresolved_issue','Behavior evidence is stale')
                state['status']='passed'
            else:
                if phase=='repair' and repair_controller.needs_diagnostics(state,cfg):
                    state['phase']='repair_diagnose';continue
                if phase=='performance_review' and state['optimization_no_gain']>=cfg['translation']['optimization_no_gain_limit']:
                    state['optimization_stop']='Repeated measured non-improvement; retain verified incumbent';state['phase']='finish';continue
                request,page_map=payload(state,cfg,work)
                if phase=='repair' and repair_controller.active(state) and repair_controller.active(state)['kind']=='behavior':
                    from .behavior_material import augment
                    request=augment(request,state,cfg,testing_project,work,executor)
                request['diagnostic_policy']={'policy':state['test_order_policy'],'candidate_locked':bool(state.get('source_candidate_lock')),'instruction':'When locked, diagnose connector/harness defects only; use repair_connection for a specific wrong call/conversion, or needs_user for a real candidate mismatch. For that terminal mismatch supply diagnosis:{kind:"candidate_semantic",active_issue,failed_path,source_equations_used:[exact source equations],candidate_locations:[{file,symbol}],executed_evidence,why_connector_is_not_at_fault:[source-grounded reasons]}. Bind it to the current actual differential issue and source entry; it records rejection, not permission to repair. Candidate edits and rollback are forbidden.' if state.get('source_candidate_lock') else 'Use the established source verdict and unchanged tests to repair the candidate; do not change expectations.'}
                if phase=='refine':
                    scope_ids,_=review_required(state,phase,cfg)
                    review_scope.record_review(state,scope_ids,review_scope.view(state,scope_ids,cfg)[0],check_only=True)
                if phase in {'whole_review','performance_review'} and state['connector']:
                    request['connection_review']={'files':state['connector'],'notes':state.get('connector_notes'),
                        'scenarios':{n:(Path(testing_project)/n).read_text() for n in ['Model.thy','Kernel.thy']}}
                attempt['delivered_material']=material_progress.delivered(state,request)
                reply=ask(provider,cfg,path,request)
                if any(reply.get(k) for k in ['request_evidence_pages','request_pages','request_code_pages','request_entities','request_files','request_sources','request_references','request_materials','request_graphs']):
                    key=tc.fingerprint([before,phase,{k:reply[k] for k in ['request_evidence_pages','request_pages','request_code_pages','request_entities','request_files','request_sources','request_references','request_materials','request_graphs'] if k in reply}])
                    state.setdefault('read_requests',{})[key]=state.get('read_requests',{}).get(key,0)+1
                    if state['read_requests'][key]>=cfg['translation']['diagnostic_read_limit']:raise Failure('repair_stalled','Repeated identical material request without progress',reply)
                if any(str(n).endswith('isabelle-syntax.md') for n in reply.get('request_references',[])):
                    raise Failure('unsupported_reference','Historical printer guidance is excluded from translation')
                material={}
                if reply.get('request_evidence_pages'):
                    material.update(repair_controller.read_evidence(reply['request_evidence_pages'],request.get('repair_evidence_catalog',[]),state['bundle'],cfg))
                if reply.get('request_pages'):
                    material.update(read_pages(page_map,reply['request_pages'],cfg['segmented']['initial_source_characters']))
                if reply.get('request_code_pages'):
                    fetched=read_pages({p['id']:p for p in review_scope.view(state,review_required(state,state['phase'],cfg)[0],cfg)[1]},reply['request_code_pages'],cfg['segmented']['initial_code_characters'])
                    material.update(code_pages=fetched['pages'],pending_code_pages=fetched['pending_pages'])
                material.update(requested(reply,state['bundle'],state['files']))
                if material:
                    preserve_readings(state,reply,request,page_map)
                    state['extra']=material;attempt['development']={'status':'material_requested'};continue
                state['extra']={}
                action=reply.get('action','generate')
                if action in {'repair','patch','refine'} and any(k in reply for k in ['files','edits','mapping','rust_config','remove_files','strategy_updates']):
                    attempt['action_normalization']={'from':action,'to':'generate'};action='generate'
                if action=='rollback':
                    order_policy.guard_edit(state)
                    target=reply.get('transaction_before')
                    event=next((x for x in state['transactions'] if x['before']==target and 'rollback_to' not in x),None)
                    if not event:raise Failure('unknown_transaction','Choose a recorded before-version',target)
                    restored=read(Path(event['path'])/'transaction.json')['before']
                    strategy.restore_check(restored)
                    state.setdefault('strategy_archives',[]).append(deepcopy(strategy.current(state)))
                    old_version=version(state)
                    if not all(k in restored for k in ['completed','reviews','source_reviews','dirty_sources']):
                        raise Failure('rollback_evidence_missing','Legacy transaction has no bound review evidence; start a derived fresh run')
                    state.update(deepcopy(restored))
                    state.pop('behavior_version',None);state.pop('whole_review_version',None)
                    advance_unit(state,cfg)
                    state['transactions'].append({'before':old_version,'after':version(state),'rollback_to':target,'path':str(path)})
                    attempt['development']={'status':'transaction_rolled_back'};continue
                if action=='needs_user':
                    from .semantic_terminal import needs_user_failure
                    raise needs_user_failure(state,reply,before)
                if action=='challenge_support_test':
                    reject_source_challenge(state)
                if action=='request_diagnostics':
                    issue=repair_controller.active(state)
                    if issue and any(x.get('after_replay')==issue['unsuccessful_replays'] for x in issue['observations']):
                        raise Failure('duplicate_diagnostics','This exact failing state already has diagnostics; request specific source/code or revise the hypothesis')
                    state['extra']={'runtime':repair_controller.diagnostic(state,cfg,executor,path/'debug-replay')};continue
                if action=='repair_connection':
                    if not reply.get('connector_issue'):raise Failure('invalid_action','Explain exact connector defect')
                    repair_controller.redirect_connector(state,before,reply)
                    state['connector_feedback']={'issue':reply['connector_issue'],'original_failure':state.get('feedback')};state['phase']='connect';continue
                if phase=='performance_review':
                    analysis=reply.get('performance_analysis',{})
                    if analysis.get('classification') not in {'rust_expression','source_model','mixed','insufficient_evidence','no_actionable_rust_change'} or any(not analysis.get(k) for k in ['evidence','source_correspondence','reason','next_step']):
                        raise Failure('invalid_performance_analysis','Provide grounded performance_analysis and explicit uncertainty')
                    state.setdefault('performance_analyses',[]).append({'version':before,'analysis':analysis})
                    if action=='finish_optimization':
                        state['optimization_stop']=reply.get('reason',analysis['reason']);state['phase']='finish';continue
                    if action!='optimize' or analysis['classification'] not in {'rust_expression','mixed'}:
                        raise Failure('invalid_optimization_action','Optimize Rust expression only, or finish_optimization with a report')
                    hypothesis=reply.get('optimization_hypothesis',{})
                    if any(not hypothesis.get(k) for k in ['cause','evidence','change','prediction']):raise Failure('missing_optimization_hypothesis','Measured hypothesis required')
                    parent=performance_search.snapshot(state,path/'incumbent');parent['development_performance']=deepcopy(state['development_performance'])
                    proposed=apply_transaction(state,reply,cfg,path)
                    if any(a.get('proposed_version')==version(proposed) for a in state['optimization_attempts']):raise Failure('repeated_optimization','This candidate was already measured')
                    state=proposed;state['attempts']=attempts;state['optimization_parent']=parent
                    state['optimization_attempts'].append({'hypothesis':hypothesis,'parent_version':before,'proposed_version':version(state),'status':'validating','path':str(path)})
                    state['unit']=next_unit(state['partition'],state['completed'])
                    state['phase']=unit_check_phase(cfg) if state['unit'] else 'final_compile'
                    continue
                if action=='accept':
                    if phase not in {'refine','whole_review'}:raise Failure('invalid_action','Acceptance only during review')
                    validate_review(state,reply,page_map,cfg)
                    if phase=='refine':
                        scope_ids,_=review_required(state,phase,cfg)
                        review_scope.record_review(state,scope_ids,review_scope.view(state,scope_ids,cfg)[0])
                        if state['partition'].get('policy')=='semantic-components':
                            for n in component_scope.review_members(state):
                                state.setdefault('source_reviews',{})[n]={'version':before,'evidence':str(path/'reply.json')}
                    if phase=='refine':state['reviews'][state['unit']]={'version':before,'evidence':str(path/'reply.json')};state['phase']='compile'
                    elif phase=='whole_review':state['whole_review_version']=before;state['phase']='final_compile'
                    state['feedback']=None;attempt['development']={'status':'quality_reviewed'}
                elif action in {'generate','revise_plan'}:
                    if phase=='repair':repair_controller.proposal(state,reply)
                    state=apply_transaction(state,reply,cfg,path);state['attempts']=attempts
                    state['decisions']+=reply.get('decisions',[])
                    state['numeric_representation']=reply.get('numeric_representation',state.get('numeric_representation','unreported'))
                    if action=='revise_plan':advance_unit(state,cfg)
                    elif phase=='generate':state['phase']=unit_check_phase(cfg) if reply.get('unit_complete',True) else 'generate'
                    elif phase=='repair':state['phase']='repair_replay'
                    else:state['phase']=phase
                    # Earlier invalidated units must be re-reviewed before any final gate.
                    if state['phase']=='whole_review' and len(state['completed'])<len(state['partition']['units']):
                        state['unit']=next_unit(state['partition'],state['completed']);state['phase']='refine'
                    state['feedback']=None
                    count=state['seen_versions'].get(version(state),0)+1;state['seen_versions'][version(state)]=count
                    if count>=cfg['segmented']['no_progress_limit']:raise Failure('representation_cycle','Repeatedly returned to the same state despite prior diagnostics',state['transactions'])
                    if count>1:state['feedback']={'status':'representation_oscillation','message':'This exact implementation/config was previously attempted. Compare recorded failures; change the repair hypothesis.', 'transactions':state['transactions']}
                    attempt['development']={'status':'transaction_committed','invalidated':state['transactions'][-1]['invalidated']}
                else:raise Failure('invalid_action',action)
        except Failure as error:
            if state.get('source_candidate_lock') and phase in {'support_audit','support_check'}:
                state['feedback']={'status':error.code,'message':str(error),'evidence':error.evidence};raise
            if error.code=='context_budget_exceeded':
                if phase=='repair' and not state.get('extra'):
                    # Mandatory repair material cannot shrink by retrying unchanged.
                    state['feedback']=attempt['development']={'status':error.code,'message':str(error),'evidence':error.evidence}
                    raise
                state['extra']={}
            attempt['development']={'status':error.code,'message':str(error),'evidence':error.evidence}
            if phase in {'compile','final_compile'} and error.code in {'plan_contract_failed','invalid_mapping','missing_exports','ambiguous_rust_item'}:
                state['failures'].append({'kind':'contract','version':before,'status':'open','failure':deepcopy(attempt['development']),'evidence':str(path/'attempt.json')})
                repair_controller.register(state,'compile',attempt['development'],{'roots':roots,'library':True,'final_coverage':complete_coverage},unit_check_phase(cfg) if phase=='compile' else integration_phase(cfg),state['failures'][-1])
            if error.code in {'provider_error','provider_protocol_error','budget_exhausted','needs_user','candidate_semantic_rejected','stale_snapshot','representation_cycle',
                              'support_binding_stalled','source_suite_review_unresolved','redundant_review_schedule','support_context_exceeded','support_output_budget_exhausted','support_author_budget_exhausted','oracle_conflict','oracle_property_conflict','reference_runtime_failed','invalid_domain','support_oracle_dispute','source_check_unresolved','source_candidate_locked','repair_stalled','connector_stalled'}:
                state['feedback']=attempt['development'];raise
            if state.get('optimization_parent') and phase in {'compile','final_compile','support','test','performance'}:
                revert_optimization(state,{'error':error.code,'evidence':error.evidence});continue
            if phase=='connect':
                if error.code=='connector_algorithm_defect':
                    if state.get('source_candidate_lock'):raise
                    state['feedback']=attempt['development'];state['phase']='repair';state['repair_return']=integration_phase(cfg)
                    if repair_controller.active(state) is None:
                        roots=[n for u in state['partition']['units'].values() for n in u['members']]
                        repair_controller.register(state,'compile',attempt['development'],{'roots':roots,'library':True},integration_phase(cfg))
                else:
                    state['connector_feedback']=attempt['development'];state['connector_failures']=state.get('connector_failures',0)+1
                    if state['connector_failures']>=cfg['translation']['connector_stall_limit']:raise Failure('connector_stalled','Repeated connector failure',attempt['development'])
            else:
                state['feedback']=attempt['development']
                if phase in {'compile','final_compile'}:state['phase']='repair';state['repair_return']=unit_check_phase(cfg) if phase=='compile' else integration_phase(cfg)
        finally:
            attempt['finished_at']=now();attempt['after_version']=version(state)
            attempt['resources']={'seconds':time.monotonic()-phase_started,'model_calls':provider.calls-calls_before,'usage_before':usage_before,'usage_after':deepcopy(provider.usage)}
            attempt['progress']={'code_or_strategy_changed':before!=version(state),'phase_before':phase,'phase_after':state['phase'],'executed_compile':bool(attempt.get('compilation')),'executed_behavior':phase in {'test','support','repair_replay'}}
            status=attempt.get('development',{}).get('status')
            attempt['verified_progress']=material_progress.advance(state,progress_before,attempt)
            save(path/'attempt.json',attempt)
            # One atomic checkpoint is the authoritative code+metadata+state transaction.
            state['attempts']=attempts;state['strategy_digest']=tc.fingerprint(strategy.current(state));save(checkpoint,state)
            update({'attempts':attempts,'model_calls':provider.calls,'usage':provider.usage})
        if state['no_progress']>=cfg['segmented']['no_progress_limit']:
            raise Failure('segmented_no_progress','Unable to advance after focused repair attempts; original issue remains unresolved',state['feedback'])
    materialize(crate,{**state['files'],'src/lib.rs':state['files']['src/lib.rs']+probes(state['mapping'])},state['rust_config'])
    save(crate/'translation.json',{'mapping':state['mapping'],'decisions':state['decisions'],'partition':state['partition'],'reviews':state['reviews']})
    state.update(crate=str(crate),plan={'dependencies':state['rust_config']['dependencies'],'rust_config':state['rust_config']},
                 workflow_evidence={'repair_issues':state['repair_issues'],'optimization_attempts':state['optimization_attempts'],'performance_analyses':state.get('performance_analyses',[]),'development_performance':state.get('development_performance'),'optimization_stop':state.get('optimization_stop')},
                 quality_evidence={'enabled':quality_reviews_enabled(cfg),'units':state['reviews'],'whole_review_version':state.get('whole_review_version'),'support_contracts':state.get('support_evidence')})
    survivor=deepcopy(state);survivor['attempts']=[a['attempt'] for a in attempts]
    return attempts,[survivor]
