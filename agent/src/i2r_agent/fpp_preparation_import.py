"""Read-only reuse of mechanical inputs across an explicit source-test revision.

No model state or outcomes are imported. Original caches retain their project and
baseline identities. Only the two run-local build directories are rebound, after
all other effective configuration and preparation recipes match exactly.
"""
from copy import deepcopy
from pathlib import Path
import fcntl
from .common import Failure,read,save,digest
from .task_context import fingerprint
from . import fpp_artifact as art,baselines,source_cache,knowledge_run

POLICY='source-test-revision-read-only-preparation-v1'
REBOUND_TOOLS=('isabelle_heaps','optimizer_target')
# A reviewable boundary, not permission to ignore arbitrary implementation changes.
# Every other released byte (including extraction, wire and reference recipes,
# prompts, configuration and complete manifest) must match the original release.
PREPARATION_NEUTRAL_CHANGES={
 'agent/src/i2r_agent/'+name+'.py' for name in [
 'fpp_runner','fpp_artifact','fpp_preparation_import','segmented_support',
 'source_failure_review','segmented_test_audit','support_issue_lineage','source_resources','source_resource_revision',
 # Reviewed primitive contract / source-test responsibility changes. Mechanical
 # source_cache excludes semantic_analysis, segmentation and candidate state;
 # extraction, references, numeric configuration and tools still match exactly.
 'default_adaptations','native_numeric_contracts','translation_workflow',
 'source_suite_review','support_scope','test_obligations']}
PREPARATION_NEUTRAL_CHANGES.add('artifact/README.md')
SUITES=('ordinary_fixed','ordinary_generated','kernel_fixed','kernel_generated')


def reject(message,evidence=None):raise Failure('preparation_import_rejected',message,evidence)


def configuration(original,current):
    expected=deepcopy(original)
    rebound={}
    for key in REBOUND_TOOLS:
        if key not in original['tools'] or key not in current['tools']:reject('Missing explicit run-local tool path')
        expected['tools'][key]=current['tools'][key]
        rebound[key]={'from':original['tools'][key],'to':current['tools'][key]}
    if expected!=current:reject('Effective configuration differs beyond the two run-local build directories')
    return rebound


def releases(old,new,identity):
    if old.get('identity')!=identity or fingerprint(old.get('files'))!=identity:reject('Original release identity mismatch')
    if fingerprint(new.get('files'))!=new.get('identity'):reject('New release identity mismatch')
    changed={name for name in set(old['files'])|set(new['files']) if old['files'].get(name)!=new['files'].get(name)}
    if not changed<=PREPARATION_NEUTRAL_CHANGES:reject('A preparation-relevant release byte changed',sorted(changed-PREPARATION_NEUTRAL_CHANGES))
    if old['tool_sources']!=new['tool_sources']:reject('Tool sources changed')
    # A new run may select a subset for validation, never an unprepared identity.
    if not set(new['evaluation_order'])<=set(old['evaluation_order']):reject('New selection is outside the original selection')
    for key in ['per_task_calls','per_task_active_seconds']:
        if old[key]!=new[key]:reject('Per-case budget changed')
    return sorted(changed)


def project(row,path):
    """Validate existing bytes only; never repair an old project while importing."""
    for name,sha in row['files'].items():
        if digest(art.ARTIFACT/row['project']/name)!=sha or digest(path/name)!=sha:reject('Project input changed',name)
    for name,spec in row['source_mounts'].items():
        if digest(art.REPO/spec['path'])!=spec['sha256'] or digest(path/name)!=spec['derived_sha256']:reject('Source input changed',name)
    expected=set(row['files'])|set(row['source_mounts'])
    # Extra source files would alter source/cache resolution; build outputs are not inputs.
    actual={str(p.relative_to(path)) for p in path.rglob('*') if p.is_file() and p.suffix in {'.thy','.ML'}}
    if actual!={name for name in expected if Path(name).suffix in {'.thy','.ML'}}:reject('Prepared source inventory changed')


