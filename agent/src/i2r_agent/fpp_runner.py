"""One FPP controller: fresh source-first tasks, atomic budgets and resumable transport."""
import argparse, copy, fcntl, json, os, signal, subprocess, sys, time
from pathlib import Path
from .common import read, save, digest, Failure
from .task_context import fingerprint
from . import fpp_artifact as art, fpp_budget, provider, knowledge_run, baselines


def identity():
    files={}
    for root in [art.ROOT/'src',art.ROOT/'prompts',art.ROOT/'isabelle',art.ROOT/'references',art.ROOT/'config',art.ARTIFACT]:
        for directory,dirs,names in os.walk(root):
            dirs[:]=[d for d in dirs if d not in {'runs','__pycache__','.venv','.git'}]
            for name in names:
                p=Path(directory)/name
                if p.name not in {'local.json','local.toml','.DS_Store'}:
                    files[str(p.relative_to(art.REPO))]=digest(p)
    return {'sha256':fingerprint(files),'files':files}

def release_data(run,rows,workers=None):
    path=run/'release.json'
    if workers is None:workers=read(path)['workers'] if path.exists() else 5
    if type(workers) is not int or workers<1:raise Failure('invalid_workers','workers must be a positive integer')
    core=identity();new={'identity':core['sha256'],'files':core['files'],'evaluation_order':[r['id'] for r in rows],'per_task_calls':48,'per_task_active_seconds':4200,'workers':workers,'global_limit':48*len(rows),'tool_sources':art.check_tools(),'effective_configs':{r['id']:art.configuration(r,run) for r in rows}}
    return new

def release(run,rows,workers=None):
    new=release_data(run,rows,workers);path=run/'release.json'
    if path.exists():
        if read(path)!=new:raise Failure('release_changed','Frozen implementation/config/inputs/tools differ; do not mutate or silently restart this run')
    else:save(path,new)
    return new

