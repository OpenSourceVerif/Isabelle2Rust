"""Versioned reference artifacts, observation results, and one-time measurements.

This is an experimental baseline registry, not a learned adapter/asset library.
"""
from __future__ import annotations
import ast
import fcntl
import hashlib
import json
import platform
import shutil
from pathlib import Path

from .common import ROOT,Failure,digest,now,read,save
from . import tool_sources


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def language_artifacts(baseline_id,language,root=ROOT):
    """Keep optional backend builds beside the paired reference artifacts."""
    return Path(root)/'data/baselines'/baseline_id/'artifacts'/language


def language_results(language,root=ROOT):
    return sorted((Path(root)/'data/baselines').glob('*/artifacts/'+language+'/*/result.json'),
                  key=lambda p:(p.parent.name, p.parents[3].name))


def implementation_identity(root=ROOT):
    result={}
    for file,names in [('references.py',{'cargo','rust_driver','ocaml_driver','compile_rust','prepare_references'}),
                       ('preprocessing.py',{'project_info','build_project'})]:
        source=(Path(root)/'src/i2r_agent'/file).read_text()
        for node in ast.parse(source).body:
            if isinstance(node,ast.FunctionDef) and node.name in names:
                result[file+':'+node.name]=fingerprint(ast.dump(node,include_attributes=False))
    return result


def identity(case,bundle,cfg):
    result={'case':case,'sources':bundle['source_hashes'],'tools':cfg['tools'],
            'tool_sources':tool_sources.manifest(),
            'reference_implementation':implementation_identity(),
            'platform':{'system':platform.system(),'machine':platform.machine(),'release':platform.release()},
            'protocol':'decimal-natural-list-v1','timing_protocol':'kernel-v1',
            'timing_enabled':not cfg.get('translation',{}).get('correctness_only')}
    from .reference_policy import enabled,POLICY
    if enabled(cfg):
        result.update(reference_policy=POLICY,availability_recipe_sha256=digest(Path(__file__).with_name('available_references.py')),
                      reference_adapter_sha256=digest(Path(__file__).with_name('reference_repairs.py')))
        result['reference_numeric_profile']=cfg.get('testing',{}).get('reference_numeric_profile','bigint')
    return result


def valid_record(record):
    from .reference_policy import POLICY
    if record.get('identity',{}).get('reference_policy')==POLICY and set(record.get('references',{}))!={'ocaml','stage1','stage2'}:return False
    for r in record['references'].values():
        if r.get('status','passed')!='passed':
            if record.get('identity',{}).get('reference_policy')==POLICY and r.get('availability_policy')==POLICY and (r.get('failure') or r.get('checks')):continue
            return False
        if not all(k in r for k in ['binary','binary_sha256','source','sha256']):return False
        if not (Path(r['binary']).is_file() and digest(r['binary'])==r['binary_sha256'] and Path(r['source']).is_file() and digest(r['source'])==r['sha256']):return False
    return True


def existing_trial(key,cfg):
    """Adopt existing real artifacts without rebuilding or relabelling their age."""
    for study in sorted((ROOT/'data/runs').glob('*/study.json'),key=lambda p:read(p.parent/'summary.json').get('started_at',''),reverse=True):
        case=key['case'];directory=study.parent
        if not (directory/'inputs'/case).exists():continue
        try:
            if implementation_identity(directory/'implementation')!=key['reference_implementation']:continue
            if read(directory/'tool-sources.json')!=key['tool_sources']:continue
        except (OSError,ValueError):continue
        for path in sorted((directory/'trials').glob(case+'--*/result.json')):
            result=read(path);refs=result.get('references') or {}
            if set(refs)!={'ocaml','stage1','stage2'} or result.get('config',{}).get('tools')!=cfg['tools']:continue
            if any(r.get('timing_enabled',True)!=key['timing_enabled'] for r in refs.values()):continue
            bundle_path=path.parent/'diagnostics/preprocessing/program.json'
            if not bundle_path.exists() or read(bundle_path).get('source_hashes')!=key['sources']:continue
            if not all(Path(r['binary']).is_file() and Path(r['source']).is_file() and digest(r['source'])==r['sha256'] for r in refs.values()):continue
            return path,result
    return None,None


