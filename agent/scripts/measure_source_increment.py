"""Measure a selected source stage against its own frozen Rust predecessor.

Only already selected, reviewed versions are used. This adds no model calls,
source edits, test generation or reference execution. The primary workload was
declared before search; final timing never changes either selected version.
"""
import argparse
from copy import deepcopy
import fcntl
from pathlib import Path
import shutil

from i2r_agent.common import ROOT, Executor, Failure, read, save, digest
from i2r_agent.task_context import fingerprint
from i2r_agent import numeric_experiment as numeric, numeric_interface as interface
from i2r_agent.optimization_matrix import selected
from i2r_agent.optimization_scope import choices
from i2r_agent.translation_workflow import version, connection, compile_crate
from i2r_agent.segmented_config import materialize
from i2r_agent.kernel_build import build
from i2r_agent.kernel_timing import DEFAULTS, measure_group


def prepare(full, row, directory):
    result=read(full/'optimization'/row['id']/'result.json')
    if not result['selected_source_optimized']:
        return None
    original,cfg,observations,_=numeric.freeze(result['baseline']['baseline_run'],row,directory/'baseline')
    after,_=selected(full,row['id'],original)
    proof=after['bundle']['source_equivalence']
    transition=next(a for a in result['attempts'] if a.get('status')=='source_proved'
                    and a['proof']['directory']==proof['directory'])
    predecessor=transition['parent_version']
    if predecessor==version(original):
        before=original;before_id=None
    else:
        candidate=next(c for c in choices(original,result['baseline'],result['attempts'])
                       if version(c['state'])==predecessor)
        review=read(full/'optimization'/row['id']/'scope-review/review.json')
        if not any(r['candidate_id']==candidate['id'] and r['decision']=='within_scope' for r in review['reviews']):
            raise Failure('source_predecessor_unapproved',row['id'])
        before=candidate['state'];before_id=candidate['id']
    workload=next(w for w in row['performance_workloads'] if w['id']==row['primary_workload'])
    states={'before':before,'after':after}
    intent={'case':row['id'],'workload':workload,'before_candidate':before_id,
            'after_candidate':result['scope_selection']['candidate'],
            'versions':{k:version(s) for k,s in states.items()},
            'source_graphs':{k:fingerprint(s['bundle']['source_model']) for k,s in states.items()},
            'source_proof':proof,'frozen_selection_sha256':digest(full/'optimization'/row['id']/'result.json'),
            'protocol':{**DEFAULTS,**cfg['performance'].get('v2',{}),'processes':6},
            'selection':'Declared primary input; predecessor immediately before the selected proved source transition versus its final accepted realization. No feedback to search.',
            'model_calls':0,'reference_executions':0,'controller_sha256':digest(__file__)}
    path=directory/'intent.json'
    if path.exists() and read(path)!=intent:raise Failure('source_increment_changed',row['id'])
    save(path,intent)
    for key,state in states.items():save(directory/(key+'-state.json'),state)
    return states,cfg,observations,intent


def measure(prepared,directory):
    states,cfg,observations,intent=prepared
    path=directory/'result.json'
    if path.exists():return read(path)
    cfg=deepcopy(cfg);cfg['translation']['correctness_only']=False
    builds=[];validation={};hashes={};locks={}
    for stage,state in states.items():
        hashes[stage]={}
        for backend in ['arbitrary','checked']:
            key=stage+'-'+backend;work=directory/'builds'/key
            rc=interface.backend_config(state['rust_config'],backend)
            crate=materialize(work/'candidate',state['files'],rc)
            harness=connection(crate,state['connector'],rc,cfg)
            master=directory/'builds/before-arbitrary/candidate/harness/Cargo.lock'
            if key!='before-arbitrary':shutil.copyfile(master,harness/'Cargo.lock')
            executor=Executor(work/'commands')
            compiled=compile_crate(harness,rc,cfg,executor,False)
            if compiled['status']!='passed':raise Failure('source_increment_compile_failed',key,compiled)
            validation[key]=[numeric.validate_lane(compiled['binary'],observations,lane,backend,executor,
                                                   cfg['testing']['process_timeout']) for lane in ['ordinary','kernel']]
            if any(intent['workload']['input'] in lane['range_exclusions'] for lane in validation[key]):
                raise Failure('source_increment_range_excluded',key)
            hashes[stage][backend]={'business':{n:digest(crate/n) for n in state['files']},
                                    'connector':{n:digest(harness/n) for n in state['connector']},
                                    'runtime':{n:digest(crate/n) for n in interface.managed_runtime(rc)}}
            locks[key]=digest(harness/'Cargo.lock')
            builds.append(build({'id':key,'case':intent['case'],'language':'rust','kind':'llm',
                                 'source':str(crate),'work':str(work/'timing')},cfg))
        if hashes[stage]['arbitrary']!=hashes[stage]['checked']:
            raise Failure('source_increment_numeric_source_changed',stage)
    if len(set(locks.values()))!=1:raise Failure('source_increment_dependencies_changed',intent['case'])
    save(directory/'validation.json',{'checks':validation,'source_pairs':hashes,'lock_hashes':locks})
    values=intent['workload']['input'];where=directory/'measurements'
    builds=[{**b,'work':str(where/b['id'])} for b in builds]
    measured=measure_group(intent['case'],builds,values,observations[('kernel',tuple(values))],intent['protocol'],where)
    rows=measured['summary'];ratios={}
    for backend in ['arbitrary','checked']:
        before,after=rows['before-'+backend],rows['after-'+backend]
        ratios[backend]={'speedup':before['median_ns']/after['median_ns'],'ci95':numeric.interval(before,after)}
    result={'case':intent['case'],'workload':intent['workload']['id'],'source_stage_speedups':ratios,
            'median_ns':{k:v['median_ns'] for k,v in rows.items()},'measurement':str(where/'measurement-v2.json'),
            'intent_sha256':digest(directory/'intent.json'),'model_calls':0,'reference_executions':0}
    save(path,result);return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--full',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--manifest',type=Path,default=ROOT.parent/'artifact/datasets/performance/manifest.json')
    args=parser.parse_args();full=args.full.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    pending=[]
    for row in read(args.manifest)['cases']:
        prepared=prepare(full,row,output/row['id'])
        if prepared:pending.append((prepared,output/row['id']))
    if args.prepare_only:
        print('Prepared',len(pending),'source-stage comparisons; no builds, measurements or model calls');return
    with (output/'controller.lock').open('a+') as controller,(ROOT/'cache/timing-v2.lock').open('a+') as timing:
        fcntl.flock(controller,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(timing,fcntl.LOCK_EX)
        results=[measure(prepared,where) for prepared,where in pending]
    save(output/'source-increment.json',{'complete':True,'results':results,'model_calls':0,'reference_executions':0})
    for r in results:print(r['case'],r['source_stage_speedups'])


if __name__=='__main__':main()
