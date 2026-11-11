"""Verify a complete timing campaign, then atomically activate its UI manifest."""
from pathlib import Path
from .common import ROOT,Failure,read,save,digest,now,config
from .timing_v2_build import STORE,RUN_ID
from . import suites
from .baselines import benchmark_key,fingerprint
from .timing_v2 import DEFAULTS
from copy import deepcopy


def register_reference_measurements(measurements,cfg):
    """Reuse verified campaign data without changing its measurement timestamp."""
    paths=[]
    for source,m in measurements:
        paired={b['language']:b for b in m['builds'] if b['language'] in {'ocaml','stage2'}}
        if set(paired)!={'ocaml','stage2'}:raise Failure('timing_reference_pair_missing',m['case'])
        base_id=paired['ocaml']['baseline_id']
        if paired['stage2']['baseline_id']!=base_id:raise Failure('timing_reference_pair_changed',m['case'])
        names={b['id']:name for name,b in paired.items()}
        for include_bits in [True,False]:
            effective=deepcopy(cfg)
            if not include_bits:effective['performance'].pop('input_bits',None)
            key=benchmark_key(m['workload'],effective)
            path=ROOT/'data/baselines'/base_id/'measurements'/(fingerprint(key)[:20]+'.json')
            if path.exists():
                paths.append(str(path));continue
            record={'scope':m['scope'],'protocol':m['protocol'],'workload':m['workload'],
                    'summary':{name:m['summary'][b['id']] for name,b in paired.items()},
                    'processes':{name:m['processes'][b['id']] for name,b in paired.items()},
                    'raw_samples':[{**r,'implementation':names[r['implementation']]} for r in m['raw_samples'] if r['implementation'] in names],
                    'origin':str(source),'measured_at':m['measured_at'],'acquisition':'adopted_campaign',
                    'campaign_identity':m['identity'],'campaign_sha256':digest(source),
                    'id':path.stem,'baseline_id':base_id,'identity':key,'record_path':str(path)}
            save(path,record);paths.append(str(path))
    return paths


def publish(store=STORE):
    store=Path(store);inventory=read(store/'inventory.json');cfg=config();records=[];count=0;measurements=[]
    if cfg['performance'].get('protocol')!='kernel-v2':raise Failure('timing_default_not_enabled','Set the verified default before publishing')
    for case in dict.fromkeys(i['case'] for i in inventory):
        expected={i['id'] for i in inventory if i['case']==case}
        path=store/case/'measurement-v2.json';m=read(path)
        if m['status']!='passed' or m['protocol']['version']!='kernel-v2':raise Failure('timing_incomplete',case)
        if m['protocol']['options']!={**DEFAULTS,**cfg['performance'].get('v2',{}),'protocol':'kernel-v2'}:
            raise Failure('timing_options_changed',case)
        if set(m['summary'])!=expected:raise Failure('timing_implementations_missing',case)
        if m['workload']!=suites.scoped_performance_input(case,cfg['performance'].get('input_bits',128)):
            raise Failure('timing_workload_changed',case)
        for b in m['builds']:
            validation=read(Path(b['work'])/'validation-v2.json')
            if validation['status']!='passed' or validation['binary_sha256']!=digest(b['binary']):raise Failure('timing_validation_changed',b['id'])
            for group in ['source_hashes','artifact_hashes']:
                if not all(Path(p).is_file() and digest(p)==h for p,h in b[group].items()):raise Failure('timing_artifact_changed',b['id'])
            if digest(b['binary'])!=m['identity']['binaries'][b['id']]:raise Failure('timing_binary_changed',b['id'])
            processes=m['processes'][b['id']]
            options=m['protocol']['options']
            if len(processes)!=options['processes']:raise Failure('timing_processes_missing',b['id'])
            for p in processes:
                if len(p['samples'])!=options['samples_per_process']:raise Failure('timing_samples_missing',b['id'])
                if any(r['batch_ns']<=0 or r['output_checks']!=r['iterations'] for r in p['raw_samples']):raise Failure('timing_invalid_sample',b['id'])
            count+=1
        records.append({'case':case,'path':str(path),'sha256':digest(path)})
        measurements.append((path,m))
    manifest={'id':store.name,'protocol':'kernel-v2','status':'complete','published_at':now(),
              'implementation_count':count,'cases':records,'inventory':str(store/'inventory.json'),
              'reference_cache_records':register_reference_measurements(measurements,cfg)}
    save(store/'publication.json',manifest)
    save(store.parent/'active.json',manifest)
    return manifest

if __name__=='__main__':
    print(publish())
