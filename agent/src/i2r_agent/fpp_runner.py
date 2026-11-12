"""One FPP controller: fresh source-first tasks, atomic budgets and resumable transport."""
import argparse, copy, fcntl, json, os, signal, subprocess, sys, time
from pathlib import Path
from .common import read, save, digest, Failure
from .task_context import fingerprint
from . import fpp_artifact as art, fpp_budget, provider, knowledge_run, baselines


def identity():
    files={}
    for root in [art.ROOT/'src',art.ROOT/'prompts',art.ROOT/'isabelle',art.ROOT/'skills',art.ROOT/'config',art.ARTIFACT]:
        for directory,dirs,names in os.walk(root):
            dirs[:]=[d for d in dirs if d not in {'runs','__pycache__','.venv','.git'}]
            for name in names:
                p=Path(directory)/name
                if p.name not in {'local.json','local.toml','.DS_Store'}:
                    files[str(p.relative_to(art.REPO))]=digest(p)
    return {'sha256':fingerprint(files),'files':files}

def release(run,rows,workers=None):
    path=run/'release.json'
    if workers is None:workers=read(path)['workers'] if path.exists() else 5
    if type(workers) is not int or workers<1:raise Failure('invalid_workers','workers must be a positive integer')
    core=identity();new={'identity':core['sha256'],'files':core['files'],'evaluation_order':[r['id'] for r in rows],'per_task_calls':48,'per_task_active_seconds':4200,'workers':workers,'global_limit':48*len(rows),'tool_sources':art.check_tools(),'effective_configs':{r['id']:art.configuration(r,run) for r in rows}}
    if path.exists():
        if read(path)!=new:raise Failure('release_changed','Frozen implementation/config/inputs/tools differ; do not mutate or silently restart this run')
    else:save(path,new)
    return new

def usage(diag):
    calls=[];known={k:0 for k in ['prompt_tokens','completion_tokens','total_tokens']};unknown=[];phases={}
    for p in sorted((diag/'model').glob('*/request.json')):
        response=read(p.parent/'response.json') if (p.parent/'response.json').exists() else None
        u=response.get('usage') if isinstance(response,dict) else None
        state=read(p.parent/'call-state.json') if (p.parent/'call-state.json').exists() else {}
        phase=state.get('phase','unknown');phases[phase]=phases.get(phase,0)+1
        if not isinstance(u,dict) or any(not isinstance(u.get(k),(float,int)) for k in known):unknown.append(str(p))
        if isinstance(u,dict):
            for k in known:
                if isinstance(u.get(k),(float,int)):known[k]+=u[k]
        calls.append({'request':str(p),'phase':phase,'usage':u})
    return {'calls':len(calls),'known_usage':known,'unknown_usage_requests':unknown,'call_records':calls,'phase_calls':phases}

def child(row,run,rel,boundary=False):
    art.install_execution(run);ad=art.admission(row,run);cfg=copy.deepcopy(ad['config']);task=run/'tasks'/row['id'];diag=task/'diagnostics';diag.mkdir(parents=True,exist_ok=True)
    cfg['preprocessing']['source_cache']={'path':ad['source_cache'],'sha256':ad['source_sha256']}
    cfg['testing']['observation_source']={'enabled':True,'artifact':ad['wrapper'],'sha256':ad['wrapper_sha256']}
    art.inputs(row);record=read(ad['baseline_record'])
    if digest(ad['baseline_record'])!=ad['baseline_sha256'] or not baselines.valid_record(record):raise Failure('baseline_changed',row['id'])
    def acquire(case,testing,bundle,conf,*args,**kwargs):
        if case!=row['id'] or baselines.identity(case,bundle,conf)!=record['identity']:raise Failure('baseline_identity_mismatch',case)
        return {**record,'acquisition':'strict_locked_read_only_cache'}
    baselines.acquire=acquire
    if boundary:
        def stop(self,system,prompt,*args,**kwargs):
            save(diag/'provider-boundary.json',{'phase':kwargs.get('phase','generation'),'fresh_analysis':not (diag/'prepared-program.json').exists(),'request_saved':False})
            raise Failure('provider_error','ZERO_API_PROVIDER_BOUNDARY')
        provider.Provider.call=stop
    else:fpp_budget.install(provider,run,rel)
    start=time.monotonic()
    result=knowledge_run.build(Path(ad['project']),task/'output',cfg,diagnostics=diag)
    cp=read(diag/'segmented-checkpoint.json') if (diag/'segmented-checkpoint.json').exists() else {}
    suites=cp.get('differential_suites',[])
    accepted=result.get('status')=='passed' and cp.get('support_evidence',{}).get('status')=='passed' and bool(suites) and all(r.get('status')=='passed' for r in suites)
    if accepted:
        from .source_failure_review import require_state
        require_state(cp,cfg,diag)
    out={'case':row['id'],'root':row['root'],'implementation_identity':rel['identity'],'seconds':time.monotonic()-start,'policy_accepted':accepted,'result':result,**usage(diag)}
    save(task/('boundary.json' if boundary else 'outcome.json'),out)

