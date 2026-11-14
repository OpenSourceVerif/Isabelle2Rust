"""Paired backend evaluation after the unchanged correctness workflow finishes.

No model calls, source regeneration, source rewriting, or reference execution.
The first correctness run already checked the declared measurement inputs.
"""
from copy import deepcopy
from pathlib import Path
import fcntl
import hashlib
import math
import random
import shutil
import statistics
from .common import ROOT, Failure, Executor, digest, read, save
from .task_context import fingerprint
from . import numeric_interface as numeric
from .segmented_config import materialize
from .translation_workflow import connection, compile_crate, version
from .validation import execute


def file_hashes(files):
    return {k:hashlib.sha256(v.encode()).hexdigest() for k,v in sorted(files.items())}


def cached_observations(state):
    """Use executed reference output matrices, never model expectations."""
    result = {}
    for suite in state.get('differential_suites', []):
        if suite.get('status') != 'passed':
            raise Failure('paired_baseline_not_validated', 'Every original differential suite must have passed')
        reproducer=suite['reproducer']; rows=suite.get('reference_coverage',{}).get('matrix')
        if rows is None or len(rows)!=len(reproducer['inputs']):
            raise Failure('paired_reference_evidence_missing', suite['kind'])
        lane='kernel' if reproducer['arguments'] else 'ordinary'
        for x,row in zip(reproducer['inputs'],rows):
            if x!=row['input'] or not row['available'] or row['expected'] is None:
                raise Failure('paired_reference_evidence_missing', suite['kind'])
            key=(lane,tuple(x));expected=row['expected']
            if key in result and result[key]!=expected:
                raise Failure('paired_cached_reference_conflict', str(key))
            result[key]=expected
    if not result or {lane for lane,_ in result}!={'ordinary','kernel'}:
        raise Failure('paired_reference_evidence_missing', 'Both behavior paths require executed reference evidence')
    return result


def validate_lane(binary, observations, lane, backend, executor, timeout):
    pairs=[(list(x),y) for (kind,x),y in observations.items() if kind==lane]
    args=('--i2r-kernel-check',) if lane=='kernel' else ()
    checked=execute(binary,[x for x,_ in pairs],executor,timeout,arguments=args)
    records=[checked['record']];excluded=[]
    if checked['status']=='passed':
        actual=checked['outputs']
    elif backend=='checked' and checked['status']=='numeric_range_exceeded':
        # One failed process cannot establish the unexecuted suffix. Isolate all
        # inputs and retain explicit exclusions instead of dropping the batch.
        actual=[]
        for x,_ in pairs:
            single=execute(binary,[x],executor,timeout,arguments=args);records.append(single['record'])
            if single['status']=='numeric_range_exceeded':
                actual.append(None);excluded.append(x)
            elif single['status']=='passed':actual.append(single['outputs'][0])
            else:raise Failure('paired_behavior_failed', backend+':'+lane, single)
    else:raise Failure('paired_behavior_failed', backend+':'+lane, checked)
    mismatches=[{'input':x,'expected':expected,'actual':out} for (x,expected),out in zip(pairs,actual) if out is not None and out!=expected]
    if mismatches:raise Failure('paired_output_mismatch', backend+':'+lane, mismatches)
    return {'status':'passed','lane':lane,'backend':backend,'requested':len(pairs),
            'compared':len(pairs)-len(excluded),'range_exclusions':excluded,'records':records}