def migrate_pipeline(run,rows,workers,from_identity):
    """Explicit zero-model scheduler migration; controller lease is held by main.
    Retain byte-exact originals and a recoverable journal before changing either
    release or ledger. Admission/cache data is validated but never rewritten.
    """
    def reject(message):raise Failure('scheduler_migration_rejected',message)
    if not from_identity or not (run/'STOP_DISPATCH').exists():reject('Require --from-identity and a drained paused run')
    with (run/'global-provider-budget.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        release_path=run/'release.json';ledger_path=run/'global-provider-budget.json';journal=run/'scheduler-migration.json'
        live_release=read(release_path);live_ledger=read(ledger_path)
        record=read(journal) if journal.exists() else None
        if record:
            archive=run/record['archive']
            for name,sha in record['snapshot_sha256'].items():
                if digest(archive/name)!=sha:reject('Migration snapshot changed: '+name)
            old=read(archive/'release-before.json');old_ledger=read(archive/'budget-before.json')
        else:old=live_release;old_ledger=live_ledger
        if old['identity']!=from_identity or fingerprint(old['files'])!=from_identity:reject('Old release identity does not match its complete file inventory')
        new=release_data(run,rows,old['workers'] if workers is None else workers)
        allowed={'agent/src/i2r_agent/fpp_runner.py','artifact/README.md'}
        if set(old['files'])!=set(new['files']):reject('Release file inventory changed')
        changed={name for name,sha in old['files'].items() if new['files'][name]!=sha}
        if not changed or not changed<=allowed:reject('Only the runner and its README may change')
        if {k:v for k,v in old.items() if k not in {'identity','files'}}!={k:v for k,v in new.items() if k not in {'identity','files'}}:
            reject('Selection, configurations, tools, inputs, concurrency or budgets changed')
        expected={'release_identity':old['identity'],'prior_attempts':0,'limit':old['global_limit'],
                  'new_study_limit':old['global_limit'],'per_case_limit':old['per_task_calls'],
                  'allowed_cases':old['evaluation_order'],'reservations':[]}
        if old_ledger!=expected:reject('Migration requires the original empty provider ledger')
        new_ledger={**old_ledger,'release_identity':new['identity']}
        if live_release not in [old,new] or live_ledger not in [old_ledger,new_ledger]:reject('Live release or ledger is not a recorded migration endpoint')
        if list((run/'tasks').glob('*/diagnostics/model/*/request.json')):reject('Model requests already exist')
        for task in (run/'tasks').glob('*'):
            if not task.is_dir():continue
            if (task/'process.json').exists() or any((task/'diagnostics').rglob('*')):reject('Generation already started: '+task.name)
            if (task/'outcome.json').exists() and not read(task/'outcome.json').get('mechanical_failure'):reject('Nonmechanical outcome already exists')
        marker=run/'preparation-process.json'
        if marker.exists() and read(marker).get('state')=='running':reject('Unreconciled preparation process')
        admissions={}
        for row in rows:
            path=run/'preparation'/row['id']/'admission.json'
            if path.exists():
                ad=art.admission(row,run);admissions[row['id']]={'sha256':digest(path),'seconds':ad['seconds']}
        if record:
            if record['to_identity']!=new['identity'] or record['admissions']!=admissions:reject('Migration target or admissions changed')
            if read(archive/'release-after.json')!=new or read(archive/'budget-after.json')!=new_ledger:reject('Migration target snapshots changed')
        else:
            archive=run/'scheduler-migrations'/(old['identity']+'-to-'+new['identity']);archive.mkdir(parents=True,exist_ok=True)
            (archive/'release-before.json').write_bytes(release_path.read_bytes())
            (archive/'budget-before.json').write_bytes(ledger_path.read_bytes())
            save(archive/'release-after.json',new);save(archive/'budget-after.json',new_ledger)
            record={'status':'prepared','from_identity':old['identity'],'to_identity':new['identity'],
                    'archive':str(archive.relative_to(run)),'changed_files':sorted(changed),'admissions':admissions,
                    'snapshot_sha256':{name:digest(archive/name) for name in ['release-before.json','budget-before.json','release-after.json','budget-after.json']},
                    'model_calls':0,'policy':'zero-model scheduler-only migration; caches and charged preparation seconds retained'}
            save(journal,record)
        fpp_budget.atomic_save(ledger_path,new_ledger);save(release_path,new)
        save(journal,{**record,'status':'complete'})
        print(json.dumps({'status':'scheduler_migrated','admissions_preserved':len(admissions),'identity':new['identity'],'model_calls':0}),flush=True)


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
        from .fpp_preparation_import import baseline_config
        original_cfg=baseline_config(row,run,ad,conf)
        if case!=row['id'] or baselines.identity(case,bundle,original_cfg)!=record['identity']:raise Failure('baseline_identity_mismatch',case)
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
    from .translation_workflow import version
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


def prepare_rows(run,rows):
    stop=run/'STOP_DISPATCH'
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

def dispatch(run,rows,rel,resume=False,pipeline=False):
    with (run/'controller.lock').open('a+') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stop=run/'STOP_DISPATCH'
        if stop.exists():
            if not resume:raise Failure('paused','Use explicit resume')
        pending=[r['id'] for r in rows if not (run/'tasks'/r['id']/'outcome.json').exists()];active={};errors=0;stop=run/'STOP_DISPATCH'
        for key in pending:
            marker=run/'tasks'/key/'process.json'
            if marker.exists() and read(marker).get('state')=='running':raise Failure('unreconciled_worker',key)
        prep_marker=run/'preparation-process.json';preparer=None
        if prep_marker.exists() and read(prep_marker).get('state')=='running':raise Failure('unreconciled_preparer','Previous preparation child has not been reconciled')
        if pipeline:
            for row in rows:
                if (run/'preparation'/row['id']/'admission.json').exists():art.admission(row,run)
        if resume and stop.exists():stop.unlink()  # All admission/worker checks passed under lease.
        if pipeline and any(not (run/'preparation'/key/'admission.json').exists() for key in pending):
            log=(run/'prepare.log').open('a')
            env={**os.environ,'I2R_FPP_RELEASE':rel['identity'],'I2R_FPP_LEASE_FD':str(lease.fileno())}
            proc=subprocess.Popen([sys.executable,'-m','i2r_agent.fpp_runner','--run',str(run),'_prepare'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lease.fileno(),),env=env)
            preparer=(proc,log);save(prep_marker,{'state':'running','pid':proc.pid,'started_at':time.time()})
        while pending or active or preparer:
            # Admission/outcome JSON is atomically published only after a complete
            # preparation; never read or launch from a partial reference build.
            pending=[key for key in pending if not (run/'tasks'/key/'outcome.json').exists()]
            while pending and len(active)<rel['workers'] and not stop.exists():
                ready=[key for key in pending if not pipeline or (run/'preparation'/key/'admission.json').exists()]
                if not ready:break
                key=ready[0];task=run/'tasks'/key
                try:ad=art.admission(next(r for r in rows if r['id']==key),run)
                except Failure as error:
                    save(stop,{'reason':'admission_invalid','case':key,'error':error.code});break
                pending.remove(key);task.mkdir(parents=True,exist_ok=True)
                prior=ad['seconds']+sum(read(p)['seconds'] for p in task.glob('transport-outcome-*.json'))
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
            if preparer and preparer[0].poll() is not None:
                proc,log=preparer;log.close();preparer=None
                save(prep_marker,{'state':'finished','pid':proc.pid,'exit_code':proc.returncode})
                if proc.returncode!=0:save(stop,{'reason':'preparation_worker_failed','exit_code':proc.returncode})
            if pipeline and not preparer and not stop.exists() and any(not (run/'preparation'/key/'admission.json').exists() and not (run/'tasks'/key/'outcome.json').exists() for key in pending):
                save(stop,{'reason':'preparation_incomplete'})
            save(run/'status.json',{'active':list(active),'pending':pending,'preparing':preparer is not None,'paused':stop.exists(),'reserved':len(read(run/'global-provider-budget.json')['reservations'])})
            if not active and not preparer and stop.exists():break
            time.sleep(1)
    return report(run,rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=['fpp','unit','performance','performance-source'],default=os.environ.get('I2R_DATASET','fpp'));p.add_argument('--run',type=Path,required=True);p.add_argument('command',choices=['prepare','resume-prepare','run','pause','resume','report','boundary','_child','pipeline','resume-pipeline','_prepare','migrate-pipeline','import-preparation','measure','optimize']);p.add_argument('--case',action='append');p.add_argument('--from-run',type=Path,help='Read-only preparation or validated optimization baseline run');p.add_argument('--from-identity',help='Expected old frozen identity for scheduler migration or preparation import');p.add_argument('--workers',type=int,help='Concurrent task processes: default 5 for a new run; otherwise use the frozen release value')
    from .experiment_config import arguments
    arguments(p)
    a=p.parse_args();os.environ['I2R_DATASET']=a.dataset;run=a.run.resolve();run.mkdir(parents=True,exist_ok=True);allrows=art.manifest()['cases']
    if a.command=='pause':save(run/'STOP_DISPATCH',{'reason':'user_pause','policy':'drain active tasks'});return
    if a.command in {'prepare','resume-prepare','migrate-pipeline','import-preparation','measure','optimize'}:
        # Share dispatch's exclusive lease before selection/release initialization.
        with (run/'controller.lock').open('a+') as lease:
            fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return execute(a,run,allrows)
    return execute(a,run,allrows)

def execute(a,run,allrows):
    from .experiment_config import initialize
    initialize(run,a)
    selection=run/'selection.json'
    if a.command=='migrate-pipeline' and not selection.exists():raise Failure('scheduler_migration_rejected','An existing frozen selection is required')
    if selection.exists():
        ids=read(selection)['ids']
        if not set(ids)<={r['id'] for r in allrows}:raise Failure('dataset_selection_mismatch','Selected run belongs to another dataset')
    else:
        ids=a.case or [r['id'] for r in allrows]
        if not set(ids)<={r['id'] for r in allrows}:raise Failure('unknown_case',str(ids))
        save(selection,{'ids':ids})
    rows=[r for r in allrows if r['id'] in ids]
    if a.command=='report':
        result=read(run/'optimization-report.json') if (run/'optimization-report.json').exists() else report(run,rows)
        print(json.dumps(result,indent=2));return
    if a.command=='migrate-pipeline':return migrate_pipeline(run,rows,a.workers,a.from_identity)
    rel=release(run,rows,a.workers)
    if a.command=='optimize':
        result=optimize_selected(run,rows,rel,a.from_run)
        print(json.dumps({'mode':result['mode'],'complete':result['complete'],'improved':result['improved'],'selected':result['selected']},indent=2));return
    fpp_budget.initialize(run,rel)
    if a.command=='measure':
        from .numeric_experiment import measure_run
        print(json.dumps(measure_run(run,rows,rel),indent=2));return
    if a.command=='import-preparation':
        from .fpp_preparation_import import import_preparation
        if not a.from_run or not a.from_identity:raise Failure('preparation_import_rejected','Require --from-run and --from-identity')
        result=import_preparation(run,rows,rel,a.from_run,a.from_identity)
        print(json.dumps({'status':result['status'],'imported':len(result['imported']),'unprepared':len(result['unprepared']),'model_calls':0}),flush=True);return
    if a.command in {'prepare','resume-prepare'}:
        stop=run/'STOP_DISPATCH'
        if stop.exists():
            if a.command!='resume-prepare':raise Failure('paused','Use resume-prepare for explicit same-version mechanical continuation')
            stop.unlink()  # Release/configuration was validated above, under lease.
        return prepare_rows(run,rows)
    if a.command in {'_child','_prepare'}:
        if os.environ.get('I2R_FPP_RELEASE')!=rel['identity']:raise Failure('unleased_worker','Internal worker requires the active controller lease')
        os.fstat(int(os.environ['I2R_FPP_LEASE_FD']))
    if a.command=='_prepare':return prepare_rows(run,rows)
    if a.command in {'pipeline','resume-pipeline'}:
        result=dispatch(run,rows,rel,resume=a.command=='resume-pipeline',pipeline=True)
        print(json.dumps(result,indent=2))
        finish_optimization(run,rows,rel);return
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
    finish_optimization(run,rows,rel)


def optimize_selected(run,rows,rel,baseline=None):
    from .optimization import run as optimize
    selection=read(run/'experiment.json') if (run/'experiment.json').exists() else {}
    if selection.get('optimization','off')=='off':raise Failure('optimization_mode_required','Select --rust-only or --full')
    if any(not r.get('performance_workloads') for r in rows):
        raise Failure('performance_workloads_required','Use an admitted dataset with declared timing workloads')
    baseline=Path(baseline or run).resolve()
    if selection.get('numeric') is not None:
        from .experiment_baselines import resolve
        for row in rows:
            source=resolve(baseline,row['id'])
            prior=read(source/'experiment.json') if (source/'experiment.json').exists() else {}
            if prior.get('numeric')!=selection['numeric']:
                raise Failure('optimization_numeric_mismatch','Optimization inherits its baseline numeric configuration; no regeneration or numeric replacement')
    return optimize(baseline,run,rows,selection['optimization'],selection['optimization_limits'],rel)


def finish_optimization(run,rows,rel):
    selection=read(run/'experiment.json') if (run/'experiment.json').exists() else {}
    if selection.get('optimization','off')=='off':return
    if (run/'STOP_DISPATCH').exists():return
    # Run only accepted artifacts; failed correctness cases remain in the report.
    accepted=[r for r in rows if (run/'tasks'/r['id']/'outcome.json').exists() and read(run/'tasks'/r['id']/'outcome.json').get('policy_accepted')]
    if accepted:
        with (run/'controller.lock').open('a+') as lease:
            fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            optimize_selected(run,accepted,rel)

if __name__=='__main__':main()