def acquire(case,project,bundle,cfg,work,executor,store=None,numeric_proof=None):
    from .references import prepare_references
    from .reference_policy import enabled,POLICY
    if enabled(cfg):
        from .available_references import prepare as prepare_references
    key=identity(case,bundle,cfg)
    if bundle.get('tool_sources') and bundle['tool_sources'] != key['tool_sources']:
        raise Failure('tool_sources_changed','Workspace tools changed since preprocessing')
    if store:
        for oldpath in Path(store).glob(case+'-*/baseline.json'):
            old=read(oldpath);oldkey=old.get('identity',{})
            if {k:v for k,v in oldkey.items() if k!='sources'}!={k:v for k,v in key.items() if k!='sources'}:continue
            if not all(oldkey.get('sources',{}).get(k)==v for k,v in key['sources'].items()):continue
            extra={k:v for k,v in oldkey.get('sources',{}).items() if k not in key['sources']}
            if not all(Path(k).is_absolute() and Path(k).is_file() and digest(k)==v for k,v in extra.items()):continue
            if valid_record(old):
                return {**old,'acquisition':'reused','reuse_note':'Only model-context source collection changed; all former additional source files remain identical.'}
    baseline_id=case+'-'+fingerprint(key)[:16]
    directory=Path(store or (Path(work)/'baseline'))/baseline_id;directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=directory/'baseline.json'
        if path.exists():
            record=read(path)
            if not valid_record(record):raise Failure('baseline_artifact_changed','Recorded baseline binary/source changed: '+str(path))
            record['acquisition']='reused'
            return record
        origin,result=existing_trial(key,cfg) if store and not enabled(cfg) else (None,None)
        if result:
            references=result['references'];acquisition='adopted_existing'
        else:
            references=prepare_references(project,cfg,directory/'build',executor,**({'numeric_proof':numeric_proof} if enabled(cfg) else {}));acquisition='built_once'
        if "tool_sources" in key:tool_sources.verify(key["tool_sources"])
        copied={}
        for name,ref in references.items():
            if enabled(cfg) and ref.get('status')!='passed':
                copied[name]={**ref,'baseline_id':baseline_id,'baseline_record':str(path)};continue
            target=directory/'artifacts'/name;target.mkdir(parents=True,exist_ok=True)
            executable=target/'reference';source=target/Path(ref['source']).name
            shutil.copy2(ref['binary'],executable);shutil.copy2(ref['source'],source)
            copied[name]={**ref,'binary':str(executable),'source':str(source),'sha256':digest(source),
                          'binary_sha256':digest(executable),'baseline_id':baseline_id,
                          'outputs_path':str(directory/'observations.json'),'baseline_record':str(path)}
        record={'id':baseline_id,'case':case,'created_at':now(),'identity':key,'references':copied,
                'acquisition':acquisition,'origin':str(origin) if origin else 'fresh reference build',
                'origin_finished_at':result.get('finished_at') if result else now()}
        save(path,record)
        if result:import_observations(directory,result,origin.parent/'diagnostics',case)
        return record


def import_observations(directory,result,diagnostics,case):
    """Only import exact paired outputs with successful records and properties."""
    from .suites import property_error
    suites=[];development=read(diagnostics/'development-inputs.json') if (diagnostics/'development-inputs.json').exists() else {}
    for attempt in result.get('attempts',[]):
        for check in attempt.get('development',{}).get('suites',[]):
            inputs=development.get('fixed' if check['kind']=='fixed' else 'generated') if check['kind'] in {'fixed','generated_differential'} else None
            if inputs is not None:suites.append((inputs,check))
    if result.get('final') and (diagnostics/'final-inputs.json').exists():suites.append((read(diagnostics/'final-inputs.json'),result['final']))
    observations={}
    for inputs,check in suites:
        refs=check.get('references',{});outputs={}
        try:
            for name in ['ocaml','stage2']:
                record=refs[name]
                if record.get('status')!='passed':raise ValueError('Reference did not pass')
                outputs[name]=[[int(v) for v in line.split()] for line in Path(record['stdout']).read_text().splitlines()]
                if len(outputs[name])!=len(inputs):raise ValueError('Incomplete reference output')
            for x,a,b in zip(inputs,outputs['ocaml'],outputs['stage2']):
                if a!=b or property_error(case,x,a):raise ValueError('Reference disagreement')
            for x,a in zip(inputs,outputs['ocaml']):observations[json.dumps(x,separators=(',',':'))]={'output':a,'origin':refs}
        except (OSError,KeyError,ValueError):continue
    save(directory/'observations.json',{'schema_version':1,'inputs':observations,'imported_at':now()})


