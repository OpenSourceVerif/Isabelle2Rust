from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from .common import ROOT,Executor,Failure,digest,now,read,save
from .generation import generate
from .preprocessing import preprocess
from .provider import Provider
from .references import prepare_references,compile_rust
from .suites import fixed,scoped_fixed,scoped_inputs,scoped_performance_input,input_bits,in_numeric_domain
from .validation import check_suite,add_regressions,reference_outputs
from .performance import benchmark
from .planning import prepare_plan, candidate_contract, require_generation_capabilities


def feedback_for(result):
    response=dict(result)
    if 'compilation' in response:
        response['compiler_diagnostics']={k:(Path(v['stdout']).read_text()+Path(v['stderr']).read_text())
            for k,v in response['compilation']['checks'].items()}
        # Repeat the first error at the end of long generation contexts. Keep
        # every diagnostic above: this highlight does not truncate the evidence.
        import re
        response['first_compiler_errors']={}
        for check,diagnostic in response['compiler_diagnostics'].items():
            match=re.search(r'^error(?:\[[^\]]+\])?:[^\n]*(?:\n(?!\s*$|error(?:\[|:)).*)*',diagnostic,re.MULTILINE)
            if match:response['first_compiler_errors'][check]=match.group(0)
    response['suites']=[{**s,'counterexamples':sorted(s.get('counterexamples',[]),key=lambda c:len(c['input']))[:5]}
                       for s in response.get('suites',[])]
    # Runtime log paths alone are not useful to a model without filesystem tools.
    # Include actual failure diagnostics, excluding only timing marker lines;
    # the complete original log remains on disk.
    response['runtime_diagnostics']=[]
    for suite in response['suites']:
        records=[('batch',suite.get('candidate',{}))]+[
            ('isolated_input',example.get('record',{})) for example in suite['counterexamples']]
        records += [('isolated_range_input',example.get('record',{})) for example in suite.get('range_event',{}).get('reproductions',[])]
        for kind,record in records:
            if record.get('status') in {None,'passed'}:continue
            path=record.get('stderr');message=Path(path).read_text() if path and Path(path).is_file() else ''
            response['runtime_diagnostics'].append({'suite':suite['kind'],'kind':kind,
                'status':record.get('status'),'returncode':record.get('returncode'),
                'stderr':'\n'.join(line for line in message.splitlines() if not line.startswith('I2R_KERNEL_NS ')),
                'original_record':record})
    response['repair_instruction']='Trace the smallest failing input through each source equation and candidate call. Preserve entire matched subtrees and aliases. Diagnose the mismatch, read missing source evidence and return concrete edits to the responsible implementation or connection. Compare actual changes and results; do not merely repeat the previous code.'
    return response


