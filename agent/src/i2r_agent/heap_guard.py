"""External execution guard; frozen core, commands and reference configuration stay unchanged."""
import fcntl,hashlib,json,os,signal,subprocess,time
from pathlib import Path


def heap_for(argv):
    argv=list(map(str,argv))
    if (len(argv)>8 and argv[1:4]==['env','bash','-c'] and argv[5]=='--'
            and argv[4]=='export ISABELLE_HEAPS="$1"; shift; exec "$@"'
            and argv[7]==argv[0] and argv[8]=='build'):
        return str(Path(argv[6]).resolve())
    return None


def install(Executor,lock_root,Failure,save,now,default_cwd):
    original=Executor.run;lock_root=Path(lock_root);lock_root.mkdir(parents=True,exist_ok=True)
    def run(self,argv,cwd=None,timeout=300,env=None,stdin=None,check=True):
        heap=heap_for(argv)
        if heap is None:return original(self,argv,cwd,timeout,env,stdin,check)
        self.sequence+=1;stem=self.directory/f'{self.sequence:04d}';started=time.monotonic()
        key=hashlib.sha256(heap.encode()).hexdigest();lock=lock_root/(key+'.lock');unreaped=lock_root/(key+'.unreaped.json')
        record={'command':list(map(str,argv)),'cwd':str(cwd or default_cwd),'started_at':now(),'timeout_seconds':timeout,
                'heap_lock':{'key':key,'heap':heap,'path':str(lock),'policy':'exclusive_same_resolved_heap_build_v1'},
                'stdout':str(stem.with_suffix('.stdout')),'stderr':str(stem.with_suffix('.stderr'))}
        with lock.open('a+') as lease:
            while True:
                if unreaped.exists():raise Failure('unreaped_isabelle_writer','Prior writer needs explicit exit verification',str(unreaped))
                try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()-started>=timeout:
                        record.update(status='isabelle_lock_timeout',seconds=time.monotonic()-started)
                        save(stem.with_suffix('.json'),record);raise Failure('isabelle_lock_timeout','Waiting for shared heap writer exceeded build budget',record)
                    time.sleep(.05)
            if unreaped.exists():raise Failure('unreaped_isabelle_writer','Prior writer needs explicit exit verification',str(unreaped))
            record['heap_lock'].update(acquired_at=now(),wait_seconds=time.monotonic()-started)
            process_env=dict(os.environ);process_env.update(env or {})
            interrupted=None
            with Path(record['stdout']).open('w') as out,Path(record['stderr']).open('w') as err:
                process=subprocess.Popen(record['command'],cwd=cwd or default_cwd,env=process_env,
                    stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,stdout=out,stderr=err,
                    start_new_session=True,text=True,pass_fds=(lease.fileno(),))
                self._guard_active_process=process
                record['pid']=process.pid;record['process_group']=process.pid
                try:
                    process.communicate(stdin,timeout=max(.01,timeout-(time.monotonic()-started)))
                    record.update(status='passed' if process.returncode==0 else 'failed',returncode=process.returncode)
                except (subprocess.TimeoutExpired,KeyboardInterrupt) as error:
                    interrupted=error;record['signals']=[]
                    for sig,delay in [(signal.SIGINT,10),(signal.SIGTERM,20)]:
                        if process.poll() is not None:break
                        try:os.killpg(process.pid,sig);record['signals'].append(sig.name)
                        except ProcessLookupError:break
                        try:process.wait(timeout=delay)
                        except subprocess.TimeoutExpired:pass
                    record.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'timeout',returncode=process.poll())
                    if process.poll() is None:
                        record['status']='unreaped_isabelle_writer';save(unreaped,record)
                        # Inherited lease and persistent blocker prevent a new build
                        # even if a still-running descendant closes inherited FDs.
            record['heap_lock']['released_at']=now();record['seconds']=time.monotonic()-started
            record['external_term_received']=getattr(self,'_guard_term_received',False)
            output=Path(record['stdout']).read_text()+Path(record['stderr']).read_text()
            if record['status']=='passed' and ('*** [SQLITE_' in output or '*** Consumer thread failure:' in output):
                record.update(status='isabelle_export_infrastructure_error',exit_zero_rejected=True)
            save(stem.with_suffix('.json'),record)
            if isinstance(interrupted,KeyboardInterrupt):raise interrupted
            if check and record['status']!='passed':raise Failure(record['status'] if record['status']!='failed' else 'tool_failed','Isabelle build/export failed',record)
            return record
    def guarded(self,argv,*args,**kwargs):
        if heap_for(argv) is None:return original(self,argv,*args,**kwargs)
        previous=signal.getsignal(signal.SIGTERM)
        self._guard_active_process=None;self._guard_term_received=False
        def terminate(signum,frame):
            self._guard_term_received=True
            process=self._guard_active_process
            if process is None:raise KeyboardInterrupt()
            if process.poll() is None:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        signal.signal(signal.SIGTERM,terminate)
        try:return run(self,argv,*args,**kwargs)
        finally:
            signal.signal(signal.SIGTERM,previous)
            self._guard_active_process=None
    Executor.run=guarded
    return original