def transport(task,data):
    if data['result']['status'] not in {'provider_error','provider_protocol_error'}:return False
    paths=sorted((task/'diagnostics/model').glob('*/request.json'))
    if not paths or not (paths[-1].parent/'error.json').exists():return False
    e=read(paths[-1].parent/'error.json')
    return e.get('type') in {'URLError','IncompleteRead','RemoteDisconnected','ConnectionResetError','ConnectionRefusedError','TimeoutError','BadStatusLine','HTTPException','JSONDecodeError','ProviderProtocolError'} or e.get('http_status') in {408,429,500,502,503,504}

def retry(task):
    from .segmented_v8 import version
    diag=task/'diagnostics';path=diag/'segmented-checkpoint.json';stamp=str(time.time_ns())
    if path.exists():
        old=read(path);state=copy.deepcopy(old);attempts=state.get('attempts',[])
        requests=sorted((diag/'model').glob('*/request.json'))
        if attempts and requests and attempts[-1].get('development',{}).get('status') in {'provider_error','provider_protocol_error'}:
            last=attempts[-1];assert last['state_version']==last['after_version']==version(state)
            assert last['progress']['code_or_strategy_changed'] is False and last['progress']['phase_before']==last['progress']['phase_after']==state['phase']
            request=read(requests[-1]);event=fingerprint({'attempt':last['attempt'],'request':request})
            if event not in state.get('network_transport_resumes',[]):
                assert state.get('no_progress',0)>=1
                payload=json.loads(request['messages'][-1]['content']);state['no_progress']-=1
                state['feedback']=copy.deepcopy(payload.get('feedback',state.get('support_evidence') if state['phase'] in {'support','support_check','support_audit'} else None))
                state.setdefault('network_transport_resumes',[]).append(event)
            assert version(state)==version(old)
            save(task/('pre-retry-checkpoint-'+stamp+'.json'),old);save(path,state)
        ledger=diag/'semantic-check-ledger.json'
        if ledger.exists() and old.get('phase')=='support_check':
            seen=read(ledger);save(task/('pre-retry-semantic-ledger-'+stamp+'.json'),seen);save(ledger,{k:v for k,v in seen.items() if v.get('status')!='reserved'})
    (task/'outcome.json').rename(task/('transport-outcome-'+stamp+'.json'))

