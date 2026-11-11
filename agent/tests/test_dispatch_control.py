"""The artifact controller drains active work and leaves pending tasks untouched."""
from i2r_agent import fpp_runner as runner
from i2r_agent.common import save,read

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
    result=runner.dispatch(tmp_path,rows,{'identity':'frozen'})
    assert started==['first'] and result['pending']==1
    assert read(tmp_path/'status.json')['paused'] is True
    assert not (tmp_path/'tasks/second').exists()