def cached_outputs(case,inputs,references,executor,timeout):
    from .validation import execute
    from .suites import property_error
    path=Path(references['ocaml']['outputs_path'])
    with path.with_suffix('.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        stored=read(path) if path.exists() else {'schema_version':1,'inputs':{}}
        keys=[json.dumps(x,separators=(',',':')) for x in inputs]
        missing=list(dict.fromkeys(k for k in keys if k not in stored['inputs']))
        fresh={}
        if missing:
            values=[json.loads(k) for k in missing]
            fresh={k:execute(references[k]['binary'],values,executor,timeout) for k in ['ocaml','stage2']}
            for name,value in fresh.items():
                if value['status']!='passed':raise Failure('reference_runtime_failed',name,value)
            for key,x,a,b in zip(missing,values,fresh['ocaml']['outputs'],fresh['stage2']['outputs']):
                if a!=b:raise Failure('oracle_conflict','OCaml and Stage 2 disagree',{'input':x,'ocaml':a,'stage2':b})
                error=property_error(case,x,a)
                if error:raise Failure('oracle_property_conflict',error,{'input':x,'output':a})
            kernel_checks={}
            for name in ['ocaml','stage2']:
                if references[name].get('timing_protocol')=='kernel-v1':
                    checked=execute(references[name]['binary'],values,executor,timeout,arguments=(references[name].get('kernel_behavior_argument','--i2r-benchmark'),))
                    if checked['status']!='passed' or checked['outputs']!=fresh[name]['outputs']:
                        raise Failure('reference_kernel_mismatch','Reference kernel wrapper differs from its observer: '+name,checked)
                    kernel_checks[name]=checked['record']
            origin={name:r['record'] for name,r in fresh.items()}
            if kernel_checks:origin['kernel_checks']=kernel_checks
            for key,out in zip(missing,fresh['ocaml']['outputs']):stored['inputs'][key]={'output':out,'origin':origin}
            save(path,stored)
        return {name:{'status':'passed','outputs':[stored['inputs'][k]['output'] for k in keys],
                       'record':{'status':'passed','kind':'cached_reference_outputs','baseline_id':references[name]['baseline_id'],
                                 'source':str(path),'requested':len(inputs),'new_unique_inputs':len(missing),
                                 'reference_processes_started':int(bool(missing)),
                                 'new_execution':fresh.get(name,{}).get('record')}} for name in ['ocaml','stage2']}


def benchmark_key(workload,cfg):
    from .performance import benchmark
    import inspect
    return {'workload':workload,'options':cfg['performance'],'process_timeout':cfg['testing']['process_timeout'],
            'implementation':fingerprint(inspect.getsource(benchmark)),
            'kernel_timing_sources':({name:digest(ROOT/'src/i2r_agent'/name) for name in
                ['kernel_timing.py','kernel_build.py','kernel_benchmark.py','timing_drivers.py']}
                if cfg['performance'].get('protocol')=='kernel-v2' else {}),
            'host':{'node':platform.node(),'machine':platform.machine(),'release':platform.release()}}


def same_reference_sources(refs,other):
    return all(refs[k]['sha256']==other.get(k,{}).get('sha256') for k in ['ocaml','stage2'])


def measure_once(record,workload,expected,cfg,executor):
    from .performance import benchmark
    directory=Path(record['references']['ocaml']['baseline_record']).parent
    # Migrated artifacts may still point into a frozen study. New measurements
    # belong to the current registry, while the original executable stays put.
    registered=ROOT/'data/baselines'/record['id']/'baseline.json'
    if registered.exists() and same_reference_sources(record['references'],read(registered)['references']):
        directory=registered.parent
    key=benchmark_key(workload,cfg);path=directory/'measurements'/ (fingerprint(key)[:20]+'.json')
    path.parent.mkdir(exist_ok=True)
    with (directory/'measurement.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if path.exists():return {**read(path),'acquisition':'reused'}
        adopted=None
        # Select the most recent compatible real measurement, even when the
        # latest LLM trial itself stopped before reaching performance testing.
        studies=sorted((ROOT/'data/runs').glob('*/summary.json'),key=lambda p:read(p).get('started_at',''),reverse=True)
        for study in studies:
            for source in (study.parent/'trials').glob(record['case']+'--*/result.json'):
                result=read(source);perf=result.get('performance') or {}
                if perf.get('scope')!='kernel' or perf.get('protocol',{}).get('version')!=cfg['performance'].get('protocol','kernel-v1'):continue
                if perf.get('workload')!=workload or perf.get('protocol',{}).get('options')!=cfg['performance']:continue
                if not same_reference_sources(record['references'],result.get('references',{})):continue
                if result.get('config',{}).get('tools')!=cfg['tools']:continue
                if not {'ocaml','stage2'}<=set(perf.get('summary',{})):continue
                adopted={'scope':perf['scope'],'protocol':perf['protocol'],'workload':workload,
                         'summary':{k:perf['summary'][k] for k in ['ocaml','stage2']},
                         'raw_samples':[s for s in perf['raw_samples'] if s['implementation'] in {'ocaml','stage2'}],
                         'origin':str(source),'measured_at':result.get('finished_at'),'acquisition':'adopted_existing'}
                break
            if adopted:break
        if adopted is None:
            perf=benchmark({k:record['references'][k]['binary'] for k in ['ocaml','stage2']},workload,expected,cfg,executor,path.parent/path.stem)
            adopted={**perf,'origin':str(path.parent/path.stem/'performance.json'),'measured_at':now(),'acquisition':'measured_once'}
        adopted.update(id=path.stem,baseline_id=record['id'],identity=key,record_path=str(path))
        save(path,adopted);return adopted
