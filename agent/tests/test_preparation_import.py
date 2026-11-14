from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import pytest
from i2r_agent import preparation_import as imp,dataset_artifact as art,experiment_runner as runner,baselines,provider
from i2r_agent.common import save,read,digest,Failure
from i2r_agent.task_context import fingerprint


def fixture(tmp_path,monkeypatch):
    origin=tmp_path/'old';run=tmp_path/'new';origin.mkdir();run.mkdir()
    cfg={'tools':{'isabelle_heaps':str(origin/'heaps'),'optimizer_target':str(origin/'optimizer-target'),'isabelle':'pinned'},
         'preprocessing':{'numeric_mode':'arbitrary'},'generation':{'workflow':'test'},'testing':{'transport':'auto'}}
    current=deepcopy(cfg)
    for k,d in [('isabelle_heaps','heaps'),('optimizer_target','optimizer-target')]:current['tools'][k]=str(run/d)
    row={'id':'case','root':'A.f','closure':['A.f'],'project':'projects/case','files':{},'source_mounts':{}}
    p=origin/'projects/case';p.mkdir(parents=True)
    work=origin/'preparation/case';work.mkdir(parents=True)
    for name in ['source','wrapper']:save(work/(name+'.json'),{'mechanical':'only'})
    reference=origin/'reference';reference.write_text('binary');source=origin/'reference.rs';source.write_text('source')
    key=lambda case,bundle,c:{'case':case,'tools':c['tools']}
    record={'identity':key('case',{},cfg),'references':{'ocaml':{'binary':str(reference),'binary_sha256':digest(reference),'source':str(source),'sha256':digest(source)}}}
    save(work/'baseline.json',record)
    ad={'id':'case','root':'A.f','status':'admitted','model_calls':0,'seconds':12.5,'project':str(p),'config':cfg,'suites':{name:'passed' for name in imp.SUITES}}
    for field,hfield,name in [('source_cache','source_sha256','source'),('wrapper','wrapper_sha256','wrapper'),('baseline_record','baseline_sha256','baseline')]:ad[field]=str(work/(name+'.json'));ad[hfield]=digest(ad[field])
    ad['seal']=fingerprint(ad);save(work/'admission.json',ad)
    for name in imp.SUITES:save(work/(name+'.json'),{'selection':{'status':'passed'}})
    old={'files':{'unchanged':'same','agent/src/i2r_agent/segmented_support.py':'old'},'tool_sources':{},'evaluation_order':['case'],
      'per_task_calls':48,'per_task_active_seconds':4200,'effective_configs':{'case':cfg},'global_limit':48}
    old['identity']=fingerprint(old['files']);new=deepcopy(old);new['files']['agent/src/i2r_agent/segmented_support.py']='new';new['identity']=fingerprint(new['files']);new['effective_configs']['case']=current
    save(origin/'release.json',old);save(run/'release.json',new);save(origin/'STOP_DISPATCH',{})
    save(origin/'global-provider-budget.json',{'reservations':[{'prior_cost':3}]});save(run/'global-provider-budget.json',{'prior_attempts':0,'reservations':[]})
    monkeypatch.setattr(art,'configuration',lambda r,where:deepcopy(current if where==run else cfg))
    monkeypatch.setattr(imp.source_cache,'load',lambda p,c:{'source_model':{'entries':['A.f'],'entities':{'A.f':{}}}})
    monkeypatch.setattr(imp.knowledge_run,'reference_bundle',lambda p,b:{})
    monkeypatch.setattr(baselines,'identity',key)
    return origin,run,row,old,new,ad


def imported(tmp_path,monkeypatch):
    origin,run,row,old,new,ad=fixture(tmp_path,monkeypatch)
    result=imp.import_preparation(run,[row],new,origin,old['identity'])
    return origin,run,row,old,new,ad,result