def search(bundle,case,cfg,provider,work,executor,references,fixed_inputs,random_inputs,regressions,update):
    from .generation import ownership_plans
    from .adapters import load_adapter
    from copy import deepcopy
    plans=ownership_plans(bundle,cfg,provider,work/'ownership')
    branches=[{'plan':p,'bundle':deepcopy(bundle),'previous':None,'feedback':None,'status':'active',
               'seen':{},'best':None,'attempts':[]} for p in plans]
    attempts=[];passed=[];number=0
    def report():
        update({'ownership_candidates':[{'plan':b['plan'],'status':b['status'],'attempts':b['attempts']} for b in branches],
                'attempts':attempts,'usage':provider.usage})
    while any(b['status']=='active' for b in branches) and provider.phase_calls['generation']<cfg['repair']['max_attempts']:
        for branch in branches:
            if branch['status']!='active' or provider.phase_calls['generation']>=cfg['repair']['max_attempts']:continue
            number+=1;attempt={'attempt':number,'ownership_candidate':branch['plan']['id'],'started_at':now()}
            attempts.append(attempt);branch['attempts'].append(number)
            update({'phase':'generation' if branch['previous'] is None else 'repair','attempts':attempts})
            current={**branch['bundle'],'ownership_plan':branch['plan']}
            try:
                generated=generate(current,cfg,provider,work/f'candidate-{number:02d}',branch['feedback'],branch['previous'])
                branch['previous']=generated['files']
                branch['bundle']['previous_contract']={k:generated[k] for k in ['mapping','adaptation_usage','ownership_changes','notes']}
                attempt.update(prompt=generated['prompt'],crate=generated['crate'])
                attempt['plan_contract']=candidate_contract(generated['translation_plan'],generated['files'],generated['mapping'],generated['adaptation_usage'],current)
                crate=Path(generated['crate']);compiled=compile_rust(crate,cfg,executor,candidate=True)
                attempt['compilation']=compiled;tests=[]
                if compiled['status']=='passed' and references:
                    update({'phase':'testing','attempts':attempts})
                    regression_inputs=[x['input'] for x in read(regressions) if in_numeric_domain(x['input'],input_bits(cfg))] if regressions.exists() else []
                    specs=[]
                    if cfg['testing']['fixed']:specs.append(('fixed',fixed_inputs))
                    if cfg['testing']['regression']:specs.append(('regression',regression_inputs))
                    if cfg['testing']['differential']:specs.append(('generated_differential',random_inputs))
                    for name,data in specs:
                        if not data:continue
                        check=check_suite(case,data,compiled['binary'],references,executor,cfg['testing']['process_timeout'],name)
                        tests.append(check);add_regressions(regressions,check['counterexamples'])
                        if bundle.get('kernel'):
                            check=check_suite(case,data,compiled['binary'],references,executor,cfg['testing']['process_timeout'],'kernel_'+name,arguments=('--i2r-benchmark',))
                            tests.append(check);add_regressions(regressions,check['counterexamples'])
                state=compiled['status'] if compiled['status']!='passed' else next((t['status'] for t in tests if t['status']!='passed'),'passed')
                development={'status':state,'count':sum(t['count'] for t in tests),
                    'failures':None if any(t['failures'] is None for t in tests) else sum(t['failures'] for t in tests),
                    'compilation':compiled,'suites':tests,'behavior_checked':bool(tests)}
                attempt['development']=development
                rank=(1 if compiled['status']=='passed' else 0,-(development['failures'] if development['failures'] is not None else 10**9))
                if branch['best'] is None or rank>branch['best']['rank']:
                    branch['best']={'rank':rank,'files':deepcopy(generated['files']),'contract':deepcopy(branch['bundle']['previous_contract']),
                        'feedback':feedback_for(development),'attempt':number}
                if state=='passed':
                    branch['status']='passed';passed.append({'id':branch['plan']['id'],'crate':crate,'binary':compiled['binary'],'attempt':number})
                else:
                    branch['feedback']=feedback_for(development)
                    key=hashlib.sha256(json.dumps(generated['files'],sort_keys=True).encode()).hexdigest()
                    count=branch['seen'].get(key,0)+1;branch['seen'][key]=count
                    if count>=2:
                        branch['feedback']['stagnation']={'identical_candidate_count':count,'instruction':'The same source has failed repeatedly. Give a different concrete fix. Read the assembled namespace; changing an import path does not remove a duplicate binding.'}
                    if count>=cfg['repair'].get('identical_failure_limit',3):
                        branch['status']='stalled';attempt['incident']='Identical candidate reached configured stagnation limit; preserve best version and stop this branch.'
                    elif branch['best']['rank']>rank:
                        branch['previous']=deepcopy(branch['best']['files']);branch['bundle']['previous_contract']=deepcopy(branch['best']['contract'])
                        branch['feedback']=deepcopy(branch['best']['feedback']);branch['feedback']['regression_recovery']='Returned to the previous better candidate; fix its remaining defect without reintroducing the later compilation regression.'
            except Failure as error:
                if error.code in {'budget_exhausted','provider_error','context_budget_exceeded'}:raise
                if error.code in {'adapter_revision_requested','ownership_adapter_requested'}:
                    try:
                        old=branch['bundle'];plan=error.evidence
                        if error.code=='ownership_adapter_requested':
                            if plan['numeric_mode']!=old['translation_plan']['numeric_mode'] or any(plan['adaptation'][k]!=old['translation_plan']['adaptation'][k] for k in ['numeric','sequence']):
                                raise Failure('ownership_scope_changed','Ownership revision cannot change numeric/collection selection')
                            loaded=load_adapter(plan,old,cfg,work/f'ownership-adapter-{number:02d}',executor)
                            branch['bundle']={**old,'programs':[loaded['after_target']],'translation_plan':plan,'loaded_adapter':loaded}
                        else:
                            g0={**old,'programs':old.get('g0_programs',old['programs'])}
                            branch['bundle'],planning=prepare_plan(g0,cfg,provider,work/f'adapter-repair-{number:02d}',executor,previous_plan=plan,initial_feedback=[{'message':str(error)}])
                            attempt['adapter_repair']=planning
                        branch['feedback']={'status':'adapter_reloaded','message':'Generate consistently with updated bindings.'}
                        branch['previous']=None;attempt['development']={'status':'adapter_reloaded'}
                    except Failure as revised:
                        if revised.code in {'budget_exhausted','provider_error'}:raise
                        branch['feedback']={'status':revised.code,'message':str(revised),'evidence':revised.evidence}
                        attempt['development']=branch['feedback']
                else:
                    branch['feedback']={'status':error.code,'message':str(error),'evidence':error.evidence}
                    attempt['development']=branch['feedback']
                    if error.code=='plan_contract_failed' and attempt.get('crate'):
                        # Contract repair may legitimately change only mapping,
                        # so do not compare Rust files alone on this path.
                        contract=branch['bundle'].get('previous_contract',{})
                        key='contract:'+hashlib.sha256(json.dumps({
                            'files':branch['previous'],'mapping':contract.get('mapping'),
                            'adaptation_usage':contract.get('adaptation_usage'),
                            'error':error.evidence},sort_keys=True).encode()).hexdigest()
                        count=branch['seen'].get(key,0)+1;branch['seen'][key]=count
                        if count>=cfg['repair'].get('identical_failure_limit',3):
                            branch['status']='stalled'
                            attempt['incident']='Identical code and interface mapping reached the configured stagnation limit.'
            save(work/f'attempt-{number:02d}.json',attempt);report()
            if not cfg['repair']['enabled'] and branch['status']=='active':branch['status']='not_repaired'
    for b in branches:
        if b['status']=='active':b['status']='budget_exhausted'
    report()
    # All survivors face the union of regression inputs found by every branch.
    survivors=[]
    for item in passed:
        reg=[x['input'] for x in read(regressions)] if regressions.exists() else []
        checks=[]
        if reg and references:
            for name,args in [('selection_regression',()),('selection_kernel_regression',('--i2r-benchmark',))]:
                if args and not bundle.get('kernel'):continue
                checks.append(check_suite(case,reg,item['binary'],references,executor,cfg['testing']['process_timeout'],name,arguments=args))
        save(item['crate']/'selection-regression.json',checks)
        if all(c['status']=='passed' for c in checks):survivors.append(item)
    if not survivors:return attempts,None,None
    selection={'candidates':[{**x,'crate':str(x['crate'])} for x in survivors],'criterion':'first passing candidate'}
    chosen=survivors[0]
    if len(survivors)>1 and references and cfg['performance']['enabled'] and bundle.get('kernel'):
        workload=scoped_performance_input(case,input_bits(cfg))
        expected=reference_outputs(case,[workload],references,executor,cfg['testing']['process_timeout'])['ocaml']['outputs'][0]
        measurement=benchmark({x['id']:x['binary'] for x in survivors},workload,expected,cfg,executor,work/'ownership-selection')
        chosen=min(survivors,key=lambda x:measurement['summary'][x['id']]['median_ns'])
        selection.update(criterion='minimum median kernel time on declared development workload; final tests unused',performance=measurement)
    selection['selected']=chosen['id'];selection['selected_attempt']=chosen['attempt']
    save(work/'ownership-selection.json',selection);update({'ownership_selection':selection,'selected_attempt':chosen['attempt']})
    return attempts,chosen['crate'],chosen['binary']


