"""Pipeline publication, lease/pause lifecycle, and explicit zero-call migration."""
import copy,json,os,subprocess,sys,time
from pathlib import Path
import pytest
from i2r_agent import fpp_runner as r,fpp_budget
from i2r_agent.common import save,read,Failure,digest
from i2r_agent.task_context import fingerprint


def migration_fixture(tmp_path,monkeypatch):
    rows=[{'id':'first'}]
    files={'agent/src/i2r_agent/fpp_runner.py':'before','artifact/README.md':'same','artifact/fpp-manifest.json':'fixed'}
    old={'identity':fingerprint(files),'files':files,'evaluation_order':['first'],'per_task_calls':48,'per_task_active_seconds':4200,'workers':10,'global_limit':48,'tool_sources':{'source':'unchanged'},'effective_configs':{'first':{'numeric_mode':'arbitrary'}}}
    new=copy.deepcopy(old);new['files']['agent/src/i2r_agent/fpp_runner.py']='after';new['identity']=fingerprint(new['files'])
    save(tmp_path/'release.json',old);fpp_budget.initialize(tmp_path,old);save(tmp_path/'STOP_DISPATCH',{'reason':'pause'})
    save(tmp_path/'preparation/first/admission.json',{'seconds':123.5,'source_sha256':'retained'})
    monkeypatch.setattr(r,'release_data',lambda run,rs,workers:new)
    monkeypatch.setattr(r.art,'admission',lambda row,run:read(run/'preparation'/row['id']/'admission.json'))
    return rows,old,new


def test_zero_model_migration_preserves_exact_snapshots_admissions_and_time(tmp_path,monkeypatch):
    rows,old,new=migration_fixture(tmp_path,monkeypatch)
    originals={p:p.read_bytes() for p in [tmp_path/'release.json',tmp_path/'global-provider-budget.json',tmp_path/'preparation/first/admission.json']}
    r.migrate_pipeline(tmp_path,rows,None,old['identity'])
    record=read(tmp_path/'scheduler-migration.json');archive=tmp_path/record['archive']
    assert (archive/'release-before.json').read_bytes()==originals[tmp_path/'release.json']
    assert (archive/'budget-before.json').read_bytes()==originals[tmp_path/'global-provider-budget.json']
    assert read(tmp_path/'release.json')==new
    assert read(tmp_path/'global-provider-budget.json')['reservations']==[]
    assert read(tmp_path/'global-provider-budget.json')['release_identity']==new['identity']
    assert (tmp_path/'preparation/first/admission.json').read_bytes()==originals[tmp_path/'preparation/first/admission.json']
    assert record['admissions']['first']['seconds']==123.5 and record['status']=='complete'
    assert (tmp_path/'STOP_DISPATCH').exists()
    r.migrate_pipeline(tmp_path,rows,None,old['identity'])  # Explicit retry remains idempotent before calls.


@pytest.mark.parametrize('change',['calls','request','checkpoint','config','tools','input_file','selection','workers','old_hash','expected_identity','unpaused','running_prepare','changed_admission'])
def test_migration_fails_closed_before_changes(tmp_path,monkeypatch,change):
    rows,old,new=migration_fixture(tmp_path,monkeypatch);expected=old['identity']
    if change=='calls':
        budget=read(tmp_path/'global-provider-budget.json');budget['reservations']=[{'case':'first'}];save(tmp_path/'global-provider-budget.json',budget)
    elif change=='request':save(tmp_path/'tasks/first/diagnostics/model/001/request.json',{})
    elif change=='checkpoint':save(tmp_path/'tasks/first/diagnostics/segmented-checkpoint.json',{})
    elif change=='config':new['effective_configs']['first']['numeric_mode']='checked'
    elif change=='tools':new['tool_sources']['source']='changed'
    elif change=='input_file':new['files']['artifact/fpp-manifest.json']='changed'
    elif change=='selection':new['evaluation_order']=['other']
    elif change=='workers':new['workers']=5
    elif change=='old_hash':
        broken=copy.deepcopy(old);broken['files']['artifact/fpp-manifest.json']='tampered';save(tmp_path/'release.json',broken)
    elif change=='expected_identity':expected='wrong'
    elif change=='unpaused':(tmp_path/'STOP_DISPATCH').unlink()
    elif change=='running_prepare':save(tmp_path/'preparation-process.json',{'state':'running'})
    elif change=='changed_admission':
        def invalid(*args):raise Failure('admission_artifact_changed','source cache')
        monkeypatch.setattr(r.art,'admission',invalid)
    before={p:p.read_bytes() for p in [tmp_path/'release.json',tmp_path/'global-provider-budget.json']}
    with pytest.raises(Failure):r.migrate_pipeline(tmp_path,rows,None,expected)
    assert all(p.read_bytes()==data for p,data in before.items())
    assert not (tmp_path/'scheduler-migration.json').exists()


