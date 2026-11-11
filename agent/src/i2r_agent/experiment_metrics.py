"""Cost and first-attempt outcomes include failed tasks, grouped by frozen version."""
from collections import defaultdict
import math
from pathlib import Path
from .common import read


def summarize(work,result,identity,case,seconds):
    work=Path(work)
    latest=read(work/'diagnostics/result.json') if (work/'diagnostics/result.json').exists() else {}
    attempts=result.get('attempts') or latest.get('attempts',[])
    compilation=next((a['compilation']['status'] for a in attempts if a.get('compilation')),None)
    behavior=next((a['development']['status'] for a in attempts if a.get('development',{}).get('suites')),None)
    source=next((a['support']['status'] for a in attempts if a.get('support')),None)
    phases=defaultdict(float)
    for a in attempts:phases[a.get('action_phase','unknown')]+=a.get('resources',{}).get('seconds',0)
    provider_dirs=[p for p in (work/'diagnostics/model').glob('*') if p.is_dir() and p.name.isdigit()]
    usage=result.get('usage',latest.get('usage',{}))
    archived_usage=defaultdict(int)
    for directory in provider_dirs:
        if (directory/'metadata.json').exists():
            for key,value in read(directory/'metadata.json').get('usage',{}).items():
                if isinstance(value,(int,float)):archived_usage[key]+=value
    usage={key:max(usage.get(key,0),archived_usage.get(key,0)) for key in set(usage)|set(archived_usage)}
    return {'case':case,'status':result['status'],'seconds':seconds,
            'model_calls':max(result.get('model_calls',latest.get('model_calls',0)),max((int(p.name) for p in provider_dirs),default=0)),
            'usage':usage,
            'generation_success':result.get('generation_success',result['status']=='passed'),
            'source_test_success':result.get('source_test_success',result['status']=='passed'),
            'verified_end_to_end':result.get('verified_end_to_end',result['status']=='passed'),
            'differential_status':result.get('differential_status'),'reference_coverage':result.get('reference_coverage',[]),
            'reference_policy':result.get('reference_policy'),
            'phase_outcomes':{k:result.get(k) for k in ['generation','source_test_production','source_test_validation','differential','candidate_defect_status']},
            'first_compile':compilation,'first_behavior':behavior,'first_source_test':source,
            'phase_seconds':dict(phases),'frozen_identity':identity,
            'result':str(work/'result.json'),'cost_accounting':'Includes failed and timed-out tasks; interrupted provider usage may be unavailable.'}


def aggregate(rows):
    identities={r['frozen_identity'] for r in rows}
    if len(identities)>1:raise ValueError('Do not pool different frozen implementations')
    completed=len(rows);passed=sum(r['status']=='passed' for r in rows)
    times=sorted(r['seconds'] for r in rows)
    def percentile(q):return times[min(len(times)-1,max(0,math.ceil(len(times)*q)-1))] if times else None
    return {'frozen_identity':next(iter(identities),None),'completed':completed,'passed':passed,
            'not_verified_end_to_end':completed-passed,
            'generation_success':sum(r.get('generation_success',r['status']=='passed') for r in rows),
            'agent_generation_failed':sum(not r.get('generation_success',r['status']=='passed') for r in rows),
            'reference_unavailable':sum(r['status']=='generated_reference_unavailable' for r in rows),
            'failed':sum(not r.get('generation_success',r['status']=='passed') for r in rows),'pass_rate':passed/completed if completed else None,
            'model_calls_all_tasks':sum(r.get('model_calls') or 0 for r in rows),
            'tokens_all_tasks':sum((r.get('usage') or {}).get('total_tokens',0) for r in rows),
            'failed_task_tokens':sum((r.get('usage') or {}).get('total_tokens',0) for r in rows if r['status']!='passed'),
            'first_compile_passed':sum(r.get('first_compile')=='passed' for r in rows),
            'first_compile_attempted':sum(r.get('first_compile') is not None for r in rows),
            'first_behavior_passed':sum(r.get('first_behavior')=='passed' for r in rows),
            'first_behavior_attempted':sum(r.get('first_behavior') is not None for r in rows),
            'p50_seconds':percentile(.5),'p95_seconds':percentile(.95)}