def freeze(run, row, directory, *, paired=True):
    from .experiment_baselines import resolve
    run=resolve(run,row['id'])
    task=Path(run)/'tasks'/row['id']; outcome=read(task/'outcome.json')
    if not outcome.get('policy_accepted') or outcome['result']['status']!='passed':
        raise Failure('paired_baseline_not_validated',row['id'])
    checkpoint=task/'diagnostics/segmented-checkpoint.json';state=read(checkpoint)
    cfg=read(task/'diagnostics/effective-config.json')
    if (paired and not numeric.enabled(cfg)) or state.get('support_evidence',{}).get('status')!='passed':
        raise Failure('paired_baseline_not_validated', 'Require paired generation and executed source tests')
    from .source_failure_review import require_state
    require_state(state,cfg,task/'diagnostics')
    if numeric.enabled(cfg):numeric.verify_runtime(state['rust_config'])
    numeric.validate_candidate(state['files'],state['rust_config'])
    observations=cached_observations(state)
    for workload in row['performance_workloads']:
        if ('kernel',tuple(workload['input'])) not in observations:
            raise Failure('paired_reference_evidence_missing','Timing input was not included in initial correctness validation: '+workload['id'])
    # Verify the delivered artifact remains the one recorded by the generator.
    delivered=Path(outcome['result']['output'])
    for name,expected in outcome['result']['crate_files'].items():
        if digest(delivered/name)!=expected:raise Failure('paired_original_changed',name)
    seal={'case':row['id'],'checkpoint_sha256':digest(checkpoint),'candidate_version':version(state),
          'business_files':file_hashes(state['files']),'connector_files':file_hashes(state['connector']),
          'numeric_runtime':state['rust_config'].get('numeric_interface'),'rust_config':state['rust_config'],
          'source_tests':state['support_evidence']['frozen_identity'],'reference_observations':fingerprint(sorted((lane,list(x),y) for (lane,x),y in observations.items())),
          'workloads':row['performance_workloads'],'implementation':'same frozen business AND connector source; compile-time numeric feature only',
          'original_artifact':str(delivered),'original_files':outcome['result']['crate_files'],
          'source_tests_reused':True,'reference_executions':0,'model_calls':0}
    path=Path(directory)/'frozen.json'
    if path.exists() and read(path)!=seal:raise Failure('paired_snapshot_changed',str(path))
    if not path.exists():save(path,seal)
    return state,cfg,observations,seal


def interval(arbitrary,checked):
    a=arbitrary['process_medians_ns'];b=checked['process_medians_ns']
    if len(a)!=len(b) or not a or min(a+b)<=0:raise Failure('invalid_paired_samples','Missing paired process rounds')
    rng=random.Random(20261113);samples=[]
    for _ in range(2000):
        idx=[rng.randrange(len(a)) for _ in a]
        samples.append(statistics.median(a[i] for i in idx)/statistics.median(b[i] for i in idx))
    samples.sort();return [samples[49],samples[1949]]


