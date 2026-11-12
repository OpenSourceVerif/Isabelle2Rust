"""The artifact controller drains active work and leaves pending tasks untouched."""
from i2r_agent import fpp_runner as runner
from i2r_agent.common import save,read
from i2r_agent.common import Failure
import pytest

def test_pause_prevents_next_dispatch(tmp_path,monkeypatch):
    rows=[{'id':'first'},{'id':'second'}]
    save(tmp_path/'global-provider-budget.json',{'reservations':[]})
    monkeypatch.setattr(runner.art,'admission',lambda row,run:{'seconds':0})
    started=[]
    class Process:
        pid=123;returncode=0
        def poll(self):return 0
    def launch(command,**kwargs):
        case=command[-1];started.append(case)
        save(tmp_path/'tasks'/case/'outcome.json',{'case':case,'seconds':0,'policy_accepted':True,'result':{'status':'passed'}})
        save(tmp_path/'STOP_DISPATCH',{'reason':'user_pause'})
        assert kwargs['pass_fds'] and kwargs['env']['I2R_FPP_RELEASE']=='frozen'
        return Process()
    monkeypatch.setattr(runner.subprocess,'Popen',launch)
    result=runner.dispatch(tmp_path,rows,{'identity':'frozen','workers':10})
    assert started==['first'] and result['pending']==1
    assert read(tmp_path/'status.json')['paused'] is True
    assert not (tmp_path/'tasks/second').exists()

@pytest.mark.parametrize('workers',[5,10])
@pytest.mark.parametrize('pipeline',[False,True])
def test_dispatch_obeys_frozen_concurrency(tmp_path,monkeypatch,workers,pipeline):
    rows=[{'id':str(i)} for i in range(13)]
    for row in rows:save(tmp_path/'preparation'/row['id']/'admission.json',{'seconds':0})
    save(tmp_path/'global-provider-budget.json',{'reservations':[]})
    monkeypatch.setattr(runner.art,'admission',lambda row,run:{'seconds':0})
    monkeypatch.setattr(runner.time,'sleep',lambda seconds:None)
    started=[];live=set();peaks=[]
    class Process:
        pid=123;returncode=0
        def __init__(self,case):self.case=case
        def poll(self):live.discard(self.case);return 0
    def launch(command,**kwargs):
        case=command[-1];started.append(case);live.add(case);peaks.append(len(live))
        save(tmp_path/'tasks'/case/'outcome.json',{'case':case,'seconds':0,'policy_accepted':True,'result':{'status':'passed'}})
        return Process(case)
    monkeypatch.setattr(runner.subprocess,'Popen',launch)
    result=runner.dispatch(tmp_path,rows,{'identity':'frozen','workers':workers},pipeline=pipeline)
    assert max(peaks)==workers and len(started)==len(set(started))==13
    assert result['completed']==result['accepted']==13 and not live

@pytest.mark.parametrize('workers',[None,10])
def test_release_freezes_workers_without_changing_budgets(tmp_path,monkeypatch,workers):
    monkeypatch.setattr(runner,'identity',lambda:{'sha256':'frozen','files':{}})
    monkeypatch.setattr(runner.art,'check_tools',lambda:{})
    monkeypatch.setattr(runner.art,'configuration',lambda row,run:{})
    rows=[{'id':'first'},{'id':'second'}]
    rel=runner.release(tmp_path,rows,workers)
    assert rel['workers']==(5 if workers is None else workers)
    assert (rel['per_task_calls'],rel['per_task_active_seconds'],rel['global_limit'])==(48,4200,96)
    assert runner.release(tmp_path,rows)==rel
    assert runner.release(tmp_path,rows,rel['workers'])==rel
    with pytest.raises(Failure) as caught:runner.release(tmp_path,rows,rel['workers']+1)
    assert caught.value.code=='release_changed' and read(tmp_path/'release.json')==rel

@pytest.mark.parametrize('workers',[0,-1,True,1.5])
def test_release_rejects_invalid_workers(tmp_path,workers):
    with pytest.raises(Failure) as caught:runner.release(tmp_path,[],workers)
    assert caught.value.code=='invalid_workers' and not (tmp_path/'release.json').exists()

