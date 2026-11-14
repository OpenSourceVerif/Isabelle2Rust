"""Portable, source-only dataset inputs and zero-model mechanical admission."""
import copy, json, os, shutil, subprocess, time
from pathlib import Path
from .common import ROOT, Failure, Executor, read, save, digest, merge, now
from . import tool_sources, knowledge_run, baselines, provider
from .task_context import fingerprint

REPO=ROOT.parent
ARTIFACT=REPO/'artifact'
RUSTLIGHTAST_COMMIT='1d25bd1ac5b406cfc08c4554ab9980ce5986db8f'

def manifest():
    dataset=os.environ.get('I2R_DATASET','fpp')
    if dataset not in {'fpp','unit','performance','performance-source'}:raise Failure('unknown_dataset',dataset)
    data=read(ARTIFACT/'datasets'/dataset/'manifest.json')
    if dataset=='fpp':
        assert len(data['cases'])==313 and len({r['root'] for r in data['cases']})==313
    elif dataset=='unit':
        assert len(data['cases'])==data['expected_root_count']==488
        assert len({(r['root'],r['original_source']) for r in data['cases']})==488
    else:
        assert len(data['cases'])==data['expected_root_count']
        assert len({r['id'] for r in data['cases']})==data['expected_root_count']
    for name,sha in data['corpus'].items():
        if digest(REPO/name)!=sha:raise Failure('corpus_changed',name)
    return data

def configuration(row,run):
    cfg=merge(read(ARTIFACT/'config.json'),row['config'])
    local=ARTIFACT/'local.json'
    if local.exists():cfg=merge(cfg,read(local))
    for key,env in [('isabelle','ISABELLE'),('afp','AFP_ROOT'),('cargo','CARGO'),('ocamlfind','OCAMLFIND')]:
        if os.environ.get(env):cfg['tools'][key]=os.environ[env]
    cfg['tools']['isabelle_heaps']=str(run/'heaps')
    cfg['tools']['optimizer_target']=str(run/'optimizer-target')
    cfg['budgets']['max_model_calls']=48
    cfg['testing']['observation_source']={'enabled':True}
    from .experiment_config import apply
    return apply(cfg, run)

def check_tools():
    root=tool_sources.repository('RustLightAST')
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if commit!=RUSTLIGHTAST_COMMIT:raise Failure('rustlightast_pin_mismatch',commit)
    if subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True).strip():
        raise Failure('rustlightast_dirty','Pinned RustLightAST must be clean')
    return tool_sources.manifest()

def install_execution(run):
    from . import heap_guard,session_context
    heap_guard.install(Executor,run/'heap-locks',Failure,save,now,ROOT)
    session_context.install(Executor,run)

def inputs(row):
    case=row['id'];values=row['inputs']
    assert values['ordinary_fixed']==values['kernel_fixed'] and values['ordinary_generated']==values['kernel_generated']
    def fixed(c):
        if c!=case:raise Failure('locked_input_case_mismatch',str(c))
        return values['ordinary_fixed']
    def generated(c,n,seed,bits):
        if c!=case or n!=len(values['ordinary_generated']):raise Failure('locked_input_case_mismatch',str((c,n)))
        return values['ordinary_generated']
    knowledge_run.fixed=fixed;knowledge_run.scoped_fixed=lambda c,bits:fixed(c);knowledge_run.scoped_inputs=generated

def project(row,run):
    if row.get('external_sources'):
        executable=configuration(row,run)['tools']['isabelle']
        home=Path(subprocess.check_output([executable,'getenv','-b','ISABELLE_HOME'],text=True).strip())
        for spec in row['external_sources']:
            if digest(home/spec['isabelle_path'])!=spec['sha256']:raise Failure('corpus_changed',spec['isabelle_path'])
    target=run/'projects'/row['id'];source=ARTIFACT/row['project']
    target.mkdir(parents=True,exist_ok=True)
    for name,sha in row['files'].items():
        p=source/name
        if digest(p)!=sha:raise Failure('project_changed',str(p))
        out=target/name;out.parent.mkdir(parents=True,exist_ok=True)
        if not out.exists():shutil.copyfile(p,out)
        if digest(out)!=sha:raise Failure('prepared_project_changed',str(out))
    for name,spec in row['source_mounts'].items():
        original=REPO/spec['path']
        if digest(original)!=spec['sha256']:raise Failure('corpus_changed',str(original))
        lines=original.read_text().splitlines(True)
        for a,b,replacement in reversed(spec['administrative_edits']):lines[a:b]=replacement
        out=target/name;out.parent.mkdir(parents=True,exist_ok=True)
        if not out.exists():out.write_text(''.join(lines))
        if digest(out)!=spec['derived_sha256']:raise Failure('derived_source_changed',str(out))
    return target

