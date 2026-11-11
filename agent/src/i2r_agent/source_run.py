"""Source-driven generation, early refinement and evidence-driven repair."""
from copy import deepcopy
import json
from pathlib import Path
from .common import Failure, read, save, now
from .knowledge import call, requested, merge_mapping, validate_dependencies
from .knowledge_run import write_library, verify_support_issue
from .pipeline import feedback_for
from .references import cargo, compile_rust
from .storage import cargo_cache
from . import task_context as tc, repair_state as repair, test_connector
from .source_context import payload, coverage
from .repair_diagnostics import compiler_messages, runtime
from .repair_actions import EditController
from .validation import check_suite, add_regressions
from .suites import input_bits, in_numeric_domain


def compile_library(crate,cfg,executor):
    with cargo_cache(executor,cfg) as target:
        executor.run(cargo(cfg,'clean','--release','--package','i2r_candidate','--manifest-path',crate/'Cargo.toml','--target-dir',target),timeout=cfg['budgets']['build_seconds'])
        result=executor.run(cargo(cfg,'build','--lib','--release','--message-format=json-render-diagnostics',
            '--manifest-path',crate/'Cargo.toml','--target-dir',target),timeout=cfg['budgets']['build_seconds'],check=False)
    return {'status':'passed' if result['status']=='passed' else 'compile_failed',
        'checks':{'build':result},'diagnostics':compiler_messages(result)}