def test_interrupted_migration_recovers_only_recorded_endpoints(tmp_path,monkeypatch):
    rows,old,new=migration_fixture(tmp_path,monkeypatch);original=r.save
    def interrupt(path,value):
        if Path(path)==tmp_path/'release.json':raise RuntimeError('interrupted after ledger write')
        original(path,value)
    with monkeypatch.context() as m:
        m.setattr(r,'save',interrupt)
        with pytest.raises(RuntimeError):r.migrate_pipeline(tmp_path,rows,None,old['identity'])
    assert read(tmp_path/'release.json')==old
    assert read(tmp_path/'global-provider-budget.json')['release_identity']==new['identity']
    r.migrate_pipeline(tmp_path,rows,None,old['identity'])
    assert read(tmp_path/'release.json')==new and read(tmp_path/'scheduler-migration.json')['status']=='complete'


def test_real_pipeline_dispatches_ready_then_drains_prepare_and_resumes(tmp_path):
    script=tmp_path/'fixture.py'
    script.write_text('''import sys,time,subprocess
from pathlib import Path
from i2r_agent import fpp_runner as r
from i2r_agent.common import save,read
r.art.manifest=lambda: {'cases':[{'id':'first'},{'id':'second'}]}
r.identity=lambda: {'sha256':'frozen','files':{}}
r.art.check_tools=lambda: {}
r.art.configuration=lambda row,run: {}
r.art.install_execution=lambda run: None
r.art.admission=lambda row,run: read(run/'preparation'/row['id']/'admission.json')
def prepare(row,run):
    assert row['id']=='second', 'Completed admission was rebuilt'
    try:r.provider.Provider.call(None,None,None)
    except RuntimeError:pass
    else:raise AssertionError('Preparation must prohibit model calls')
    unfinished=run/'preparation/second/admission.json.tmp'
    unfinished.parent.mkdir(parents=True,exist_ok=True);unfinished.write_text('{')
    (run/'second-preparing').touch()
    until=time.monotonic()+20
    while not (run/'finish-second').exists():
        if time.monotonic()>until:raise RuntimeError('test timeout')
        time.sleep(.02)
    result={'status':'admitted','seconds':7}
    save(run/'preparation/second/admission.json',result)
    return result
r.art.prepare=prepare
def child(row,run,rel,boundary=False):
    assert (run/'preparation'/row['id']/'admission.json').exists()
    save(run/'tasks'/row['id']/'outcome.json',{'case':row['id'],'seconds':0,'policy_accepted':True,'result':{'status':'passed'}})
r.child=child
original=subprocess.Popen
def launch(command,**kwargs):
    if command[1:3]==['-m','i2r_agent.fpp_runner']:command=[sys.executable,__file__]+command[3:]
    return original(command,**kwargs)
r.subprocess.Popen=launch
r.main()
''')
    run=tmp_path/'run';save(run/'preparation/first/admission.json',{'status':'admitted','seconds':123.5})
    original_admission=(run/'preparation/first/admission.json').read_bytes()
    command=[sys.executable,str(script),'--run',str(run)]
    proc=subprocess.Popen(command+['pipeline','--workers','10'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+10
        while time.monotonic()<deadline and proc.poll() is None and not ((run/'second-preparing').exists() and (run/'tasks/first/outcome.json').exists()):time.sleep(.02)
        assert (run/'second-preparing').exists() and (run/'tasks/first/outcome.json').exists()
        assert not (run/'preparation/second/admission.json').exists() and not (run/'tasks/second/process.json').exists()
        subprocess.run(command+['pause'],check=True,capture_output=True,timeout=10)
        conflict=subprocess.run(command+['resume-pipeline'],capture_output=True,text=True,timeout=10)
        assert conflict.returncode!=0 and 'BlockingIOError' in conflict.stderr and (run/'STOP_DISPATCH').exists()
        (run/'finish-second').touch();stdout,stderr=proc.communicate(timeout=15)
        assert proc.returncode==0,stderr
        assert not (run/'tasks/second/process.json').exists()
        assert read(run/'preparation-process.json')['state']=='finished'
        assert read(run/'status.json')['paused'] is True
        resumed=subprocess.run(command+['resume-pipeline'],capture_output=True,text=True,timeout=10)
        assert resumed.returncode==0,resumed.stderr
        assert read(run/'report.json')['accepted']==2
        assert read(run/'release.json')['workers']==10
        assert (run/'preparation/first/admission.json').read_bytes()==original_admission
        assert read(run/'global-provider-budget.json')['reservations']==[]
    finally:
        (run/'finish-second').touch()
        if proc.poll() is None:proc.communicate(timeout=25)


def test_preparation_systemic_failure_publishes_failure_and_pause(tmp_path,monkeypatch):
    monkeypatch.setattr(r.art,'install_execution',lambda run:None)
    monkeypatch.setattr(r.provider.Provider,'call',r.provider.Provider.call)  # Restore the child-only guard after this in-process test.
    def fail(row,run):raise Failure('missing_tool_repository','fixture missing tool')
    monkeypatch.setattr(r.art,'prepare',fail)
    with pytest.raises(Failure):r.prepare_rows(tmp_path,[{'id':'first'},{'id':'second'}])
    assert read(tmp_path/'STOP_DISPATCH')['reason']=='mechanical_systemic_failure'
    assert read(tmp_path/'tasks/first/outcome.json')['mechanical_failure']
    assert read(tmp_path/'preparation/first/failure.json')['model_calls']==0
    assert not (tmp_path/'preparation/second').exists()


def test_crashed_preparer_stops_dispatch_without_claiming_unprepared_success(tmp_path,monkeypatch):
    save(tmp_path/'preparation/first/admission.json',{'seconds':0})
    save(tmp_path/'global-provider-budget.json',{'reservations':[]})
    monkeypatch.setattr(r.art,'admission',lambda row,run:read(run/'preparation'/row['id']/'admission.json'))
    class Process:
        pid=123
        def __init__(self,code):self.returncode=code
        def poll(self):return self.returncode
    started=[]
    def launch(command,**kwargs):
        if command[-1]=='_prepare':return Process(1)
        key=command[-1];started.append(key)
        save(tmp_path/'tasks'/key/'outcome.json',{'case':key,'seconds':0,'policy_accepted':True,'result':{'status':'passed'}})
        return Process(0)
    monkeypatch.setattr(r.subprocess,'Popen',launch)
    result=r.dispatch(tmp_path,[{'id':'first'},{'id':'second'}],{'identity':'frozen','workers':10},pipeline=True)
    assert started==['first'] and result['pending']==1 and result['completed']==1
    assert read(tmp_path/'STOP_DISPATCH')['reason']=='preparation_worker_failed'
    assert read(tmp_path/'preparation-process.json')['state']=='finished'