def measure_case(run,row,directory):
    from .kernel_build import build
    from .kernel_timing import DEFAULTS, measure_group
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    state,cfg,observations,seal=freeze(run,row,directory)
    finished=directory/'result.json'
    if finished.exists():
        result=read(finished)
        if result.get('frozen_sha256')!=digest(directory/'frozen.json'):
            raise Failure('paired_snapshot_changed',str(finished))
        if result.get('status')=='measured':return result
    measure_cfg=deepcopy(cfg)
    # Only the separate observer driver gets a clock. Generation policies and
    # accepted candidate/test files remain frozen and are not re-entered.
    measure_cfg['translation']['correctness_only']=False
    builds=[];validations={};snapshots={};locks={}
    for backend in ['arbitrary','checked']:
        rc=numeric.backend_config(state['rust_config'],backend);crate=directory/backend
        materialize(crate,state['files'],rc)
        harness=connection(crate,state['connector'],rc,measure_cfg)
        if backend=='checked':
            shutil.copyfile(directory/'arbitrary/harness/Cargo.lock',harness/'Cargo.lock')
        executor=Executor(directory/'commands'/backend)
        built=compile_crate(harness,rc,measure_cfg,executor,False)
        if built['status']!='passed':raise Failure('paired_backend_compile_failed',backend,built)
        locks[backend]=digest(harness/'Cargo.lock')
        validations[backend]=[validate_lane(built['binary'],observations,lane,backend,executor,cfg['testing']['process_timeout']) for lane in ['ordinary','kernel']]
        snapshots[backend]={'business':{name:digest(crate/name) for name in state['files']},
                            'connector':{name:digest(harness/name) for name in state['connector']},
                            'runtime':{name:digest(crate/name) for name in numeric.managed_runtime(rc)}}
        builds.append(build({'id':backend,'case':row['id'],'language':'rust','kind':'llm',
                             'source':str(crate),'work':str(directory/'timing-builds'/backend)},measure_cfg))
    if snapshots['arbitrary']!=snapshots['checked'] or locks['arbitrary']!=locks['checked']:
        raise Failure('paired_source_or_lock_mismatch','Business, connector, runtime and resolved dependencies must match byte for byte')
    save(directory/'validation.json',{'lanes':validations,'file_hashes':snapshots,'harness_lock_sha256':locks,
         'source_test_evidence_reused':seal['source_tests'],'reference_executions':0,'model_calls':0})
    excluded={tuple(x) for lane in validations['checked'] for x in lane['range_exclusions']}
    options={**DEFAULTS,**cfg['performance'].get('v2',{})}
    rows=[]
    for workload in row['performance_workloads']:
        values=workload['input'];name=workload['id']
        if tuple(values) in excluded:
            rows.append({'workload':name,'status':'checked_range_exceeded','speedup':None});continue
        work=directory/'measurements'/name
        # Each workload owns its process records; later measurements cannot
        # overwrite an earlier workload's warmup/sample provenance.
        scoped=[{**b,'work':str(work/b['id'])} for b in builds]
        result=measure_group(row['id'],scoped,values,observations[('kernel',tuple(values))],options,work)
        a=result['summary']['arbitrary'];b=result['summary']['checked']
        rows.append({'workload':name,'status':'measured','arbitrary_ns':a['median_ns'],'checked_ns':b['median_ns'],
                     'speedup':a['median_ns']/b['median_ns'],'speedup_ci95':interval(a,b),
                     'independent_processes':options['processes'],
                     'unstable_processes':{'arbitrary':a['unstable_processes'],'checked':b['unstable_processes']},
                     'record':str(work/'measurement-v2.json')})
    for name,expected in seal['original_files'].items():
        if digest(Path(seal['original_artifact'])/name)!=expected:raise Failure('paired_original_changed',name)
    measured=[r for r in rows if r['status']=='measured']
    result={'case':row['id'],'status':'measured' if measured else 'no_common_measurements',
            'optimization':'off','frozen_sha256':digest(directory/'frozen.json'),
            'primary_workload':row.get('primary_workload'),'rows':rows,
            'geomean_speedup':math.exp(statistics.mean(math.log(r['speedup']) for r in measured)) if measured else None,
            'common_domain':'Only executed inputs whose checked inputs, intermediates and outputs fit. No claim of unrestricted HOL equivalence for checked.',
            'model_calls':0,'reference_executions':0,'source_regeneration':False,'same_source':True}
    save(finished,result);return result


def measure_run(run,rows,release):
    run=Path(run);selection=read(run/'experiment.json') if (run/'experiment.json').exists() else {}
    if selection.get('numeric')!='paired' or selection.get('optimization')!='off':
        raise Failure('paired_configuration_required','Use --paired-numerics --off for the first numeric ablation')
    lockpath=ROOT/'cache/timing-v2.lock';lockpath.parent.mkdir(parents=True,exist_ok=True)
    results=[]
    with lockpath.open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for row in rows:
            directory=run/'performance/off'/row['id']
            try:result=measure_case(run,row,directory)
            except Failure as error:
                result={'case':row['id'],'status':error.code,'error':str(error),'evidence':error.evidence}
                save(directory/'failure.json',result)
            results.append(result)
            save(run/'numeric-ablation.json',{'release_identity':release['identity'],'results':results,'complete':False})
    report={'release_identity':release['identity'],'results':results,'complete':True,
            'measured':sum(r['status']=='measured' for r in results),'selected':len(rows),
            'matrix_rows':{'off':'this experiment','rust-only':'pending next stage','full':'pending next stage'}}
    save(run/'numeric-ablation.json',report);return report