def test_real_prepare_pause_exclusion_and_same_version_resume(tmp_path):
    import os,subprocess,sys,time
    from pathlib import Path
    script=tmp_path/'fixture.py'
    script.write_text('''import os,sys,time
from pathlib import Path
from i2r_agent import fpp_runner as r
from i2r_agent.common import save,read,Failure
r.art.manifest=lambda: {'cases':[{'id':'first'},{'id':'second'}]}
r.identity=lambda: {'sha256':os.environ.get('TEST_IDENTITY','frozen'),'files':{}}
r.art.check_tools=lambda: {}
r.art.configuration=lambda row,run: {}
r.art.install_execution=lambda run: None
def admission(row,run):
    if os.environ.get('TEST_ADMISSION_FAIL'):raise Failure('admission_changed','fixture')
    return {}  # Isolate lease conflict from reference construction.
r.art.admission=admission
def prepare(row,run):
    (run/(row['id']+'-started')).touch()
    if row['id']=='first':
        until=time.monotonic()+15
        while not (run/'finish-first').exists():
            if time.monotonic()>until:raise RuntimeError('test timeout')
            time.sleep(.02)
    result={'id':row['id'],'status':'admitted'}
    save(run/'preparation'/row['id']/'admission.json',result)
    return result
r.art.prepare=prepare
r.main()
''')
    run=tmp_path/'run'
    command=[sys.executable,str(script),'--run',str(run)]
    proc=subprocess.Popen(command+['prepare','--workers','10'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+10
        while not (run/'first-started').exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.02)
        assert (run/'first-started').exists()
        assert read(run/'release.json')['workers']==10
        duplicate=subprocess.run(command+['prepare'],capture_output=True,text=True,timeout=10)
        assert duplicate.returncode!=0 and 'BlockingIOError' in duplicate.stderr
        subprocess.run(command+['pause'],check=True,capture_output=True,timeout=10)
        conflict=subprocess.run(command+['resume'],capture_output=True,text=True,timeout=10)
        assert conflict.returncode!=0 and 'BlockingIOError' in conflict.stderr
        assert (run/'STOP_DISPATCH').exists()
        (run/'finish-first').touch()
        stdout,stderr=proc.communicate(timeout=15)
        assert proc.returncode==0,stderr
        assert (run/'preparation/first/admission.json').exists()
        assert not (run/'second-started').exists()
        assert read(run/'preparation-status.json')=={'paused':True,'pending':['second']}
        paused=subprocess.run(command+['prepare'],capture_output=True,text=True,timeout=10)
        assert paused.returncode!=0 and 'resume-prepare' in paused.stderr
        invalid=subprocess.run(command+['resume'],env={**os.environ,'TEST_ADMISSION_FAIL':'1'},capture_output=True,text=True,timeout=10)
        assert invalid.returncode!=0 and (run/'STOP_DISPATCH').exists()
        save(run/'tasks/second/process.json',{'state':'running'})
        unreconciled=subprocess.run(command+['resume'],capture_output=True,text=True,timeout=10)
        assert unreconciled.returncode!=0 and (run/'STOP_DISPATCH').exists()
        (run/'tasks/second/process.json').unlink()
        changed=subprocess.run(command+['resume-prepare'],env={**os.environ,'TEST_IDENTITY':'changed'},capture_output=True,text=True,timeout=10)
        assert changed.returncode!=0 and (run/'STOP_DISPATCH').exists()
        changed_workers=subprocess.run(command+['resume-prepare','--workers','5'],capture_output=True,text=True,timeout=10)
        assert changed_workers.returncode!=0 and 'release_changed' in changed_workers.stderr and (run/'STOP_DISPATCH').exists()
        resumed=subprocess.run(command+['resume-prepare'],capture_output=True,text=True,timeout=10)
        assert resumed.returncode==0,resumed.stderr
        assert (run/'preparation/second/admission.json').exists()
        assert read(run/'preparation-status.json')=={'paused':False,'pending':[]}
        assert read(run/'release.json')['workers']==10
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
