"""Separate generated-code facts from test-production failure and supplemental differential evidence."""
from pathlib import Path
from copy import deepcopy
from .common import Failure,read,save
from .task_context import fingerprint


def source_failure_state(work):
    path=Path(work)/'segmented-checkpoint.json'
    if not path.exists():return None
    state=read(path)
    active=next((r for r in state.get('repair_issues',[]) if r.get('status')=='open'),{})
    if state.get('phase') not in {'support','source_test_check','support_execute','support_audit','support_check'} and not (state.get('phase') in {'repair','repair_replay','repair_diagnose'} and active.get('kind')=='support'):return None
    units=state.get('partition',{}).get('units',{})
    if not units or set(state.get('completed',[]))!=set(units):return None
    return state


def facts(state,compile_status,differential,error=None,work=None):
    support=state.get('support_evidence') or {}
    produced=bool(support.get('frozen_identity'))
    production='produced' if produced else 'failed_or_partial' if error else 'not_started'
    validation=support.get('status','not_executed')
    suites=differential.get('suites',[])
    diff_status=differential.get('status','not_run')
    # A source failure remains open even when every exported observation agrees.
    open_source=bool(error) or validation not in {'passed'}
    source_conflict=validation not in {'passed','not_executed'} or bool(error and error.get('code')=='support_oracle_dispute')
    return {'generation_success':compile_status=='passed','source_test_success':validation=='passed',
            'verified_end_to_end':compile_status=='passed' and validation=='passed' and diff_status=='passed' and not error and state.get('support_review_evidence',{}).get('status')=='accepted',
            'differential_status':diff_status,
            'generation':{'status':'compiled' if compile_status=='passed' else compile_status,'candidate_identity':fingerprint([state.get('files'),state.get('rust_config')]),'meaning':'Code produced and compiled, not a semantic correctness claim'},
            'source_test_production':{'status':production,'frozen_identity':support.get('frozen_identity'),'error':error,'artifact_root':str(Path(work)/'support-tests') if work else None},
            'source_test_validation':{'status':validation,'unresolved':open_source,'conflicting':source_conflict,'evidence':support,
                                      'oracle_status':'independently_checked' if support.get('source_test_check',{}).get('status')=='accepted' else 'disputed' if error and error.get('code')=='support_oracle_dispute' else 'not_independently_established',
                                      'interpretation':'Candidate agreement or differential agreement does not establish a generated test oracle. Original assertions, obligations and failures remain authoritative evidence.'},
            'differential':differential,
            'candidate_defect_status':'observed_differential_or_compile_failure' if compile_status!='passed' or diff_status in {'mismatch','runtime_failed','numeric_range_exceeded','protocol_failed'} else 'source_conflict_unresolved' if source_conflict else 'no_observed_defect_in_executed_checks',
            'reference_coverage':[{'kind':s['kind'],**s.get('reference_coverage',{})} for s in suites]}


def collect(state,testing_project,cfg,provider,executor,refs,inputs,regressions,work):
    """Execute only connector/ordinary/kernel observation checks on this exact candidate.

    No source-test creation/review, no algorithm edits, and no change to the
    original source failure. A connector may consume remaining normal budget.
    """
    from . import translation_workflow as translation,test_connector
    from .segmented_config import materialize
    from .validation import check_suite
    from .suites import in_numeric_domain
    from .suites import input_bits
    work=Path(work);work.mkdir(parents=True,exist_ok=False)
    snapshot=deepcopy(state);candidate=fingerprint([snapshot['files'],snapshot['rust_config']]);save(work/'candidate-snapshot.json',{'files':snapshot['files'],'mapping':snapshot['mapping'],'rust_config':snapshot['rust_config'],'candidate_identity':candidate})
    crate=materialize(work/'candidate',{**snapshot['files'],'src/lib.rs':snapshot['files']['src/lib.rs']+translation.probes(snapshot['mapping'])},snapshot['rust_config'])
    compilation=translation.compile_crate(crate,snapshot['rust_config'],cfg,executor,True);save(work/'candidate-compile.json',compilation)
    result={'status':'not_run','candidate_identity':candidate,'compile':compilation,'suites':[],'candidate_code_changed':False,'source_tests_changed':False,'purpose':'Supplemental evidence only; cannot clear any original source/test issue'}
    if compilation['status']!='passed':result['status']='not_run_candidate_compile_failed';save(work/'result.json',result);return result
    if not testing_project or not refs:result['status']='differential_unavailable';save(work/'result.json',result);return result
    connector=deepcopy(snapshot.get('connector',{}));feedback=None
    try:
        for attempt in range(cfg['translation']['connector_stall_limit']):
            directory=work/f'connector-{attempt+1:02d}';directory.mkdir()
            if not connector or snapshot.get('connector_identity')!=translation.connector_identity(snapshot) or feedback:
                connector,notes=test_connector.connect(testing_project,crate,snapshot['files'],snapshot['mapping'],{'dependencies':snapshot['rust_config']['dependencies'],'rust_config':snapshot['rust_config']},cfg,provider,directory,connector,feedback,context_directory=work/'connector-context')
            harness=translation.connection(crate,connector,snapshot['rust_config'],cfg);built=translation.compile_crate(harness,snapshot['rust_config'],cfg,executor,False);save(directory/'compile.json',built)
            if built['status']=='passed':break
            feedback=built
        else:raise Failure('connector_stalled','Supplemental connector exhausted normal compilation attempts',feedback)
        result.update(connector=connector,binary=built['binary'],connector_compile=built)
        history=read(regressions) if Path(regressions).exists() else []
        specs=[('fixed',inputs['fixed']),('regression',[r['input'] for r in history if in_numeric_domain(r['input'],input_bits(cfg))]),('generated_differential',inputs['generated'])]
        for kind,values in specs:
            if not values:continue
            for prefix,args in [('',()),('kernel_',('--i2r-kernel-check',))]:
                suite=check_suite(snapshot['bundle']['case'],values,built['binary'],refs,executor,cfg['testing']['process_timeout'],prefix+kind,args);suite['exact_inputs']=values;result['suites'].append(suite)
        failed=next((s for s in result['suites'] if s['status'] not in {'passed','differential_unavailable'}),None)
        result['status']=failed['status'] if failed else 'differential_unavailable' if not result['suites'] or any(s['status']=='differential_unavailable' for s in result['suites']) else 'passed'
    except Failure as error:
        result.update(status='not_run_budget' if error.code=='budget_exhausted' else error.code,error={'code':error.code,'message':str(error),'evidence':error.evidence})
    if fingerprint([state['files'],state['rust_config']])!=candidate:raise Failure('supplemental_candidate_changed','Supplemental differential must not edit candidate code')
    save(work/'result.json',result);return result


def after_source_failure(work,cfg,provider,executor,refs,testing_project,error):
    if not cfg.get('translation',{}).get('correctness_only'):return None
    state=source_failure_state(work)
    if state is None:return None
    work=Path(work);inputs_path=work/'development-inputs.json'
    if not inputs_path.exists():return None
    evidence={'code':error.code,'message':str(error),'evidence':error.evidence,'checkpoint':str(work/'segmented-checkpoint.json')}
    suites=state.get('differential_suites',[])
    result={'status':'passed' if suites and all(s['status']=='passed' for s in suites) else 'differential_unavailable','suites':suites,'reuse':'Differential stage already executed before source validation; no post-failure models or rerun'}
    return facts(state,'passed',result,evidence,work)