def report(run,rows):
    outcomes=[read(run/'tasks'/r['id']/'outcome.json') for r in rows if (run/'tasks'/r['id']/'outcome.json').exists()]
    accepted=sum(bool(r.get('policy_accepted')) for r in outcomes);account=[usage(run/'tasks'/r['id']/'diagnostics') for r in rows]
    result={'selected_roots':len(rows),'completed':len(outcomes),'accepted':accepted,'failed':len(outcomes)-accepted,'pending':len(rows)-len(outcomes),'accepted_over_all_roots':accepted/len(rows),'completed_acceptance_rate':accepted/len(outcomes) if outcomes else None,'first_complete_automatic_rate':accepted/len(rows) if len(outcomes)==len(rows) else None,'target':.95,'target_met':len(outcomes)==len(rows) and accepted/len(rows)>=.95,'includes_builtin_repairs':True,'requests':sum(r['calls'] for r in account),'known_usage':{k:sum(r['known_usage'][k] for r in account) for k in ['prompt_tokens','completion_tokens','total_tokens']},'unknown_usage_requests':sum(len(r['unknown_usage_requests']) for r in account),'failures':[{'case':r['case'],'status':r['result']['status']} for r in outcomes if not r.get('policy_accepted')]}
    save(run/'report.json',result);return result