def prepare(row,run):
    from .source_input import preprocess
    from .validation import reference_outputs
    from .observation_source import verify
    work=run/'preparation'/row['id'];work.mkdir(parents=True,exist_ok=True)
    cfg=configuration(row,run);p=project(row,run);ex=Executor(work/'commands')
    def source(directory,where):
        cache=where/'program.json'
        if cache.exists():
            from .source_cache import load
            local=copy.deepcopy(cfg);local['preprocessing']['source_cache']={'path':str(cache),'sha256':digest(cache)}
            return load(directory,local)
        return preprocess(directory,cfg,where,ex)
    start=time.monotonic()
    bundle=source(p/'program',work/'source')
    if bundle['source_model']['entries']!=row.get('roots',[row['root']]):raise Failure('root_changed',row['id'])
    if sorted(bundle['source_model']['entities'])!=row['closure']:raise Failure('closure_changed',row['id'])
    wrapper=source(p/'testing',work/'wrapper')
    # Ownership is resolved by the unchanged core during execution.
    from .reference_repairs import numeric_domains
    proof=numeric_domains(bundle['source_model'],wrapper['source_model'])
    record=baselines.acquire(row['id'],p/'testing',knowledge_run.reference_bundle(p/'testing',bundle),cfg,work,ex,run/'baselines',numeric_proof=proof)
    refs=copy.deepcopy(record['references'])
    for ref in refs.values():ref.pop('outputs_path',None)
    suites={}
    for name,values in row['inputs'].items():
        if name not in {'ordinary_fixed','ordinary_generated','kernel_fixed','kernel_generated'}:continue
        checked=reference_outputs(row['id'],values,refs,ex,30,arguments=('--i2r-kernel-check',) if name.startswith('kernel') else ())
        save(work/(name+'.json'),checked);suites[name]=checked['selection']['status']
    if set(suites.values())!={'passed'}:raise Failure('reference_admission_failed',row['id'],suites)
    result={'id':row['id'],'status':'admitted','root':row['root'],'project':str(p),'source_cache':str(work/'source/program.json'),'source_sha256':digest(work/'source/program.json'),'wrapper':str(work/'wrapper/program.json'),'wrapper_sha256':digest(work/'wrapper/program.json'),'baseline_record':str(run/'baselines'/record['id']/'baseline.json'),'baseline_sha256':digest(run/'baselines'/record['id']/'baseline.json'),'config':cfg,'seconds':sum(read(p).get('seconds',0) for p in (work/'commands').glob('*.json')),'model_calls':0,'suites':suites}
    result['seal']=fingerprint(result)
    save(work/'admission.json',result);return result


def admission(row,run):
    path=run/'preparation'/row['id']/'admission.json'
    if not path.exists():raise Failure('not_prepared',row['id'])
    result=read(path)
    if result.get('seal')!=fingerprint({k:v for k,v in result.items() if k!='seal'}):raise Failure('admission_changed',row['id'])
    if result['config']!=configuration(row,run):raise Failure('admission_config_changed',row['id'])
    if result.get('preparation_import'):
        from .fpp_preparation_import import verify
        verify(row,run,result)
    elif Path(result['project'])!=project(row,run):raise Failure('admission_project_changed',row['id'])
    for field,hashfield in [('source_cache','source_sha256'),('wrapper','wrapper_sha256'),('baseline_record','baseline_sha256')]:
        if digest(result[field])!=result[hashfield]:raise Failure('admission_artifact_changed',field)
    return result
