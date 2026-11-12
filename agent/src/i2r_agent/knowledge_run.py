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
from .segmented_context import analyze
from . import test_connector, tool_sources
from .validation import check_suite, reference_outputs, add_regressions
from .suites import input_bits, scoped_fixed, scoped_inputs, scoped_performance_input, in_numeric_domain, fixed
from .performance import benchmark
from . import task_context as tc


def failure(error):
    return {'status':error.code,'message':str(error),'evidence':error.evidence}


def reference_bundle(project,bundle):
    files={str(p.relative_to(project)):digest(p) for p in Path(project).rglob('*') if p.suffix in {'.thy','.ML'}}
    metadata=read(Path(project)/'case.json')
    for name in metadata.get('source_files',[]):files[name]=digest(name)
    return {'source_hashes':files,'tool_sources':bundle['tool_sources']}


def build(project,output,cfg,diagnostics=None,regression_path=None,progress=None,baseline_store=None):
    cfg=deepcopy(cfg)
    if cfg.get('generation',{}).get('workflow') != 'source-translation':
        raise Failure('unknown_workflow', 'This artifact supports source-translation only; use the historical workspace for older workflows')
    if cfg.get('translation',{}).get('correctness_only'):
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
    if cfg['generation']['workflow']== 'source-translation':
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
            raise Failure('unsupported_configuration','This artifact supports structured generation, automatic semantic analysis and correctness repair. Legacy source_only/no-repair/fixed-profile ablations have not been ported; this configuration will not be silently ignored.')
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
        if testing and cfg['generation']['workflow']=='source-translation' and cfg['segmented']['development_performance']:
            from .performance_search import workloads
            fixed_inputs+= [x for x in workloads(case,cfg) if x not in fixed_inputs]
        random_inputs=scoped_inputs(case,cfg['testing']['random_cases'],seed,bits) if testing else []
        final_inputs=scoped_inputs(case,cfg['testing']['final_cases'],seed+1000003,bits) if testing and not cfg.get('translation',{}).get('correctness_only') else []
        if cfg['generation']['workflow']== 'source-translation' and testing and not cfg.get('translation',{}).get('correctness_only'):
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
        from .translation_workflow import search as run_search
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
        if cfg['generation']['workflow']=='source-translation':result['workflow_evidence']=selected.get('workflow_evidence',{})
        result['representation_decisions']=selected.get('decisions',[])
        loaded=selected['bundle'].get('loaded_adapter',{})
        result['binding_audit']={'theory':loaded.get('theory'),'audit':loaded.get('audit'),
            'bindings':loaded.get('bindings',{}),'numeric_representation_source':'Model-reported; inspect actual code and loaded bindings alongside this label.'}
        update({'phase':'delivery' if cfg.get('translation',{}).get('correctness_only') else 'final_evaluation'})
        if cfg.get('translation',{}).get('correctness_only'):
            result['final_evaluation']={'status':'removed','reason':'Correctness-only uses source tests and repairable reference differential checks; availability policy is explicit'}
        if refs and not cfg.get('translation',{}).get('correctness_only'):
            result['final']=check_suite(case,final_inputs,selected['binary'],refs,executor,cfg['testing']['process_timeout'],'final_generated_differential')
            result['final_kernel']=check_suite(case,final_inputs,selected['binary'],refs,executor,cfg['testing']['process_timeout'],'final_kernel_differential',arguments=('--i2r-benchmark',))
            for key in ['final','final_kernel']:
                if result[key]['status']!='passed':
                    add_regressions(work/'released-final-counterexamples.json',result[key]['counterexamples'])
                    raise Failure(key+'_failed','Held-out evaluation failed; not fed back into this run',result[key])
        shutil.copytree(selected['crate'],output,dirs_exist_ok=True,symlinks=False,ignore=shutil.ignore_patterns('target') if cfg['generation']['workflow']== 'source-translation' else None)
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
            for correction in rows[0].get('citation_protocol_attempts',[])+rows[0].get('inventory_protocol_attempts',[]):
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