def dispatch(run,rows,rel,resume=False):
    with (run/'controller.lock').open('a+') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stop=run/'STOP_DISPATCH'
        if stop.exists():
            if not resume:raise Failure('paused','Use explicit resume')
        pending=[r['id'] for r in rows if not (run/'tasks'/r['id']/'outcome.json').exists()];active={};errors=0;stop=run/'STOP_DISPATCH'
        for key in pending:
            marker=run/'tasks'/key/'process.json'
            if marker.exists() and read(marker).get('state')=='running':raise Failure('unreconciled_worker',key)
        if resume and stop.exists():stop.unlink()  # All admission/worker checks passed under lease.
        while pending or active:
            while pending and len(active)<rel['workers'] and not stop.exists():
                key=pending.pop(0);task=run/'tasks'/key;task.mkdir(parents=True,exist_ok=True)
                ad=art.admission(next(r for r in rows if r['id']==key),run);prior=ad['seconds']+sum(read(p)['seconds'] for p in task.glob('transport-outcome-*.json'))
                if prior>=4200 or usage(task/'diagnostics')['calls']>=48:
                    save(task/'outcome.json',{'case':key,'seconds':0,'policy_accepted':False,'result':{'status':'budget_exhausted'}});continue
                log=(task/'worker.log').open('a');child_env={**os.environ,'I2R_FPP_RELEASE':rel['identity'],'I2R_FPP_LEASE_FD':str(lease.fileno())};proc=subprocess.Popen([sys.executable,'-m','i2r_agent.fpp_runner','--run',str(run),'_child','--case',key],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lease.fileno(),),env=child_env);active[key]=(proc,log,time.monotonic(),prior)
                save(task/'process.json',{'state':'running','pid':proc.pid,'started_at':time.time()})
            for key,(proc,log,start,prior) in list(active.items()):
                elapsed=time.monotonic()-start;task=run/'tasks'/key
                if proc.poll() is None and elapsed+prior>4200:
                    try:os.killpg(proc.pid,signal.SIGKILL if elapsed+prior>4210 else signal.SIGTERM)
                    except ProcessLookupError:pass
                if proc.poll() is not None:
                    log.close();del active[key];save(task/'process.json',{'state':'finished','pid':proc.pid,'exit_code':proc.returncode});p=task/'outcome.json'
                    if not p.exists():save(p,{'case':key,'seconds':elapsed,'policy_accepted':False,'result':{'status':'time_budget_exhausted' if elapsed+prior>=4200 else 'worker_failed'}})
                    data=read(p);network=transport(task,data);errors=errors+1 if network else 0
                    if network:
                        retry(task);pending.insert(0,key)
                        if errors>=2:save(stop,{'reason':'two_consecutive_transport_errors'})
                    elif data['result']['status'] in {'worker_failed','internal_error','stale_source_cache','observation_source_changed','global_budget_identity_mismatch'}:save(stop,{'reason':'systemic_failure','case':key})
            save(run/'status.json',{'active':list(active),'pending':pending,'paused':stop.exists(),'reserved':len(read(run/'global-provider-budget.json')['reservations'])})
            if not active and stop.exists():break
            time.sleep(1)
    return report(run,rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('command',choices=['prepare','resume-prepare','run','pause','resume','report','boundary','_child']);p.add_argument('--case',action='append');p.add_argument('--workers',type=int,help='Concurrent task processes: default 5 for a new run; otherwise use the frozen release value');a=p.parse_args();run=a.run.resolve();run.mkdir(parents=True,exist_ok=True);allrows=art.manifest()['cases']
    if a.command=='pause':save(run/'STOP_DISPATCH',{'reason':'user_pause','policy':'drain active tasks'});return
    if a.command in {'prepare','resume-prepare'}:
        # Share dispatch's exclusive lease before selection/release initialization.
        with (run/'controller.lock').open('a+') as lease:
            fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return execute(a,run,allrows)
    return execute(a,run,allrows)

def execute(a,run,allrows):
    selection=run/'selection.json'
    if selection.exists():ids=read(selection)['ids']
    else:
        ids=a.case or [r['id'] for r in allrows]
        if not set(ids)<={r['id'] for r in allrows}:raise Failure('unknown_case',str(ids))
        save(selection,{'ids':ids})
    rows=[r for r in allrows if r['id'] in ids]
    if a.command=='report':print(json.dumps(report(run,rows),indent=2));return
    rel=release(run,rows,a.workers);fpp_budget.initialize(run,rel)
    if a.command in {'prepare','resume-prepare'}:
        stop=run/'STOP_DISPATCH'
        if stop.exists():
            if a.command!='resume-prepare':raise Failure('paused','Use resume-prepare for explicit same-version mechanical continuation')
            stop.unlink()  # Release/configuration was validated above, under lease.
        art.install_execution(run)
        def forbidden(*args,**kwargs):raise RuntimeError('Mechanical preparation forbids model calls')
        provider.Provider.call=forbidden
        for row in rows:
            if stop.exists():break  # Drain the current preparation; start no next task.
            ad=run/'preparation'/row['id']/'admission.json'
            if ad.exists():
                art.admission(row,run);continue
            if (ad.parent/'failure.json').exists():continue
            try:
                result=art.prepare(row,run)
                print(json.dumps({'case':row['id'],'status':result['status']}),flush=True)
            except Exception as error:
                result={'case':row['id'],'status':getattr(error,'code','preparation_exception'),'error':str(error),'evidence':getattr(error,'evidence',None),'model_calls':0}
                save(ad.parent/'failure.json',result)
                save(run/'tasks'/row['id']/'outcome.json',{'case':row['id'],'seconds':0,'policy_accepted':False,'result':result,'mechanical_failure':True})
                print(json.dumps(result),flush=True)
                if result['status'] in {'preparation_exception','missing_tool_repository','unreaped_isabelle_writer','isabelle_lock_timeout','isabelle_export_infrastructure_error'}:
                    save(run/'STOP_DISPATCH',{'reason':'mechanical_systemic_failure','case':row['id']});raise

        save(run/'preparation-status.json',{'paused':stop.exists(),'pending':[r['id'] for r in rows if not (run/'preparation'/r['id']/'admission.json').exists() and not (run/'preparation'/r['id']/'failure.json').exists()]})
        return
    if a.command in {'boundary','_child'}:
        if not a.case or len(a.case)!=1:raise Failure('case_required','Select one task')
        if a.command=='_child':
            if os.environ.get('I2R_FPP_RELEASE')!=rel['identity']:raise Failure('unleased_worker','Internal worker requires the active controller lease')
            os.fstat(int(os.environ['I2R_FPP_LEASE_FD']))
        row=next(r for r in rows if r['id']==a.case[0]);return child(row,run,rel,a.command=='boundary')
    if a.command=='run' and (run/'STOP_DISPATCH').exists():raise Failure('paused','Use explicit resume')
    for row in rows:
        if (run/'tasks'/row['id']/'outcome.json').exists():continue
        art.admission(row,run)
    print(json.dumps(dispatch(run,rows,rel,resume=a.command=='resume'),indent=2))

if __name__=='__main__':main()