def test_import_keeps_exact_original_artifacts_and_cost_with_zero_provider_calls(tmp_path,monkeypatch):
    origin,run,row,old,new,ad=fixture(tmp_path,monkeypatch)
    before={str(p):digest(p) for p in origin.rglob('*') if p.is_file()}
    with patch.object(provider.Provider,'call',side_effect=AssertionError('No model call')) as api,patch.object(art,'prepare',side_effect=AssertionError('No re-export')) as prepare:
        result=imp.import_preparation(run,[row],new,origin,old['identity'])
        actual=art.admission(row,run)
        assert result['model_calls']==0 and actual['seconds']==ad['seconds']
        assert actual['project']==ad['project'] and actual['baseline_record']==ad['baseline_record'] and actual['source_cache']==ad['source_cache']
        assert actual['config']==new['effective_configs']['case']
        assert result['imported_model_results']==0 and not (run/'tasks').exists()
        api.assert_not_called();prepare.assert_not_called()
    assert all(digest(p)==sha for p,sha in before.items())
    assert imp.import_preparation(run,[row],new,origin,old['identity'])==result

@pytest.mark.parametrize('fault',['cfg','numeric','source','ref','recipe','tools','origin_config','origin_seal','target_calls','target_state','not_paused'])
def test_import_rejects_incompatible_or_mutated_inputs(tmp_path,monkeypatch,fault):
    origin,run,row,old,new,ad=fixture(tmp_path,monkeypatch)
    if fault=='cfg':new['effective_configs']['case']['tools']['isabelle']='changed'
    elif fault=='numeric':new['effective_configs']['case']['preprocessing']['numeric_mode']='checked'
    elif fault=='source':Path(ad['source_cache']).write_text('{}')
    elif fault=='ref':(origin/'reference').write_text('changed')
    elif fault=='recipe':new['files']['agent/src/i2r_agent/preprocessing.py']='new';new['identity']=fingerprint(new['files'])
    elif fault=='tools':new['tool_sources']={'changed':True}
    elif fault=='origin_config':old['effective_configs']['case']['testing']['transport']='other';save(origin/'release.json',old)
    elif fault=='origin_seal':ad['seconds']=0;save(origin/'preparation/case/admission.json',ad)
    elif fault=='target_calls':save(run/'global-provider-budget.json',{'prior_attempts':0,'reservations':[{}]})
    elif fault=='target_state':save(run/'tasks/case/diagnostics/segmented-checkpoint.json',{})
    else:(origin/'STOP_DISPATCH').unlink()
    with pytest.raises(Failure):imp.import_preparation(run,[row],new,origin,old['identity'])
    assert not (run/'preparation/case/admission.json').exists()


def test_child_acquisition_revalidates_read_only_origin_and_explicit_path_binding(tmp_path,monkeypatch):
    origin,run,row,old,new,ad,_=imported(tmp_path,monkeypatch)
    monkeypatch.setattr(art,'install_execution',lambda run:None);monkeypatch.setattr(art,'inputs',lambda row:None)
    monkeypatch.setattr(runner.request_budget,'install',lambda *a:None)
    original_acquire=baselines.acquire
    seen=[]
    def build(project,output,cfg,diagnostics):
        assert project==Path(ad['project'])
        # Real knowledge_run resolves transport before calling the installed acquire.
        cfg=deepcopy(cfg);cfg['testing']['transport']='dashu-ubig'
        record=baselines.acquire('case',project/'testing',{},cfg)
        seen.append(record);return {'status':'provider_boundary_no_call'}
    monkeypatch.setattr(runner.knowledge_run,'build',build)
    try:
        with patch.object(provider.Provider,'call',side_effect=AssertionError('No API')) as api:
            runner.child(row,run,new)
            assert seen[0]['identity']['tools']==ad['config']['tools'];api.assert_not_called()
        # Mutation after import is rejected by the actual child entry before build.
        Path(ad['wrapper']).write_text('{}')
        with pytest.raises(Failure):runner.child(row,run,new)
        assert len(seen)==1
    finally:baselines.acquire=original_acquire


def test_import_requires_old_controller_lease_and_retains_pause(tmp_path,monkeypatch):
    import fcntl
    origin,run,row,old,new,ad=fixture(tmp_path,monkeypatch)
    with (origin/'controller.lock').open('a+') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):imp.import_preparation(run,[row],new,origin,old['identity'])
    assert (origin/'STOP_DISPATCH').exists()
