"""Knowledge-guided translation with analysis-only preparation and late test linking."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from .common import ROOT, Executor, Failure, digest, now, read, save
from .provider import Provider
from .preprocessing import preprocess
from .knowledge import analyze, material, requested, references as skill_references, call, adapter_plan, apply_files, correspondence, merge_mapping,validate_dependencies
from .adapters import load_adapter, materialize_support
from .planning import manifest
from .references import compile_rust, cargo
from . import test_connector, tool_sources
from .validation import check_suite, reference_outputs, add_regressions
from .suites import input_bits, scoped_fixed, scoped_inputs, scoped_performance_input, in_numeric_domain, fixed
from .performance import benchmark
from . import task_context as tc
from . import repair_state as repair


def failure(error):
    return {'status':error.code,'message':str(error),'evidence':error.evidence}


def reference_bundle(project,bundle):
    files={str(p.relative_to(project)):digest(p) for p in Path(project).rglob('*') if p.suffix in {'.thy','.ML'}}
    metadata=read(Path(project)/'case.json')
    for name in metadata.get('source_files',[]):files[name]=digest(name)
    return {'source_hashes':files,'tool_sources':bundle['tool_sources']}


def write_library(crate,files,plan,bundle):
    crate=Path(crate);crate.mkdir(parents=True,exist_ok=True)
    for name,code in files.items():
        path=crate/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(code)
    (crate/'Cargo.toml').write_text(manifest(plan.get('dependencies',{}),transport='none',build_dependencies=plan.get('build_dependencies')))
    save(crate/'migration-plan.json',plan)
    loaded=bundle.get('loaded_adapter')
    if loaded and loaded.get('theory'):
        from .storage import attach_adapter
        attach_adapter(crate,loaded,bundle.get('original_programs',bundle['programs']))


def synchronize_support(branch):
    """Ordinary support edits are versioned alongside actual declarations."""
    loaded=branch['bundle'].get('loaded_adapter')
    if not loaded:return
    support=loaded['support']
    for name in list(support['files']):
        if name in branch['files']:
            support['files'][name]=branch['files'][name]
            if name in branch['plan']['adapter']['rust_files']:
                branch['plan']['adapter']['rust_files'][name]=branch['files'][name]


def compile_library(crate,cfg,executor):
    from .storage import cargo_cache
    with cargo_cache(executor,cfg) as target:
        executor.run(cargo(cfg,'clean','--release','--package','i2r_candidate','--manifest-path',Path(crate)/'Cargo.toml','--target-dir',target),timeout=cfg['budgets']['build_seconds'])
        checked=executor.run(cargo(cfg,'build','--lib','--release','--manifest-path',Path(crate)/'Cargo.toml','--target-dir',target),timeout=cfg['budgets']['build_seconds'],check=False)
    return {'status':'passed' if checked['status']=='passed' else 'compile_failed','checks':{'build':checked}}


def verify_support_issue(branch,crate,cfg,executor,path):
    """An independent regression supplied with the issue is never edited by the candidate."""
    issue=branch['repair_issue'];source=issue['evidence'].get('test_source')
    if not source:
        return {'status':'missing_verification','message':'Support issue needs an independent source-grounded test_source; unrelated behavior checks cannot close it.'}
    target=Path(path)/'support-verification';(target/'tests').mkdir(parents=True,exist_ok=True)
    (target/'tests/issue.rs').write_text(source)
    text=manifest(branch['plan'].get('dependencies',{}),package='i2r_support_verification',transport='none')
    text+='i2r_candidate = { path = '+json.dumps(str(Path(crate).resolve()))+' }\n'
    (target/'Cargo.toml').write_text(text)
    checked=executor.run(cargo(cfg,'test','--manifest-path',target/'Cargo.toml','--test','issue'),timeout=cfg['budgets']['build_seconds'],check=False)
    import re
    diagnostic=Path(checked['stdout']).read_text()+Path(checked['stderr']).read_text()
    ran_tests=any(int(n)>0 for n in re.findall(r'test result: ok\. (\d+) passed',diagnostic))
    return {'status':'passed' if checked['status']=='passed' and ran_tests else 'support_contract_failed',
        'test_sha256':digest(target/'tests/issue.rs'),'code_version':tc.fingerprint(branch['files']),
        'diagnostic':Path(checked['stdout']).read_text()+Path(checked['stderr']).read_text(),'record':checked}


def search(bundle,testing_project,cfg,provider,work,executor,refs,fixed_inputs,random_inputs,regressions,update):
    from .pipeline import feedback_for
    base=deepcopy(bundle);managed=tc.enabled(cfg)
    def branch(strategy):
        return {'id':'candidate-'+str(len(branches)+1),'strategy':strategy,'bundle':deepcopy(base),
            'files':deepcopy(base.get('base_adapter',{}).get('support',{}).get('files',{})),
            'mapping':[],'plan':{'dependencies':{},'adapter':{'rust_files':{},'rust_root':''}},
            'extra':deepcopy(base.get('knowledge_material',{})) if managed else {},'pending_material':{},'decisions':[],'repair_history':[],'feedback':None,'mode':'generate','connector':{},'connector_feedback':None,
            'status':'active','seen':{},'attempts':[],'alternatives':[]}
    branches=[];branches.append(branch('Main recommended source-grounded implementation.'))
    attempts=[];survivors=[]
    checkpoint=Path(work)/'generation-checkpoint.json'
    if checkpoint.exists():
        saved=read(checkpoint);branches=saved['branches'];attempts=saved['attempts']
        survivors=[deepcopy(b) for b in branches if b['status']=='passed']
    for b in branches:
        while b['status']=='active' and provider.phase_calls['generation']<cfg['repair']['max_attempts']:
            number=len(attempts)+1;path=Path(work)/f'candidate-{number:02d}';path.mkdir(exist_ok=True)
            attempt={'attempt':number,'ownership_candidate':b['id'],'started_at':now(),'action_phase':b['mode']}
            attempts.append(attempt);b['attempts'].append(number)
            before_files=deepcopy(b['files']);before_adapter=repair.adapter_snapshot(b);reply=None
            if managed:repair.capture(b)
            before_issue=(b.get('repair_issue') or {}).get('id')
            update({'phase':'testing' if b['mode']=='connect' else 'generation' if not b['files'] else 'repair',
                    'attempts':attempts,'ownership_candidates':[{'plan':{'id':x['id'],'strategy':x['strategy']},'status':x['status'],'attempts':x['attempts']} for x in branches]})
            try:
                if b['mode']=='connect':
                    if testing_project is None:
                        if managed:repair.ensure_acceptible(b)
                        b['status']='passed';survivors.append({**b,'crate':b['crate'],'binary':None});break
                    if managed and b['connector'] and not b['connector_feedback']:
                        connector,notes=b['connector'],b.get('connector_notes','')
                    else:
                        connector,notes=test_connector.connect(testing_project,b['crate'],b['files'],b['mapping'],b['plan'],cfg,provider,path/'connection',b['connector'],b['connector_feedback'],
                            context_directory=Path(work)/'context'/(b['id']+'-connector') if managed else None,
                            original_issue=repair.feedback(b) if managed and b.get('repair_issue') else None)
                    if b.get('connector_feedback') and connector==b['connector']:
                        b['connector_feedback']['unchanged_repair']={'actual_file_changes':0,'last_claim':notes,
                            'instruction':'Return an actual exact edit for the faulty connector or algorithm_issue for an algorithm defect; unchanged files cannot repair the recorded failure.'}
                        attempt['development']={'status':'unchanged_connector','message':'No connector file changes despite unresolved failure; original diagnostics retained.'};continue
                    b['connector']=connector;b['connector_notes']=notes
                    crate=path/'algorithm';write_library(crate,b['files'],b['plan'],b['bundle']);save(crate/'translation.json',{'mapping':b['mapping'],'notes':b.get('notes','')})
                    harness=test_connector.materialize(crate,connector,b['plan'],cfg)
                    compiled=compile_rust(harness,cfg,executor,candidate=True);attempt.update(crate=str(crate),compilation=compiled)
                    tests=[]
                    if managed and compiled['status']=='passed':repair.verified(b,'compile',tc.fingerprint({'files':b['files'],'connector':connector}))
                    if managed and compiled['status']=='passed' and (b.get('repair_issue') or {}).get('kind')=='support':
                        support_check=verify_support_issue(b,crate,cfg,executor,path)
                        attempt['support_verification']=support_check
                        if support_check['status']!='passed':
                            b['feedback']={**repair.feedback(b),'verification_failure':support_check};b['mode']='generate'
                            attempt['development']={'status':'support_contract_failed','support_verification':support_check}
                            continue
                        repair.verified(b,'support',tc.fingerprint(b['files']))
                    if compiled['status']=='passed':
                        history=read(regressions) if Path(regressions).exists() else []
                        regression=[x['input'] for x in history if in_numeric_domain(x['input'],input_bits(cfg))]
                        specs=[('fixed',fixed_inputs),('regression',regression),('generated_differential',random_inputs)]
                        if managed and repair.reproducer_inputs(b):specs.insert(0,('repair_reproducer',repair.reproducer_inputs(b)))
                        for name,inputs in specs:
                            if not inputs or not cfg['testing'].get({'generated_differential':'differential'}.get(name,name),True):continue
                            for suffix,args in [('',()),('kernel_',('--i2r-kernel-check' if cfg.get('v8',{}).get('correctness_only') else '--i2r-benchmark',))]:
                                suite=check_suite(b['bundle']['case'],inputs,compiled['binary'],refs,executor,cfg['testing']['process_timeout'],suffix+name,arguments=args)
                                tests.append(suite);add_regressions(regressions,suite['counterexamples'])
                    status=compiled['status'] if compiled['status']!='passed' else next((t['status'] for t in tests if t['status']!='passed'),'passed')
                    result={'status':status,'count':sum(t['count'] for t in tests),'compilation':compiled,'suites':tests,
                            'failures':sum(t['failures'] or 0 for t in tests),'behavior_checked':bool(tests)}
                    attempt['development']=result
                    if status=='passed':
                        if managed and tests:repair.verified(b,'behavior',tc.fingerprint(b['files']))
                        b['crate']=str(crate);b['binary']=compiled['binary']
                        if managed:
                            b['mode']='review';b['behavior_validated']=tc.fingerprint(b['files']);b['feedback']=None;b['connector_feedback']=None
                        else:
                            b['status']='passed';survivors.append(deepcopy(b))
                        save(crate/'connector-boundary.json',{'wire':cfg['testing']['transport'],'notes':notes,'algorithm_read_only_during_connection':True,
                            'limitation':'LLM-authored bridge checked by compiler and composed differential tests, not a separate equivalence proof. Timing placement requires review.'})
                    elif compiled['status']!='passed':
                        b['connector_feedback']=feedback_for(result)
                    else:
                        b['feedback']={'behavior_failure':feedback_for(result),'test_connection':connector,
                            'test_scenarios':{name:(Path(testing_project)/name).read_text() for name in ['Model.thy','Kernel.thy']},
                            'instruction':'Diagnose the failed call against source equations. Repair the algorithm, or use action repair_connection with a concrete connector defect. Do not change the algorithm API merely to fit the test ABI.'}
                        b['mode']='generate'
                else:
                    current=material(b['bundle'],b['extra'])
                    current['support']={'root':current.get('support',{}).get('root',''),
                        'file_names':list(current.get('support',{}).get('files',{})),
                        'body_location':'Actual support bodies are supplied once in current_files.'}
                    adapter_context=deepcopy(b['plan'])
                    support_names=list(adapter_context.get('adapter',{}).pop('rust_files',{}))
                    adapter_context['support_file_names']=support_names
                    adapter_context['support_body_location']='current_files'
                    installed=bool(b['bundle'].get('loaded_adapter'))
                    task=('Inspect current compiled code. Return accept if no concrete changes are needed.' if b['mode']=='review'
                          else 'Diagnose the failing composed test call. For an algorithm defect return generate/adapt; for a connector defect return repair_connection with connector_issue. Do not re-emit unchanged code without routing the defect.' if (b.get('feedback') or {}).get('behavior_failure')
                          else 'The setup is already loaded successfully. Now return action generate with the Rust library. Use adapt only to CHANGE a declaration/support choice; do not resubmit the installed setup.' if installed
                          else 'Install your concrete program setup with action adapt. Its successful result will be followed by a separate Rust generation step.')
                    payload={'task':task,'controller_state':{'phase':b['mode'],'setup_installed':installed,'last_attempt_status':attempts[-2].get('development',{}).get('status') if len(attempts)>1 else None},
                        'program':current,'strategy':b['strategy'],'current_files':b['files'],'current_mapping':b['mapping'],
                        'current_adapter':adapter_context,'feedback':b['feedback'],
                        'available_actions':['adapt','generate','accept (review only)','repair_connection (test bridge defect)','request_nodes','request_sources','request_references']}
                    if not b['bundle'].get('loaded_adapter') or (b.get('feedback') or {}).get('status','').startswith('adapter'):
                        payload['declaration_reference']=skill_references(['semantic-adaptation/references/isabelle-syntax.md'])
                    if managed:
                        payload=tc.prepare_generation(b,payload,cfg,work)
                        if b['mode']=='review' and b.get('connector'):
                            payload['connection_review']={'files':b['connector'],'notes':b.get('connector_notes'),'scenarios':{name:(Path(testing_project)/name).read_text() for name in ['Model.thy','Kernel.thy']},
                                'instruction':'Audit source calls, callbacks and numeric operations, preparation/run/encoding boundaries. For a concrete connector defect return repair_connection. Runtime measurements are not supplied.'}
                    reply=call(provider,cfg,path,'generation',payload)
                    if managed:b['pending_material']={}
                    additions=requested(reply,b['bundle'],b['files'])
                    if additions:
                        b['extra']=tc.merge_material(b['extra'],additions) if managed else additions
                        if managed:b['pending_material']=additions
                        attempt['development']={'status':'material_requested'};continue
                    if managed and reply.get('action')=='revise_analysis':
                        revised=reply.get('analysis')
                        if not isinstance(revised,dict) or not isinstance(revised.get('opportunities'),list):
                            raise Failure('invalid_analysis','Revised analysis needs opportunities and a source-grounded reason')
                        if not reply.get('reason'):raise Failure('invalid_analysis','Explain the evidence requiring revision')
                        save(path/'analysis-revision.json',{'before':b['bundle'].get('semantic_analysis'),'after':revised,'reason':reply['reason']})
                        b['bundle']['semantic_analysis']=revised
                        attempt['development']={'status':'analysis_revised'};continue
                    if managed:tc.update_decisions(b,reply)
                    if any(k in reply for k in ['mapping_changes','mapping_additions','mapping_updates']):
                        raise Failure('invalid_mapping_field','Use the exact field mapping: [{source: "source ID", rust: "actual realization"}]. These records merge with existing mapping. No Rust or Isabelle edit is needed for a mapping-only omission.')
                    action=reply.get('action','generate');attempt['action']=action
                    if action=='repair_connection':
                        if managed and (b.get('repair_issue') or {}).get('kind')=='support':
                            raise Failure('invalid_candidate','This independent support test never calls the connector. Repair the tested support function; the original test and source evidence remain authoritative.')
                        if not b.get('connector') or not reply.get('connector_issue'):
                            raise Failure('invalid_candidate','repair_connection needs an existing connector and a concrete connector_issue')
                        b['connector_feedback']={'diagnosis':reply['connector_issue'],'failure':b['feedback']};b['mode']='connect'
                        attempt['development']={'status':'connection_repair_requested'};continue
                    if reply.get('alternatives') and b['id']=='candidate-1':
                        b['alternatives']=[x for x in reply['alternatives'] if x.get('strategy') and x.get('rationale')][:2]
                    if action=='adapt':
                        if managed:reply=repair.adapter_reply(b,reply)
                        plan=adapter_plan(reply,b['bundle']);old_nodes=set(n['id'] for p in b['bundle']['programs'] for n in p['nodes'])
                        if installed and all(plan.get(k)==b['plan'].get(k) for k in ['adapter','dependencies','build_dependencies']):
                            raise Failure('adapter_already_loaded','These exact declarations and support are already loaded successfully. Return action generate with src/lib.rs; no further setup action is needed.')
                        b['pending_adapter']=deepcopy(reply)
                        save(path/'adapter-plan.json',plan)
                        adapter_key=tc.fingerprint({k:plan[k] for k in ['adapter','dependencies','build_dependencies']})
                        if managed and adapter_key in b.get('adapter_failures',{}):
                            cached=b['adapter_failures'][adapter_key]
                            raise Failure('repeated_adapter','These exact declarations/support already failed. Return adapter_edits or read the relevant signature; the original diagnostic is retained.',cached)
                        try:loaded=load_adapter(plan,b['bundle'],cfg,path/'adapter',executor,check_support=False)
                        except Failure as error:
                            if managed and error.code.startswith('adapter'):
                                b.setdefault('adapter_failures',{})[adapter_key]=failure(error)
                            raise
                        if managed:repair.verified(b,'declaration',adapter_key)
                        b.pop('pending_adapter',None)
                        b['plan']=plan;b['bundle']={**b['bundle'],'loaded_adapter':loaded,'programs':[loaded['after_target']]}
                        if loaded.get('source_model'):
                            b['bundle']['source_model']=loaded['source_model']
                        b['files'].update(loaded['support']['files']);b['mode']='generate';b['feedback']=None
                        graph_material={'graph_change':{'removed':sorted(old_nodes-set(n['id'] for n in loaded['after_target']['nodes'])),
                            'new_symbols':[n['id'] for n in loaded['after_target']['nodes'] if n['id'] not in old_nodes]},
                            'adapter_audit':loaded['audit']}
                        b['extra']=tc.merge_material(b['extra'],graph_material) if managed else graph_material
                        if managed:
                            b['pending_material']=graph_material;b.pop('behavior_validated',None)
                            for decision in b.get('decisions',[]):decision['review_required']=True
                        attempt['development']={'status':'adapter_loaded'};continue
                    if action=='accept':
                        if managed:
                            from .code_quality import validate_review
                            validate_review(b['files'],reply)
                            repair.review_resolution(b,reply)
                            repair.ensure_acceptible(b)
                        if b['mode']!='review' or not b.get('crate'):raise Failure('invalid_candidate','Accept is available only after a compiled library and static review')
                        if managed and b.get('behavior_validated')==tc.fingerprint(b['files']):
                            b['status']='passed';survivors.append(deepcopy(b))
                        else:b['mode']='connect'
                        b['connector_feedback']=None;b['feedback']=None
                        attempt['development']={'status':'quality_reviewed','review':reply.get('quality_review','')};continue
                    if action!='generate':raise Failure('invalid_candidate','Unknown action: '+action)
                    reviewing=b['mode']=='review';old_files=deepcopy(b['files']);old_plan=deepcopy(b['plan']);old_mapping=deepcopy(b['mapping'])
                    if managed and reply.get('edits') and not reply.get('base_code_version'):
                        raise Failure('missing_patch_version','Return base_code_version from the current request with exact edits')
                    next_files=apply_files(b['files'],reply,path/'file-normalizations.json')
                    next_dependencies=reply.get('dependencies',b['plan']['dependencies'])
                    validate_dependencies(next_dependencies,b['plan'].get('build_dependencies'))
                    for module in b['bundle'].get('loaded_adapter',{}).get('bindings',{}).get('support_modules',[]):
                        name='src/'+module['module']+'.rs'
                        if name in next_files and next_files[name]!=module['code']:
                            raise Failure('binding_sync_required','Change embedded code_module through action adapt',name)
                    b['files']=next_files
                    if 'src/lib.rs' not in b['files']:raise Failure('invalid_candidate','Return complete src/lib.rs')
                    if not b['bundle'].get('loaded_adapter'):
                        b['mapping']=merge_mapping(b['mapping'],reply.get('mapping'))
                        raise Failure('adapter_not_installed','Submit action adapt with the real Isabelle mappings used by this draft. If no new mappings are needed, submit an empty declaration body to record that choice. Draft code is retained.')
                    loaded=b['bundle'].get('loaded_adapter',{})
                    for module in loaded.get('bindings',{}).get('support_modules',[]):
                        name='src/'+module['module']+'.rs'
                        if name in b['files'] and b['files'][name]!=module['code']:
                            raise Failure('binding_sync_required','Change embedded code_module through action adapt',name)
                    b['mapping']=merge_mapping(b['mapping'],reply.get('mapping'));b['notes']=reply.get('notes','')
                    b['numeric_representation']=reply.get('numeric_representation',b.get('numeric_representation',b['plan'].get('adaptation',{}).get('numeric','unreported')))
                    if reply.get('dependencies') is not None:b['plan']['dependencies']=reply['dependencies']
                    validate_dependencies(b['plan']['dependencies'],b['plan'].get('build_dependencies'))
                    synchronize_support(b)
                    attempt['plan_contract']=correspondence(b['bundle'],b['files'],b['mapping'])
                    if not reviewing and b.get('feedback') and repair.executable_text(b['files'])==repair.executable_text(old_files) and all(b['plan'].get(k)==old_plan.get(k) for k in ['dependencies','build_dependencies']) and b['mapping']==old_mapping:
                        b['feedback']['unchanged_repair']={'actual_file_changes':0,'last_claim':reply.get('notes',''),
                            'instruction':'Your response did not change any file or dependency. The diagnosed fault remains. Return concrete edits [{file,old,new}] with exactly matching source text, or action repair_connection for a specifically identified bridge defect. Do not describe a fix without applying it.'}
                        attempt['development']={'status':'unchanged_repair','message':'No file changes despite outstanding failure; original diagnostics retained.'};continue
                    if reviewing and b['files']==old_files and b['plan']==old_plan:
                        if managed:
                            from .code_quality import validate_review
                            validate_review(b['files'],reply)
                            repair.review_resolution(b,reply)
                            repair.ensure_acceptible(b)
                        if managed and b.get('behavior_validated')==tc.fingerprint(b['files']):
                            b['status']='passed';survivors.append(deepcopy(b))
                        else:b['mode']='connect'
                        b['feedback']=None;b['connector_feedback']=None
                        attempt['development']={'status':'quality_reviewed','review':reply.get('quality_review',reply.get('notes','')),
                            'normalization':'unchanged generation during review accepted as no-change review'};continue
                    crate=path/'algorithm';write_library(crate,b['files'],b['plan'],b['bundle'])
                    save(crate/'translation.json',{'mapping':b['mapping'],'notes':b['notes'],'quality_review':reply.get('quality_review','')})
                    attempt['crate']=str(crate)
                    compiled=compile_library(crate,cfg,executor);attempt['compilation']=compiled
                    attempt['development']={'status':compiled['status'],'compilation':compiled,'suites':[]}
                    if compiled['status']=='passed':
                        if managed:repair.verified(b,'compile',tc.fingerprint(b['files']))
                        b['crate']=str(crate);b['mode']='connect' if managed and testing_project is not None else 'review';b['feedback']=None
                        if managed:b.pop('behavior_validated',None)
                        # A changed public interface needs a fresh/repaired connector.
                        if b['files']!=old_files:b['connector_feedback']=None
                    else:b['feedback']=feedback_for(attempt['development']);b['mode']='generate'
            except Failure as error:
                attempt['development']=failure(error)
                if error.code in {'provider_error','budget_exhausted','context_budget_exceeded','reference_runtime_failed','oracle_conflict','oracle_property_conflict','material_changed'}:raise
                if error.code in {'connector_algorithm_interface','connector_algorithm_defect'}:
                    b['feedback']={'algorithm_issue':str(error),'connection_feedback':b['connector_feedback']};b['mode']='generate'
                elif b['mode']=='connect':b['connector_feedback']=failure(error)
                else:
                    b['feedback']=failure(error)
                    if b.get('pending_adapter'):b['feedback']['attempted_adapter']=b['pending_adapter']
                    if not (b['mode']=='review' and error.code in {'invalid_model_response','incomplete_response','incomplete_quality_review','unresolved_issue'}):b['mode']='generate'
            finally:
                attempt['finished_at']=now()
                import re
                diagnostic=str(attempt.get('development',{}).get('message',''))
                diagnostic=re.sub(r'candidate-\d+', 'candidate-N',diagnostic)
                diagnostic=re.sub(r'0:\d+:\d+ elapsed time','ELAPSED',diagnostic)
                key=hashlib.sha256(json.dumps({'files':b['files'],'mapping':b['mapping'],'connector':b['connector'],
                    'adapter':b.get('pending_adapter'),'status':attempt.get('development',{}).get('status'),
                    'message':diagnostic},sort_keys=True).encode()).hexdigest()
                status=attempt.get('development',{}).get('status')
                if status not in {None,'passed','adapter_loaded','material_requested','quality_reviewed'}:
                    b['seen'][key]=b['seen'].get(key,0)+1
                    attempt['same_failure_count']=b['seen'][key]
                    if b['seen'][key]>1:
                        target='connector_feedback' if b['mode']=='connect' else 'feedback'
                        if not isinstance(b.get(target),dict):b[target]={}
                        b[target]['repeated_failure']={'count':b['seen'][key],
                            'instruction':'The actual files and error repeated. Use a focused exact edit or request the relevant source equations; do not repeat an unchanged implementation. Remaining calls stay available within the shared budget.'}
                if managed:
                    repair.capture(b)
                    tc.record_attempt(b,attempt,before_files,reply,path,before_adapter=before_adapter,before_issue=before_issue)
                    if b['status']=='passed':
                        survivors=[deepcopy(b) if s['id']==b['id'] else s for s in survivors]
                save(path/'attempt.json',attempt)
                save(Path(work)/'generation-checkpoint.json',{'branches':branches,'attempts':attempts,'model_calls':provider.calls})
                update({'attempts':attempts,'usage':provider.usage,'model_calls':provider.calls,
                    'ownership_candidates':[{'plan':{'id':x['id'],'strategy':x['strategy']},'status':x['status'],'attempts':x['attempts']} for x in branches]})
        if b['status']=='active':b['status']='budget_exhausted'
        if b['id']=='candidate-1' and not b.get('alternatives_scheduled'):
            for alt in b['alternatives'][:max(0,min(3,cfg['generation'].get('max_ownership_candidates',3))-1)]:
                branches.append(branch(alt['strategy']+' Reason: '+alt['rationale']))
            b['alternatives_scheduled']=True
        save(checkpoint,{'branches':branches,'attempts':attempts,'model_calls':provider.calls})
    return attempts,survivors


def build(project,output,cfg,diagnostics=None,regression_path=None,progress=None,baseline_store=None):
    cfg=deepcopy(cfg)
    if cfg['generation']['workflow']=='segmented-v8' and cfg.get('v8',{}).get('correctness_only'):
        from .segmented_config import configure
        cfg=configure(cfg)
    if cfg['testing'].get('transport')=='auto':
        cfg['testing']['transport']='native-u128' if cfg['preprocessing']['numeric_mode']=='checked' else 'dashu-ubig'
    project=Path(project).resolve();output=Path(output).resolve()
    temporary=None
    if diagnostics:work=Path(diagnostics).resolve();work.mkdir(parents=True,exist_ok=True)
    else:temporary=tempfile.TemporaryDirectory(prefix='i2r-knowledge-');work=Path(temporary.name)
    executor=Executor(work/'commands');provider=Provider(cfg,work/'model')
    if baseline_store:executor.shared_cargo_root=ROOT/'cache/cargo-shared'
    result={'schema_version':2,'workflow':cfg['generation']['workflow'],'context_policy':'bounded-v1' if tc.enabled(cfg) else 'full-material','started_at':now(),'status':'running','phase':'preprocessing','config':cfg,
            'attempts':[],'source_optimization':{'status':'disabled'},'implementation_limits':[
                'Source correspondence is traceability, not a Rust equivalence proof.',
                'Test connection is generated separately and validated compositionally; manual timing-boundary review is required.',
                'All graph nodes are archived; model reads a complete index plus requested bodies. This is not a general large-project partitioning solution.']}
    if cfg['generation']['workflow']in {'segmented-v7','segmented-v8'}:
        result['context_policy']='unit-paged-v1'
        result['implementation_limits']=['Coverage/review and differential tests are evidence, not a formal Rust equivalence proof.']
    import time
    stage_clock=time.monotonic();active_phase=result['phase']
    with (work/'phase-events.jsonl').open('a') as stream:stream.write(json.dumps({'event':'phase_started','phase':active_phase,'at':now()})+'\n')
    def update(changes):
        nonlocal stage_clock,active_phase
        next_phase=changes.get('phase',active_phase)
        if next_phase!=active_phase:
            stamp=time.monotonic()
            event={'event':'phase_completed','phase':active_phase,'next_phase':next_phase,'at':now(),'seconds':stamp-stage_clock,'model_calls':provider.calls,'usage':provider.usage,'status':changes.get('status',result.get('status'))}
            with (work/'phase-events.jsonl').open('a') as stream:
                stream.write(json.dumps(event,ensure_ascii=False)+'\n')
                if next_phase!='finished':stream.write(json.dumps({'event':'phase_started','phase':next_phase,'at':now(),'model_calls':provider.calls})+'\n')
            active_phase=next_phase;stage_clock=stamp
        result.update(changes);save(work/'result.json',result)
        if progress:progress(result)
    try:
        if output.exists() and any(output.iterdir()):raise Failure('output_exists','Output must be empty: '+str(output))
        if cfg['source_optimization']['enabled']:raise Failure('source_optimization_disabled','Source optimization is not part of this experiment')
        if not cfg['repair'].get('enabled',True) or cfg['generation'].get('strategy')!='structured' or cfg['preprocessing'].get('mode')!='auto':
            raise Failure('unsupported_configuration','knowledge-v5 currently supports structured generation, automatic semantic analysis and correctness repair. Legacy source_only/no-repair/fixed-profile ablations have not been ported; this configuration will not be silently ignored.')
        metadata=read(project/'case.json') if (project/'case.json').exists() else {}
        result['case']=metadata.get('id');save(work/'effective-config.json',cfg)
        program=project/metadata.get('algorithm_project','.')
        testing=project/metadata['testing_project'] if metadata.get('testing_project') else None
        prepared=work/'prepared-program.json'
        from . import prepared_identity
        cache_identity=prepared_identity.identity(program,cfg)
        if prepared.exists():
            bundle=read(prepared);prepared_identity.validate(bundle,cache_identity);record={'status':'analyzed','analysis':bundle['semantic_analysis'],'resumed':True}
        else:
            from .source_cache import load as load_source_cache
            bundle=load_source_cache(program,cfg)
            if bundle is None:bundle=preprocess(program,cfg,work/'preprocessing',executor)
            else:save(work/'source-cache-reuse.json',{'kind':'mechanical_source_only','cache':cfg['preprocessing']['source_cache'],'new_model_analysis_required':True})
            if metadata.get('id'):bundle['case']=metadata['id']
            bundle['original_programs']=deepcopy(bundle['programs'])
            for field in ['observation_binding','kernel','workload','contract']:bundle.pop(field,None)
            save(work/'preprocessing/program.json',bundle)
            bundle,record=analyze(bundle,cfg,provider,work/'planning')
            bundle['prepared_identity']=cache_identity
            save(prepared,bundle)
        result['tool_sources']=bundle['tool_sources']
        result['program_summary']=[{'entries':p['entries'],'nodes':len(p['nodes']),'sccs':len(p['sccs'])} for p in bundle['programs']]
        update({'preprocessing':record})
        case=metadata.get('id');refs=None;baseline=None
        if testing:
            from .baselines import acquire
            update({'phase':'references'});baseline=acquire(case,testing,reference_bundle(testing,bundle),cfg,work,executor,baseline_store)
            refs=baseline['references'];update({'references':refs,'baseline':{'id':baseline['id'],'acquisition':baseline['acquisition'],'created_at':baseline['created_at']}})
        regressions=work/'regressions.json'
        if not regressions.exists():save(regressions,read(regression_path) if regression_path and Path(regression_path).exists() else [])
        bits=input_bits(cfg);seed=cfg['testing']['seed']+int(hashlib.sha256((case or '').encode()).hexdigest()[:6],16)
        fixed_inputs=scoped_fixed(case,bits) if testing else []
        if testing and cfg['generation']['workflow']=='segmented-v8' and cfg['segmented']['development_performance']:
            from .v8_performance import workloads
            fixed_inputs+= [x for x in workloads(case,cfg) if x not in fixed_inputs]
        random_inputs=scoped_inputs(case,cfg['testing']['random_cases'],seed,bits) if testing else []
        final_inputs=scoped_inputs(case,cfg['testing']['final_cases'],seed+1000003,bits) if testing and not cfg.get('v8',{}).get('correctness_only') else []
        if cfg['generation']['workflow']in {'segmented-v7','segmented-v8'} and testing and not cfg.get('v8',{}).get('correctness_only'):
            from .segmented_inputs import split
            random_inputs,final_inputs,split_record=split(case,fixed_inputs,read(regressions),cfg['testing']['random_cases'],cfg['testing']['final_cases'],seed,bits)
            save(work/'input-partition.json',split_record)
            result['input_partition']=split_record
            if not final_inputs:raise Failure('missing_independent_holdout','Generator produced no unseen final inputs; do not claim held-out success',split_record)
        save(work/'development-inputs.json',{'fixed':fixed_inputs,'generated':random_inputs});save(work/'final-inputs.json',final_inputs)
        dev_keys={tuple(x) for x in fixed_inputs+random_inputs};final_keys={tuple(x) for x in final_inputs}
        result['input_statistics']={'development_requests':len(fixed_inputs)+len(random_inputs),'development_unique':len(dev_keys),
            'final_requests':len(final_inputs),'final_unique':len(final_keys),'development_final_overlap_unique':len(dev_keys&final_keys),
            'boundary':'Final samples are not fed back, but generators can produce overlapping inputs.'}
        result['experiment_input_domain']={'max_input_bits':bits or None,'scope':'input bound only; intermediate overflow remains checked',
            'fixed_outside_domain':[x for x in fixed(case) if not in_numeric_domain(x,bits)] if testing else []}
        if refs:
            reference_execution=reference_outputs(case,fixed_inputs+random_inputs,refs,executor,cfg['testing']['process_timeout'])
            if 'selection' in reference_execution:
                save(work/'reference-execution.json',reference_execution)
                update({'reference_preflight':reference_execution['selection'],'reference_policy':reference_execution['selection']['policy']})
        run_search = search
        if cfg['generation']['workflow']=='source-v6':
            from .source_run import search as run_search
        if cfg['generation']['workflow']in {'segmented-v7','segmented-v8'}:
            from .segmented_run import search as run_search
            if cfg['generation']['workflow']=='segmented-v8':
                from .segmented_v8 import search as run_search
        attempts,survivors=run_search(bundle,testing,cfg,provider,work,executor,refs,fixed_inputs,random_inputs,regressions,update)
        if not survivors:
            exhausted=(bool(cfg['repair']['max_attempts']) and provider.phase_calls['generation']>=cfg['repair']['max_attempts']) or (bool(cfg['budgets']['max_model_calls']) and provider.calls>=cfg['budgets']['max_model_calls'])
            raise Failure('attempt_budget_exhausted' if exhausted else 'generation_stalled',
                'No candidate passed: shared budget exhausted' if exhausted else 'No candidate passed: repeated unchanged failures stopped progress; inspect attempt diagnostics')
        # Performance may select already existing candidates; results never feed model calls.
        selected=survivors[0];measurements=[]
        if refs and cfg['performance']['enabled']:
            workload=scoped_performance_input(case,cfg['performance'].get('input_bits',128))
            measure_cfg=deepcopy(cfg);measure_cfg['performance'].pop('input_bits',None)
            expected=reference_outputs(case,[workload],refs,executor,cfg['testing']['process_timeout'])['ocaml']['outputs'][0]
            for survivor in survivors:
                perf=benchmark({'candidate':survivor['binary']},workload,expected,measure_cfg,executor,work/('measure-'+survivor['id']))
                measurements.append({'candidate':survivor['id'],'performance':perf})
            selected=min(survivors,key=lambda s:next(m['performance']['summary']['candidate']['median_ns'] for m in measurements if m['candidate']==s['id']))
            result['performance']=next(m['performance'] for m in measurements if m['candidate']==selected['id'])
            from .baselines import measure_once
            result['baseline_measurement']=measure_once(baseline,workload,expected,measure_cfg,executor)
        result['candidate_measurements']=measurements;result['selected_candidate']=selected['id'];result['selected_attempt']=selected['attempts'][-1]
        result['numeric_representation']=selected.get('numeric_representation',selected['plan'].get('adaptation',{}).get('numeric','unreported'))
        result['adaptation']=selected['plan'].get('adaptation',{})
        result['quality_evidence']=selected.get('quality_evidence',{})
        if cfg['generation']['workflow']=='segmented-v8':result['v8_evidence']=selected.get('v8_evidence',{})
        result['representation_decisions']=selected.get('decisions',[])
        loaded=selected['bundle'].get('loaded_adapter',{})
        result['binding_audit']={'theory':loaded.get('theory'),'audit':loaded.get('audit'),
            'bindings':loaded.get('bindings',{}),'numeric_representation_source':'Model-reported; inspect actual code and loaded bindings alongside this label.'}
        update({'phase':'delivery' if cfg.get('v8',{}).get('correctness_only') else 'final_evaluation'})
        if cfg.get('v8',{}).get('correctness_only'):
            result['final_evaluation']={'status':'removed','reason':'Correctness-only uses source tests and repairable reference differential checks; availability policy is explicit'}
        if refs and not cfg.get('v8',{}).get('correctness_only'):
            result['final']=check_suite(case,final_inputs,selected['binary'],refs,executor,cfg['testing']['process_timeout'],'final_generated_differential')
            result['final_kernel']=check_suite(case,final_inputs,selected['binary'],refs,executor,cfg['testing']['process_timeout'],'final_kernel_differential',arguments=('--i2r-benchmark',))
            for key in ['final','final_kernel']:
                if result[key]['status']!='passed':
                    add_regressions(work/'released-final-counterexamples.json',result[key]['counterexamples'])
                    raise Failure(key+'_failed','Held-out evaluation failed; not fed back into this run',result[key])
        shutil.copytree(selected['crate'],output,dirs_exist_ok=True,symlinks=False,ignore=shutil.ignore_patterns('target') if cfg['generation']['workflow']in {'segmented-v7','segmented-v8'} else None)
        save(output/'tool-sources.json',bundle['tool_sources']);result.update(output=str(output),code_sha256=digest(output/'src/lib.rs'))
        result['crate_files']={str(p.relative_to(output)):digest(p) for p in output.rglob('*') if p.is_file() and 'target' not in p.parts}
        save(output/'artifact-manifest.json',result['crate_files']);tool_sources.verify(bundle['tool_sources'])
        from .reference_policy import enabled,POLICY
        if enabled(cfg):update(correctness_delivery(selected,cfg,work))
        else:update({'status':'passed','phase':'finished'})
    except Failure as error:
        update({'status':error.code,'phase':'finished','error':str(error),'error_evidence':error.evidence})
        from .source_stage_outcomes import after_source_failure
        try:
            supplemental=after_source_failure(work,cfg,provider,executor,locals().get('refs'),locals().get('testing'),error)
            if supplemental:update(supplemental)
        except Exception as supplemental_error:
            import traceback
            (work/'supplemental-error.txt').write_text(traceback.format_exc())
            update({'supplemental_collection_failure':{'type':type(supplemental_error).__name__,'message':str(supplemental_error),'trace':str(work/'supplemental-error.txt')},'verified_end_to_end':False})
    except KeyboardInterrupt:update({'status':'interrupted'});raise
    except Exception as error:
        import traceback
        (work/'internal-error.txt').write_text(traceback.format_exc())
        update({'status':'internal_error','phase':'finished','error':type(error).__name__+': '+str(error),'error_evidence':str(work/'internal-error.txt')})
    finally:
        status=result.get('status','unknown')
        result['failure_class']=('reference_unavailable' if status=='generated_reference_unavailable' else 'none' if status=='passed' else 'budget_exhausted' if 'budget' in status else 'timeout' if 'timeout' in status else 'model_error' if 'provider' in status else 'reference_conflict' if status.startswith('oracle_') else 'numeric_range' if 'range' in status else 'semantic_failure' if status in {'mismatch','support_contract_failed','repair_stalled','candidate_semantic_rejected'} else 'controller_or_infrastructure')
        result.update(finished_at=now(),usage=provider.usage,model_calls=provider.calls,model_calls_by_phase=provider.phase_calls)
        update({})
        if temporary:temporary.cleanup()
    return result


def correctness_delivery(selected,cfg,work):
    """Policy-aware aggregation of already executed source/reference evidence."""
    from .reference_policy import POLICY,LANES
    from .source_stage_outcomes import facts
    from .source_failure_review import POLICY as failure_policy,require_state,require_revision
    work=Path(work);suites=selected.get('differential_suites',[])
    source_passed=selected.get('support_evidence',{}).get('status')=='passed'
    failure_only=selected.get('source_failure_review_policy')==failure_policy and selected.get('source_suite_review_required') is False
    checked=False;check_status='unavailable';review=selected.get('support_review_evidence')
    if failure_only and source_passed:
        require_state(selected,cfg,work) # exact current candidate/source/test execution and inventory
        ledger_path=work/'source-failure-check/ledger.json'
        ledger=read(ledger_path) if ledger_path.exists() else {'attempts':[]}
        if review or ledger.get('attempts'):
            evidence=(review or {}).get('source_check',{})
            frozen=read(work/'support-tests'/(selected['support_evidence']['frozen_identity']+'.json'))
            require_revision(frozen,selected,cfg,{'revision':{'failed_test_ids':evidence.get('failed_test_ids',[])},'source_check':evidence})
            rows=[r for r in ledger['attempts'] if r.get('status')=='completed' and r.get('action')=='accept' and r.get('scope')==evidence.get('scope') and r.get('resolved_verdict_sha256')==evidence.get('verdict_sha256') and r.get('directory')==evidence.get('evidence')]
            if len(rows)!=1:raise Failure('source_check_unresolved','Triggered failure check lacks its complete current-scope accepted ledger record')
            from .source_suite_review import verify_receipt
            for correction in rows[0].get('citation_protocol_attempts',[]):
                if correction.get('status')=='completed':verify_receipt(correction.get('provider_receipt'))
            checked=True;check_status='failure_scope_accepted'
        else:
            # A missing review cannot erase a real failed assertion occurrence.
            for old in selected.get('failures',[]):
                if old.get('kind')!='support':continue
                path=Path(old.get('evidence',''))
                if not path.is_file():raise Failure('source_check_unresolved','Missing archived source-failure classification')
                if read(path).get('support',{}).get('status')=='support_contract_failed':raise Failure('source_check_unresolved','Executed semantic failure was never independently resolved')
            check_status='not_required'
    elif not failure_only:
        checked=(review or {}).get('status')=='accepted';check_status='whole_suite_accepted' if checked else 'unavailable'
    def executed_reference_suite(suite):
        cov=suite.get('reference_coverage',{});count=suite.get('count',0);matrix=cov.get('matrix',[])
        if suite.get('status')!='passed' or suite.get('failures')!=0 or not isinstance(count,int) or count<=0 or cov.get('policy')!=POLICY or cov.get('status')!='passed' or cov.get('complete') is not True or cov.get('covered')!=count or cov.get('total')!=count or len(matrix)!=count:return False
        candidate=suite.get('candidate',{})
        if candidate.get('status')!='passed' or candidate.get('returncode')!=0 or not Path(candidate.get('stdout','')).is_file():return False
        inputs=suite.get('reproducer',{}).get('inputs')
        if inputs is not None and len(inputs)!=count:return False
        for i,row in enumerate(matrix):
            available=row.get('available',[]);refs=row.get('references',{})
            if row.get('input_index')!=i or not available or len(set(available))!=len(available) or set(available)-set(LANES) or row.get('expected') is None:return False
            if inputs is not None and row.get('input')!=inputs[i]:return False
            for name in available:
                ref=refs.get(name,{});rec=ref.get('record',{})
                if ref.get('status')!='passed' or ref.get('output')!=row['expected'] or rec.get('status')!='passed' or rec.get('returncode')!=0 or not Path(rec.get('stdout','')).is_file():return False
        return True
    diff_passed=bool(suites) and all(executed_reference_suite(s) for s in suites)
    kinds=[s.get('kind') for s in suites]
    if len(set(kinds))!=len(kinds):diff_passed=False
    admitted=work/'development-inputs.json'
    if admitted.exists():
        inputs=read(admitted)
        for name,key in [('fixed','fixed'),('generated_differential','generated')]:
            if inputs.get(key) and any(prefix+name not in kinds for prefix in ('','kernel_')):diff_passed=False
    checker_satisfied=check_status in {'not_required','failure_scope_accepted','whole_suite_accepted'}
    verified=source_passed and diff_passed and checker_satisfied
    info=facts(selected,'passed',{'status':'passed' if diff_passed else 'differential_unavailable','suites':suites},work=work)
    info['source_test_validation']['oracle_status']=check_status
    info.update(status='passed' if verified else 'generated_source_test_unavailable' if not source_passed else 'generated_source_check_unavailable' if not checker_satisfied else 'generated_reference_unavailable',phase='finished',generation_success=True,source_test_success=source_passed,verified_end_to_end=verified,source_test_check_success=True if checked else None if check_status=='not_required' else False,source_test_check_status=check_status,source_test_check_required=check_status!='not_required',source_test_check=review,reference_policy=POLICY,differential_status='passed' if diff_passed else 'unavailable_or_partial',reference_coverage=[{'kind':s['kind'],**s.get('reference_coverage',{})} for s in suites])
    return info
