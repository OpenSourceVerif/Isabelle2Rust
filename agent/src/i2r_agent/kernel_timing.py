"""Persistent-process, verified batch timing protocol kernel-v2."""
from pathlib import Path
import contextlib,fcntl,json,math,os,platform,select,signal,statistics,subprocess,time
from .common import ROOT,Failure,now,read,save,digest,Executor,config
from .baselines import fingerprint,cached_outputs
from . import suites

DEFAULTS={'processes':5,'samples_per_process':10,'warmup_min_seconds':1.0,
          'warmup_max_seconds':10.0,'warmup_stability_ratio':1.15,'target_batch_ns':20000000,
          'max_batch':262144,'estimated_prepared_budget_bytes':134217728,'timeout_seconds':120,
          'max_clock_tick_ns':500,'min_batch_ticks':1000}


class Session:
    def __init__(self,binary,directory,timeout=120,deadline=None):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.stderr=(self.directory/'stderr.txt').open('w');self.log=(self.directory/'batches.jsonl').open('w')
        self.process=subprocess.Popen([str(binary),'--i2r-batch-v2'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=self.stderr,start_new_session=True,bufsize=0)
        self.buffer=b'';self.timeout=timeout;self.deadline=deadline;self.started_at=now();self.sequence=0
        try:
            line=self.line();parts=line.split()
            if len(parts)!=3 or parts[0]!='V2_CLOCK':raise Failure('timing_handshake',line)
            self.clock={'minimum_positive_ns':int(parts[1]),'startup_empty_ns':int(parts[2])}
            if not 0<self.clock['minimum_positive_ns']<=DEFAULTS['max_clock_tick_ns']:
                raise Failure('clock_resolution_insufficient',str(self.clock))
            save(self.directory/'process.json',{'command':[str(binary),'--i2r-batch-v2'],'pid':self.process.pid,
                                             'started_at':self.started_at,'clock':self.clock})
        except BaseException:self.close();raise
    def line(self):
        deadline=time.monotonic()+self.timeout
        if self.deadline is not None:deadline=min(deadline,self.deadline)
        while b'\n' not in self.buffer:
            if not select.select([self.process.stdout],[],[],max(0,deadline-time.monotonic()))[0]:
                raise Failure('optimization_time_exhausted' if self.deadline is not None and time.monotonic()>=self.deadline else 'timing_process_timeout',str(self.directory))
            chunk=os.read(self.process.stdout.fileno(),65536)
            if not chunk:raise Failure('timing_process_ended',str(self.directory)+': '+(self.directory/'stderr.txt').read_text()[-4000:])
            self.buffer+=chunk
        result,self.buffer=self.buffer.split(b'\n',1);return result.decode()
    def batch(self,n,workload,expected,phase):
        if self.deadline is not None and time.monotonic()>=self.deadline:
            raise Failure('optimization_time_exhausted',str(self.directory))
        wire=f'B {n}\n'+ ' '.join(map(str,workload))+'\n'+' '.join(map(str,expected))+'\n'
        self.process.stdin.write(wire.encode());self.process.stdin.flush()
        line=self.line();parts=line.split()
        if len(parts)!=3 or parts[0]!='V2' or int(parts[2])!=n:raise Failure('timing_protocol',line)
        elapsed=int(parts[1])
        if elapsed<0 or (phase=='sample' and n>0 and elapsed==0):raise Failure('timing_zero_or_negative',line)
        record={'sequence':self.sequence,'phase':phase,'batch_ns':elapsed,'iterations':n,
                'per_call_ns':elapsed/n if n else None,'output_checks':n}
        self.sequence+=1;self.log.write(json.dumps(record)+'\n');self.log.flush()
        return record
    def close(self):
        if getattr(self,'process',None):
            with contextlib.suppress(OSError):self.process.stdin.close()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):os.killpg(self.process.pid,signal.SIGTERM)
                try:self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    with contextlib.suppress(ProcessLookupError):os.killpg(self.process.pid,signal.SIGKILL)
                    self.process.wait()
            self.process.stdout.close()
        self.stderr.close();self.log.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def batch_cap(workload,options):
    # Conservative element-based preparation budget, plus a hard invocation cap.
    # This bounds requested retained inputs, not total runtime/VM RSS.
    estimate=1024+256*max(1,len(workload))+sum(max(1,x.bit_length()//8) for x in workload)*4
    return max(1,min(options['max_batch'],options['estimated_prepared_budget_bytes']//estimate))


def calibrate(session,workload,expected,options):
    cap=batch_cap(workload,options);n=1;records=[]
    while True:
        record=session.batch(n,workload,expected,'calibration');records.append(record)
        if record['batch_ns']>=options['target_batch_ns'] or n>=cap:break
        n=min(cap,max(n+1,min(n*8,math.ceil(n*options['target_batch_ns']/max(1,record['batch_ns'])))))
    return n,records,cap


def warmup(session,n,workload,expected,options):
    started=time.monotonic();records=[];stable=False
    while True:
        records.append(session.batch(n,workload,expected,'warmup'))
        elapsed=time.monotonic()-started
        if len(records)>=5:
            tail=[r['per_call_ns'] for r in records[-5:]]
            stable=min(tail)>0 and max(tail)/min(tail)<=options['warmup_stability_ratio']
        if elapsed>=options['warmup_min_seconds'] and stable:break
        if elapsed>=options['warmup_max_seconds']:break
    return {'stable':stable,'wall_seconds':time.monotonic()-started,'batches':len(records),
            'last_samples':[r['per_call_ns'] for r in records[-5:]]}


def summarize(processes):
    means=[statistics.median(p['samples']) for p in processes]
    samples=[s for p in processes for s in p['samples']]
    median=statistics.median(means)
    return {'median_ns':median,'min_ns':min(samples),'max_ns':max(samples),'samples':samples,
            'process_medians_ns':means,'process_min_ns':min(means),'process_max_ns':max(means),
            'mad_ns':statistics.median(abs(s-median) for s in means),'independent_processes':len(processes),
            'unstable_processes':sum(not p['warmup']['stable'] for p in processes)}


def process_order(builds,round_,design='rotating'):
    """Williams orders balance position and adjacent implementations.

    Even groups require n rounds; odd groups require 2*n. Legacy callers keep
    their original rotation unless the experiment explicitly opts in.
    """
    n=len(builds)
    if design=='rotating':return builds[round_%n:]+builds[:round_%n]
    if design!='williams':raise Failure('unknown_timing_order',design)
    sequence=[0];lo=1;hi=n-1
    while lo<=hi:
        sequence.append(lo);lo+=1
        if lo<=hi:sequence.append(hi);hi-=1
    if n%2 and (round_//n)%2:sequence.reverse()
    shift=round_%n
    return [builds[(i+shift)%n] for i in sequence]


def balanced_rounds(implementations,minimum=6):
    cycle=implementations if implementations%2==0 else 2*implementations
    return math.ceil(minimum/cycle)*cycle


def validate_build(build,cfg):
    work=Path(build['work']);path=work/'validation-v2.json'
    if path.exists():
        r=read(path)
        if r.get('binary_sha256')==digest(build['binary']):return r
    base=read(ROOT/'data/baselines'/build['baseline_id']/'baseline.json')
    original=read(build['source_record']);case=build['case']
    bits=128 if build['kind']=='llm' and 'checked' in build['id'] else 0
    seed=cfg['testing']['seed'];reg={}
    for p in (ROOT/'data/runs').glob('*/inputs/'+case+'/regressions.json'):
        for entry in read(p):
            x=entry['input']
            if suites.domain(case,x) and suites.in_numeric_domain(x,bits):reg[fingerprint(x)]=x
    groups={'fixed':suites.scoped_fixed(case,bits),'regression':list(reg.values()),
            'generated':suites.scoped_inputs(case,100,seed,bits),'final':suites.scoped_inputs(case,200,seed+1000003,bits)}
    ex=Executor(work/'validation-oracle');checks=[]
    with Session(build['binary'],work/'validation-process') as session:
        for name,inputs in groups.items():
            save(work/('validation-'+name+'-inputs.json'),inputs)
            expected=cached_outputs(case,inputs,base['references'],ex,15)['ocaml']['outputs']
            for x,y in zip(inputs,expected):session.batch(3 if name in ['fixed','regression'] else 1,x,y,'validation-'+name)
            checks.append({'suite':name,'inputs':len(inputs),'batch_size':3 if name in ['fixed','regression'] else 1,'status':'passed'})
    result={'status':'passed','binary_sha256':digest(build['binary']),'checks':checks,'checked_at':now()}
    save(path,result);return result


def measure_group(case,builds,workload,expected,options,casework):
    from .owned_process import assert_timing_ready
    assert_timing_ready()
    casework=Path(casework);casework.mkdir(parents=True,exist_ok=True)
    statepath=casework/'progress.json'
    identity={'protocol':'kernel-v2','options':{k:v for k,v in options.items() if k!='deadline_monotonic'},'workload':workload,'expected':expected,'controller':digest(__file__),
              'binaries':{b['id']:digest(b['binary']) for b in builds}}
    state=read(statepath) if statepath.exists() else {'identity':identity,'started_at':now(),'processes':{b['id']:[] for b in builds}}
    if state['identity']!=identity:raise Failure('timing_resume_identity_changed',str(statepath))
    completed=casework/'measurement-v2.json'
    if completed.exists():
        previous=read(completed)
        if previous.get('identity')==identity and previous.get('status')=='passed':
            return previous
    for round_ in range(options['processes']):
        order=process_order(builds,round_,options.get('order_design','rotating'))
        for b in order:
            if len(state['processes'][b['id']])>round_:continue
            print('MEASURE',case,b['id'],'process',round_+1,flush=True)
            directory=Path(b['work'])/('timing-process-'+str(round_+1))
            with Session(b['binary'],directory,options['timeout_seconds'],deadline=options.get('deadline_monotonic')) as session:
                empty=[session.batch(0,[],[],'empty')['batch_ns'] for _ in range(31)]
                n,calibration,cap=calibrate(session,workload,expected,options)
                warmed=warmup(session,n,workload,expected,options)
                # A fixed, preregistered extension for short batches; never
                # repeat based on whether the observed speedup is favorable.
                sample_count=options['samples_per_process']
                warm_batch=statistics.median(warmed['last_samples'])*n
                if min(calibration[-1]['batch_ns'],warm_batch)<options['min_batch_ticks']*session.clock['minimum_positive_ns']:
                    sample_count=max(sample_count,options.get('short_batch_samples',sample_count))
                records=[session.batch(n,workload,expected,'sample') for _ in range(sample_count)]
                warnings=[]
                if not warmed['stable']:warnings.append('warmup_not_stable')
                if min(r['batch_ns'] for r in records)<options['target_batch_ns']:warnings.append('batch_below_target_duration')
                if min(r['batch_ns'] for r in records)<options['min_batch_ticks']*session.clock['minimum_positive_ns']:warnings.append('batch_too_close_to_clock_resolution')
                process={'pid':session.process.pid,'started_at':session.started_at,'clock':session.clock,
                         'empty_batch_median_ns':statistics.median(empty),'batch_size':n,'batch_cap':cap,
                         'sample_count':sample_count,
                         'timer_probe_fraction':session.clock['minimum_positive_ns']/min(r['batch_ns'] for r in records),
                         'empty_batch_fraction':statistics.median(empty)/min(r['batch_ns'] for r in records),
                         'calibration':calibration,'warmup':warmed,'samples':[r['per_call_ns'] for r in records],
                         'raw_samples':records,'warnings':warnings,'evidence':str(directory)}
            state['processes'][b['id']].append(process);save(statepath,state)
    result={'case':case,'status':'passed','started_at':state['started_at'],'measured_at':now(),'scope':'kernel',
            'protocol':{'version':'kernel-v2','options':options,'boundary':'prepared independent inputs -> all kernel results fully computed and retained; encoding and checks after timer',
                        'timer':'high-resolution monotonic clock, self-tested per process; no overhead subtraction',
                        'order':options.get('order_design','rotating')+' implementations across independent processes; same-process warmup and samples',
                        'timer_probe':'Minimum positive elapsed timer self-test is an empirical overhead/resolution probe, not a proven hardware clock tick or error bound.',
                        'lifecycle':'inputs and output storage prepared before timing; kernel-intrinsic copies/allocations/drops and result storage remain timed',
                        'haskell':'NFData forcing of prepared inputs before timing and results inside timing; traversal cost included'},
            'workload':workload,'summary':{b['id']:summarize(state['processes'][b['id']]) for b in builds},
            'processes':state['processes'],'builds':builds,'identity':identity,
            'raw_samples':[{**r,'implementation':b['id'],'process':j,'warmup':False} for b in builds for j,p in enumerate(state['processes'][b['id']]) for r in p['raw_samples']]}
    save(casework/'measurement-v2.json',result)
    for b in builds:save(Path(b['work'])/'measurement-v2.json',{'case_measurement':str(casework/'measurement-v2.json'),'implementation':b['id'],'binary_sha256':digest(b['binary'])})
    return result