def search(bundle,testing_project,cfg,provider,work,executor,refs,fixed_inputs,random_inputs,regressions,update):
    work=Path(work); checkpoint=work/'generation-checkpoint.json'
    if checkpoint.exists():
        saved=read(checkpoint);b=saved['branches'][0];attempts=saved['attempts']
    else:
        b={'id':'candidate-1','strategy':'Source-grounded main implementation','bundle':deepcopy(bundle),
            'files':{},'mapping':[],'plan':{'dependencies':{},'build_dependencies':{}},
            'decisions':[],'repair_history':[],'feedback':None,'mode':'generate','connector':{},
            'connector_feedback':None,'status':'active','attempts':[],'extra':deepcopy(bundle.get('knowledge_material',{})),'pending_material':{},'repeat_count':0,'seen':{}}
        attempts=[]
    tc.register(b['bundle'],work/'context/materials',b['files'])
    edit_controller=EditController(work/'context/algorithm-actions','algorithm',tc.Archive(b['bundle']['_context_archive']))
    while b['status']=='active':
        number=len(attempts)+1;path=work/f'candidate-{number:02d}';path.mkdir(parents=True,exist_ok=True)
        before=deepcopy(b['files']);before_connector=deepcopy(b['connector']);reply=None;repair.capture(b)
        before_mapping=deepcopy(b['mapping']);before_plan=deepcopy(b['plan'])
        original_issue=(b.get('repair_issue') or {}).get('id')
        mode=b['mode'];attempt={'attempt':number,'action_phase':mode,'started_at':now(),'ownership_candidate':b['id']}
        attempts.append(attempt);b['attempts'].append(number)
        update({'phase':mode,'attempts':attempts})
        try:
            if mode in {'generate','quick_refine','repair','review','connect'} and provider.phase_calls['generation']>=cfg['repair']['max_attempts']:
                b['status']='budget_exhausted';attempt['development']={'status':'attempt_budget_exhausted'};break
            if mode=='compile':
                if not b.get('quick_done'):
                    b['mode']='quick_refine';attempt['development']={'status':'quality_review_required'};continue
                attempt['plan_contract']=coverage(b['bundle'],b['files'],b['mapping'])
                repair.verified(b,'contract',tc.fingerprint({'files':b['files'],'mapping':b['mapping']}))
                crate=path/'algorithm';write_library(crate,b['files'],b['plan'],b['bundle'])
                attempt['crate']=str(crate)
                save(crate/'translation.json',{'mapping':b['mapping'],'decisions':b['decisions']})
                result=compile_library(crate,cfg,executor);attempt['compilation']=result
                edit_controller.verify(b['files'],'compile',result['status'],path/'attempt.json')
                attempt['development']={'status':result['status'],'compilation':result,'suites':[]}
                b['crate']=str(crate)
                if result['status']=='passed':
                    repair.verified(b,'compile',tc.fingerprint(b['files']))
                    b['mode']='connect' if testing_project else 'review';b['feedback']=None
                else:
                    b['feedback']=feedback_for(attempt['development']);b['feedback']['structured_diagnostics']=result['diagnostics'];b['mode']='repair'
            elif mode=='connect':
                if not b['connector'] or b.get('connector_feedback'):
                    connector,notes=test_connector.connect(testing_project,b['crate'],b['files'],b['mapping'],b['plan'],cfg,provider,path/'connection',
                        b['connector'],b.get('connector_feedback'),context_directory=work/'context/connector',original_issue=repair.feedback(b) if b.get('repair_issue') else None)
                    if connector==b['connector'] and b.get('connector_feedback'):
                        raise Failure('unchanged_connector','No change to failing connector; route an algorithm defect explicitly')
                    b['connector']=connector;b['connector_notes']=notes
                b['mode']='test';attempt['development']={'status':'connector_ready'}
            elif mode=='test':
                crate=path/'algorithm';write_library(crate,b['files'],b['plan'],b['bundle'])
                attempt['crate']=str(crate)
                save(crate/'translation.json',{'mapping':b['mapping'],'decisions':b['decisions']})
                harness=test_connector.materialize(crate,b['connector'],b['plan'],cfg)
                compiled=compile_rust(harness,cfg,executor,candidate=True);attempt['compilation']=compiled
                connector_edits=EditController(work/'context/connector/actions','connector',tc.Archive(work/'context/connector/materials'))
                connector_edits.verify(b['connector'],'compile',compiled['status'],path/'attempt.json')
                b['crate']=str(crate);b['harness']=str(harness);b['binary']=compiled.get('binary')
                if compiled['status']!='passed':
                    attempt['development']={'status':'compile_failed','compilation':compiled,'suites':[]}
                    b['connector_feedback']=feedback_for(attempt['development']);b['mode']='connect'
                    continue
                repair.verified(b,'compile',tc.fingerprint({'files':b['files'],'connector':b['connector']}))
                if (b.get('repair_issue') or {}).get('kind')=='support':
                    checked=verify_support_issue(b,crate,cfg,executor,path)
                    if checked['status']!='passed':raise Failure('support_contract_failed','Independent operation check failed',checked)
                    repair.verified(b,'support',tc.fingerprint(b['files']))
                history=read(regressions) if Path(regressions).exists() else []
                specs=[('repair_reproducer',repair.reproducer_inputs(b)),('fixed',fixed_inputs),
                    ('regression',[x['input'] for x in history if in_numeric_domain(x['input'],input_bits(cfg))]),
                    ('generated_differential',random_inputs)]
                tests=[]
                for name,inputs in specs:
                    if not inputs: continue
                    for prefix,args in [('',()),('kernel_',('--i2r-benchmark',))]:
                        suite=check_suite(b['bundle']['case'],inputs,compiled['binary'],refs,executor,cfg['testing']['process_timeout'],prefix+name,arguments=args)
                        tests.append(suite);add_regressions(regressions,suite['counterexamples'])
                status=next((t['status'] for t in tests if t['status']!='passed'),'passed')
                result={'status':status,'compilation':compiled,'suites':tests,'behavior_checked':True,
                    'count':sum(t['count'] for t in tests),'failures':sum(t['failures'] or 0 for t in tests)}
                attempt['development']=result
                edit_controller.verify(b['files'],'behavior',status,path/'attempt.json')
                connector_edits.verify(b['connector'],'behavior',status,path/'attempt.json')
                if status=='passed':
                    repair.verified(b,'behavior',tc.fingerprint(b['files']));b['behavior_validated']=tc.fingerprint(b['files'])
                    b['mode']='review';b['feedback']=None;b['connector_feedback']=None
                else:
                    b['feedback']={'status':status,'behavior_failure':feedback_for(result),'test_connection':b['connector']};b['mode']='repair'
                    repair.capture(b)
                    failed=next(t for t in tests if t['status']!='passed')
                    if status in {'numeric_range_exceeded','candidate_failed','candidate_timeout'} or b['feedback']['behavior_failure'].get('runtime_diagnostics'):
                        b['feedback']['runtime_localization']=runtime(harness,repair.reproducer_inputs(b),cfg,executor,path/'runtime-diagnostic',
                            ('--i2r-benchmark',) if failed['kind'].startswith('kernel_') else ())
            else:
                current=payload(b,cfg,work)
                if mode=='review' and b['connector']:
                    current['connection_review']={'files':b['connector'],'scenarios':{n:(Path(testing_project)/n).read_text() for n in ['Model.thy','Kernel.thy']}}
                reply=call(provider,cfg,path,'generation',current);b['pending_material']={}
                additions=requested(reply,b['bundle'],b['files'])
                if additions:
                    b['extra']=tc.merge_material(b['extra'],additions);b['pending_material']=additions
                    attempt['development']={'status':'material_requested'};continue
                if reply.get('action')=='request_diagnostics':
                    if not b.get('harness'):raise Failure('invalid_candidate','Runtime diagnostics require a built test connection')
                    b.setdefault('feedback',{})['runtime_localization']=runtime(b['harness'],repair.reproducer_inputs(b),cfg,executor,path/'requested-diagnostic')
                    attempt['development']={'status':'diagnostic_requested'};continue
                action=reply.get('action','generate');attempt['action']=action
                if action=='repair_connection':
                    if not reply.get('connector_issue'):raise Failure('invalid_candidate','Give the specific wrong call/conversion')
                    b['connector_feedback']={'diagnosis':reply['connector_issue'],'failure':b['feedback']};b['mode']='connect'
                    attempt['development']={'status':'connection_repair_requested'};continue
                if action=='accept':
                    if mode not in {'quick_refine','review'}:raise Failure('invalid_candidate','Accept is only a quality-review action')
                    from .code_quality import validate_review
                    validate_review(b['files'],reply)
                    if mode=='quick_refine':b['mode']='compile';b['quick_done']=True
                    else:
                        repair.ensure_acceptible(b)
                        if testing_project and b.get('behavior_validated')!=tc.fingerprint(b['files']):raise Failure('unresolved_issue','Current code has not passed behavior validation')
                        b['status']='passed'
                    b['feedback']=None;attempt['development']={'status':'quality_reviewed','review':reply.get('quality_review')};continue
                if action!='generate':raise Failure('invalid_candidate','Use generate with Rust code/edits; no Isabelle printing installation exists in source-v6')
                if b['mapping']!=before_mapping or b['plan']!=before_plan:
                    raise Failure('stale_patch','Realizations or dependencies changed after this request; reread current state')
                deps=reply.get('dependencies',b['plan']['dependencies']);build_deps=reply.get('build_dependencies',b['plan']['build_dependencies'])
                validate_dependencies(deps,build_deps)
                mapping=merge_mapping(b['mapping'],reply.get('mapping'),reply.get('remove_mapping'))
                metadata_changed=(mapping!=b['mapping'] or deps!=b['plan']['dependencies'] or build_deps!=b['plan']['build_dependencies'])
                new=edit_controller.apply(b['files'],reply,before,path,
                    require_change=not metadata_changed and mode not in {'quick_refine','review'},
                    metadata_before={'mapping':before_mapping,'dependencies':before_plan},
                    metadata_after={'mapping':mapping,'dependencies':{**b['plan'],'dependencies':deps,'build_dependencies':build_deps}})
                changed=new!=b['files'] or deps!=b['plan']['dependencies'] or build_deps!=b['plan']['build_dependencies']
                if not changed and mapping==b['mapping'] and mode not in {'quick_refine','review'}:
                    raise Failure('unchanged_repair','Actual code and mapping are unchanged. Read the responsible definition or request diagnostics; repeating this proposal cannot repair the issue.')
                b['files']=new;b['mapping']=mapping;b['plan'].update(dependencies=deps,build_dependencies=build_deps)
                tc.update_decisions(b,reply)
                b['numeric_representation']=reply.get('numeric_representation',b.get('numeric_representation','model-selected'))
                if changed:b.pop('behavior_validated',None)
                b['mode']='quick_refine' if mode=='generate' else 'compile'
                if mode=='quick_refine':b['quick_done']=True
                b['feedback']=None;b['connector_feedback']=None
                attempt['development']={'status':'quality_refined' if mode in {'quick_refine','review'} else 'implementation_updated'}
        except Failure as error:
            if error.code in {'provider_error','budget_exhausted','context_budget_exceeded'}:raise
            if mode in {'generate','quick_refine','repair','review'} and error.code in repair.PROTOCOL_ERRORS:
                try:edit_controller.reject(b['files'],reply,error,path,before)
                except Failure as stalled:error=stalled
            attempt['development']={'status':error.code,'message':str(error),'evidence':error.evidence}
            if error.code=='repair_protocol_stalled':
                b['status']='repair_protocol_stalled'
            elif mode=='connect' and error.code=='connector_algorithm_defect':
                b['feedback']={'algorithm_issue':str(error),'connection_feedback':b.get('connector_feedback')};b['mode']='repair'
            elif mode=='connect':
                b['connector_feedback']=attempt['development']
            else:
                b['feedback']=attempt['development'];b['mode']=mode if mode in {'quick_refine','review'} else 'repair'
        finally:
            attempt['finished_at']=now()
            status=attempt.get('development',{}).get('status')
            active_feedback=b.get('connector_feedback') if mode=='connect' else b.get('feedback')
            if active_feedback and status not in {'material_requested','diagnostic_requested'}:
                import re
                fb=active_feedback; behavioral=fb.get('behavior_failure',{})
                key=tc.fingerprint({'status':fb.get('status'),
                    'compiler_codes':[m.get('code') for m in fb.get('structured_diagnostics',[])],
                    'inputs':repair.reproducer_inputs(b) if behavioral else [],
                    'message':re.sub(r'candidate-\d+','candidate-N',str(fb.get('message',''))),
                    'behavior_status':behavioral.get('status')})
                b['seen'][key]=b['seen'].get(key,0)+1;b['repeat_count']=b['seen'][key]-1
                if b['repeat_count']:
                    fb['next_step']='Compare actual executed diffs and operation outcomes. Change the explanation or obtain diagnostic evidence before repeating a rejected patch.'
            repair.capture(b)
            tc.record_attempt(b,attempt,before,reply,path,before_issue=original_issue,before_connector=before_connector,before_mapping=before_mapping)
            save(path/'attempt.json',attempt);save(checkpoint,{'branches':[b],'attempts':attempts,'model_calls':provider.calls})
            update({'attempts':attempts,'model_calls':provider.calls,'usage':provider.usage})
    return attempts,[b] if b['status']=='passed' else []