def validate_original(row,origin,old,new):
    path=origin/'preparation'/row['id']/'admission.json';ad=read(path)
    if ad.get('seal')!=fingerprint({k:v for k,v in ad.items() if k!='seal'}):reject('Original admission seal changed')
    if ad.get('preparation_import'):reject('Import only original mechanical admissions, not an import chain')
    if (ad.get('id'),ad.get('root'),ad.get('status'),ad.get('model_calls'))!=(row['id'],row['root'],'admitted',0):reject('Invalid original mechanical admission')
    if ad['config']!=old['effective_configs'][row['id']]:reject('Original config differs from its release')
    current=new['effective_configs'][row['id']];rebound=configuration(ad['config'],current)
    p=Path(ad['project'])
    if p!=origin/'projects'/row['id']:reject('Unexpected original project path')
    project(row,p)
    for field,hashfield in [('source_cache','source_sha256'),('wrapper','wrapper_sha256'),('baseline_record','baseline_sha256')]:
        if digest(ad[field])!=ad[hashfield]:reject('Original mechanical artifact changed',field)
    bundle=None
    for field,hashfield,subproject in [('source_cache','source_sha256','program'),('wrapper','wrapper_sha256','testing')]:
        cfg=deepcopy(current);cfg['preprocessing']['source_cache']={'path':ad[field],'sha256':ad[hashfield]}
        loaded=source_cache.load(p/subproject,cfg)
        if field=='source_cache':bundle=loaded
    if bundle['source_model']['entries']!=[row['root']] or sorted(bundle['source_model']['entities'])!=row['closure']:reject('Source root/closure changed')
    record=read(ad['baseline_record']);reference_bundle=knowledge_run.reference_bundle(p/'testing',bundle)
    if not baselines.valid_record(record) or baselines.identity(row['id'],reference_bundle,ad['config'])!=record['identity']:reject('Original baseline source/tool/recipe/binary identity differs')
    if ad['suites']!={name:'passed' for name in SUITES}:reject('Original input suites were not all admitted')
    receipts={}
    def logs(value):
        if isinstance(value,dict):
            for key,v in value.items():
                if key in {'stdout','stderr'} and isinstance(v,str):receipts[v]=digest(v)
                else:logs(v)
        elif isinstance(value,list):
            for v in value:logs(v)
    for name in SUITES:
        q=path.parent/(name+'.json');suite=read(q)
        if suite.get('selection',{}).get('status')!='passed':reject('Original reference input suite was not passed',name)
        receipts[str(q)]=digest(q);logs(suite)
    return ad,{'original_admission':str(path),'original_admission_sha256':digest(path),
               'rebound_tools':rebound,'reference_execution_artifacts':receipts}


def verify(row,run,ad):
    """Called from normal admission(), including the actual generation child."""
    provenance=ad['preparation_import']
    if provenance.get('policy')!=POLICY:reject('Unknown preparation import policy')
    origin=Path(provenance['origin_run']);oldpath=origin/'release.json'
    if digest(oldpath)!=provenance['origin_release_sha256']:reject('Original release changed')
    old=read(oldpath);new=read(run/'release.json')
    releases(old,new,provenance['origin_identity'])
    if provenance.get('new_identity')!=new['identity']:reject('Import target release changed')
    if digest(provenance['old_cost_snapshot'])!=provenance['old_cost_snapshot_sha256']:reject('Old cost snapshot changed')
    original,proof=validate_original(row,origin,old,new)
    if any(provenance.get(k)!=v for k,v in proof.items()):reject('Import provenance differs from its original receipts')
    expected={**original,'config':new['effective_configs'][row['id']],'preparation_import':provenance}
    expected.pop('seal');expected['seal']=fingerprint(expected)
    if expected!=ad:reject('Imported admission differs beyond recorded config path binding')
    return original