def build(project,output,cfg,diagnostics=None,regression_seed=None,progress=None,baseline_store=None):
    workflow=cfg.get('generation',{}).get('workflow')
    if workflow not in {None,'knowledge-v5','source-v6','segmented-v7','segmented-v8'}:
        raise Failure('unknown_workflow',str(workflow))
    if workflow in {'segmented-v7','segmented-v8'}:
        from .segmented_config import configure
        cfg=configure(cfg)
    if cfg.get('generation',{}).get('workflow') in {'knowledge-v5','source-v6','segmented-v7','segmented-v8'}:
        from .knowledge_run import build as build_knowledge
        return build_knowledge(project,output,cfg,diagnostics,regression_seed,progress,baseline_store)
    project,output=Path(project).resolve(),Path(output).resolve()
    if output.exists() and any(output.iterdir()):raise Failure('output_exists',str(output))
    temporary=None
    if diagnostics:
        work=Path(diagnostics).resolve();work.mkdir(parents=True,exist_ok=True)
    else:
        temporary=tempfile.TemporaryDirectory(prefix='i2r-agent-');work=Path(temporary.name)
    result={'schema_version':1,'started_at':now(),'status':'running','phase':'preprocessing','config':cfg,
            'attempts':[],'usage':{'total_tokens':0},'cost_usd':None,'source_optimization':{'status':'disabled'}}
    def update(change):
        result.update(change);save(work/'result.json',result)
        if progress:progress(result)
    executor=Executor(work/'commands');provider=Provider(cfg,work/'model')
    if baseline_store:executor.shared_cargo_root=ROOT/'cache/cargo-shared'
    try:
        metadata=read(project/'case.json') if (project/'case.json').exists() else {}
        case=metadata.get('id');result['case']=case
        save(work/'effective-config.json',cfg)
        bundle=preprocess(project,cfg,work/'preprocessing',executor)
        result['tool_sources']=bundle['tool_sources']
        result['program_summary']=[{'entries':p['entries'],'nodes':len(p['nodes']),'sccs':len(p['sccs'])} for p in bundle['programs']]
        if cfg.get('preprocessing',{}).get('mode')=='auto':
            update({'phase':'migration_planning'})
            bundle,record=prepare_plan(bundle,cfg,provider,work/'planning',executor)
            update({'preprocessing':record,'usage':provider.usage})
            require_generation_capabilities(bundle['translation_plan'])
        update({'phase':'references'})
        baseline=None;references=None
        if case:
            from .baselines import acquire
            baseline=acquire(case,project,bundle,cfg,work,executor,baseline_store)
            references=baseline['references']
            result['baseline']={k:v for k,v in baseline.items() if k!='references'}
        result['references']=references
        regressions=work/'regressions.json'
        save(regressions,read(regression_seed) if regression_seed and Path(regression_seed).exists() else [])
        seed=cfg['testing']['seed']+int(hashlib.sha256((case or '').encode()).hexdigest()[:6],16)
        bits=input_bits(cfg)
        fixed_inputs=scoped_fixed(case,bits) if case else []
        random_inputs=scoped_inputs(case,cfg['testing']['random_cases'],seed,bits) if case else []
        final_inputs=scoped_inputs(case,cfg['testing']['final_cases'],seed+1000003,bits) if case else []
        result['experiment_input_domain']={'max_input_bits':bits or None,'scope':'observation input values; not intermediate/output bounds',
            'fixed_outside_domain':[x for x in fixed(case) if not in_numeric_domain(x,bits)] if case else [],
            'regressions_outside_domain':[x for x in read(regressions) if not in_numeric_domain(x['input'],bits)]}
        save(work/'input-domain.json',result['experiment_input_domain'])
        dev_set={tuple(x) for x in fixed_inputs+random_inputs};final_set={tuple(x) for x in final_inputs}
        result['input_statistics']={'development_requests':len(fixed_inputs)+len(random_inputs),
            'development_unique':len(dev_set),'final_requests':len(final_inputs),'final_unique':len(final_set),
            'development_final_overlap':len(dev_set & final_set),'final_feedback_to_current_run':False}
        save(work/'development-inputs.json',{'fixed':fixed_inputs,'generated':random_inputs})
        # This file is never included in the provider context.
        save(work/'final-inputs.json',final_inputs)
        if references:
            reference_outputs(case,fixed_inputs+random_inputs,references,executor,cfg['testing']['process_timeout'])
        attempts,crate,binary=search(bundle,case,cfg,provider,work,executor,references,fixed_inputs,random_inputs,regressions,update)
        result['attempts']=attempts
        if crate is None:
            update({'status':'attempt_budget_exhausted','phase':'finished'});return result
        result.setdefault('selected_attempt',len(attempts))
        if cfg['source_optimization']['enabled']:
            if not references or not cfg['performance']['enabled']:
                raise Failure('missing_optimization_inputs','Source optimization requires behavior and performance inputs')
            from .source_optimization import optimize
            crate,binary,record=optimize(project,bundle,case,crate,binary,cfg,provider,work,executor,references,
                                        fixed_inputs,random_inputs,regressions,update)
            result['source_optimization']=record
        update({'phase':'final_evaluation'})
        if references:
            final=check_suite(case,final_inputs,binary,references,executor,cfg['testing']['process_timeout'],'final_generated_differential')
            result['final']=final
            if bundle.get('kernel'):
                result['final_kernel']=check_suite(case,final_inputs,binary,references,executor,cfg['testing']['process_timeout'],'final_kernel_differential',arguments=('--i2r-benchmark',))
                if result['final_kernel']['status']!='passed':
                    save(work/'released-final-counterexamples.json',result['final_kernel']['counterexamples'])
                    update({'status':'final_kernel_failed','phase':'finished'});return result
            # Published after selection: available only for future runs, never this run's repair.
            save(work/'released-final-counterexamples.json',final['counterexamples'])
            if final['status']!='passed':
                update({'status':'final_failed','phase':'finished'});return result
        else:result['final']={'status':'not_run','reason':'No observation bindings supplied'}
        if references and cfg['performance']['enabled']:
            update({'phase':'performance'})
            workload=scoped_performance_input(case,input_bits(cfg))
            expected=reference_outputs(case,[workload],references,executor,cfg['testing']['process_timeout'])['ocaml']['outputs'][0]
            from .baselines import measure_once
            fixed_measurement=measure_once(baseline,workload,expected,cfg,executor)
            result['baseline_measurement']=fixed_measurement
            result['performance']=benchmark({'candidate':binary},workload,expected,cfg,executor,work)
            result['performance']['baseline_reference']={'baseline_id':baseline['id'],'measurement':fixed_measurement['record_path'],
                'measured_at':fixed_measurement['measured_at'],'acquisition':fixed_measurement['acquisition']}
            save(work/'performance.json',result['performance'])
        from .tool_sources import verify
        verify(bundle['tool_sources'])
        output.mkdir(parents=True,exist_ok=True)
        extra_files=read(crate/'loaded-adapter.json')['support']['files'] if (crate/'loaded-adapter.json').exists() else {}
        for name in list(dict.fromkeys(['Cargo.toml','Cargo.lock','src','adapter','translation.json','migration-plan.json','plan-revision.json','loaded-adapter.json']+list(extra_files))):
            src=crate/name
            if baseline_store and name in {'adapter','loaded-adapter.json'} and src.exists():
                from .storage import link
                link(src,output/name)
            elif src.is_dir():shutil.copytree(src,output/name,dirs_exist_ok=True)
            elif src.exists():
                (output/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,output/name)
        if result['source_optimization'].get('status')=='accepted':
            shutil.copytree(Path(result['source_optimization']['project']),output/'hol')
        save(output/'tool-sources.json',bundle['tool_sources'])
        result['output']=str(output);result['code_sha256']=digest(output/'src/lib.rs')
        from .storage import artifact_files
        result['crate_files']={str(p.relative_to(output)):digest(p) for p in artifact_files(output)}
        save(output/'artifact-manifest.json',result['crate_files'])
        update({'status':'passed','phase':'finished'})
    except Failure as error:
        update({'status':error.code,'phase':'finished','error':str(error),'error_evidence':error.evidence})
    except KeyboardInterrupt:
        update({'status':'interrupted','phase':result['phase']});raise
    finally:
        result.update(finished_at=now(),usage=provider.usage,model_calls=provider.calls,model_calls_by_phase=provider.phase_calls)
        save(work/'result.json',result)
        if progress:progress(result)
        if temporary:temporary.cleanup()
    return result