def baseline_config(row,run,ad,conf):
    if not ad.get('preparation_import'):return conf
    original=verify(row,run,ad)
    # knowledge_run adds these exact read-only artifacts before baseline acquisition.
    expected=deepcopy(ad['config'])
    expected['preprocessing']['source_cache']={'path':ad['source_cache'],'sha256':ad['source_sha256']}
    expected['testing']['observation_source']={'enabled':True,'artifact':ad['wrapper'],'sha256':ad['wrapper_sha256']}
    if expected['generation']['workflow']=='source-translation' and expected.get('translation',{}).get('correctness_only'):
        from .segmented_config import configure
        expected=configure(expected)
    if expected['testing'].get('transport')=='auto':
        expected['testing']['transport']='native-u128' if expected['preprocessing']['numeric_mode']=='checked' else 'dashu-ubig'
    if conf!=expected:reject('Child baseline configuration differs from the admitted cache binding')
    result=deepcopy(conf)
    for key in REBOUND_TOOLS:result['tools'][key]=original['config']['tools'][key]
    return result


def import_preparation(run,rows,new,origin,identity):
    """Controller lease for the new run is held by the CLI; take the old lease too."""
    origin=Path(origin).resolve()
    if origin==run or not (origin/'STOP_DISPATCH').is_file():reject('Require a distinct drained paused origin run')
    with (origin/'controller.lock').open('a+') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=read(origin/'release.json');changed=releases(old,new,identity)
        ledger=read(run/'global-provider-budget.json')
        if ledger.get('reservations') or ledger.get('prior_attempts')!=0:reject('Target must have no model calls')
        if any((run/'tasks').glob('*/diagnostics/*')) or any((run/'tasks').glob('*/outcome.json')):reject('Target already contains generation state')
        marker=origin/'preparation-process.json'
        if marker.exists() and read(marker).get('state')=='running':reject('Unreconciled original preparation process')
        archive=run/'preparation-import'/identity;archive.mkdir(parents=True,exist_ok=True)
        # Freeze the old cost separately. No old model cost/results enter the new ledger.
        for name in ['release.json','global-provider-budget.json']:
            target=archive/name;raw=(origin/name).read_bytes()
            if target.exists() and target.read_bytes()!=raw:reject('Original provenance snapshot changed',name)
            if not target.exists():target.write_bytes(raw)
        imported=[];unprepared=[]
        for row in rows:
            original_path=origin/'preparation'/row['id']/'admission.json'
            if not original_path.exists():unprepared.append(row['id']);continue
            original,proof=validate_original(row,origin,old,new)
            provenance={'policy':POLICY,'origin_run':str(origin),'origin_identity':identity,
              'origin_release_sha256':digest(origin/'release.json'),'new_identity':new['identity'],
              'old_cost_snapshot':str(archive/'global-provider-budget.json'),
              'old_cost_snapshot_sha256':digest(archive/'global-provider-budget.json'),
              'seconds_policy':'original mechanical seconds retained as conservative task budget charge; no mechanical work repeated',
              'fresh_model_state':True,**proof}
            ad={**original,'config':new['effective_configs'][row['id']],'preparation_import':provenance};ad.pop('seal');ad['seal']=fingerprint(ad)
            path=run/'preparation'/row['id']/'admission.json'
            if path.exists() and read(path)!=ad:reject('Target admission already differs',row['id'])
            if not path.exists():save(path,ad)
            imported.append({'id':row['id'],'seconds':ad['seconds'],'origin_admission_sha256':proof['original_admission_sha256']})
        result={'policy':POLICY,'status':'complete','origin_identity':identity,'new_identity':new['identity'],
                'changed_release_files':changed,'imported':imported,'unprepared':unprepared,'model_calls':0,
                'reused_preparation_seconds':sum(r['seconds'] for r in imported),'imported_model_results':0}
        save(run/'preparation-import.json',result);return result
