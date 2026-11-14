"""Exercise persistent budget reservation and immutable admission controls."""
import copy, json, multiprocessing
from pathlib import Path
from types import SimpleNamespace
import pytest
from i2r_agent.common import Failure, save, read, digest
from i2r_agent import request_budget as budget, dataset_artifact as artifact
from i2r_agent.task_context import fingerprint


def reserve(run,release,index,queue):
    module=SimpleNamespace(save=save,Failure=Failure)
    budget.install(module,Path(run),release)
    try:
        module.save(Path(run)/'tasks/case/diagnostics/model'/f'{index:03d}'/'request.json',{'model':'deepseek-flash'})
        queue.put('reserved')
    except Failure as error:queue.put(error.code)


def test_concurrent_requests_cannot_exceed_per_case_budget(tmp_path):
    release={'identity':'frozen','global_limit':20,'per_task_calls':2,'evaluation_order':['case']}
    budget.initialize(tmp_path,release)
    ctx=multiprocessing.get_context('spawn');queue=ctx.Queue()
    workers=[ctx.Process(target=reserve,args=(str(tmp_path),release,i,queue)) for i in range(1,5)]
    for worker in workers:worker.start()
    for worker in workers:worker.join(15);assert worker.exitcode==0
    results=[queue.get(timeout=5) for _ in workers]
    assert results.count('reserved')==2 and results.count('budget_exhausted')==2
    assert len(read(tmp_path/'global-provider-budget.json')['reservations'])==2
    assert len(list(tmp_path.glob('tasks/case/diagnostics/model/*/request.json')))==2
    with pytest.raises(ValueError):budget.initialize(tmp_path,{**release,'identity':'changed'})


def test_existing_request_cannot_be_reserved_or_overwritten(tmp_path):
    release={'identity':'frozen','global_limit':48,'per_task_calls':48,'evaluation_order':['case']}
    module=SimpleNamespace(save=save,Failure=Failure);budget.install(module,tmp_path,release)
    path=tmp_path/'tasks/case/diagnostics/model/001/request.json';payload={'model':'deepseek-flash'}
    module.save(path,payload)
    with pytest.raises(Failure):module.save(path,{**payload,'messages':['changed']})
    assert read(path)==payload and len(read(tmp_path/'global-provider-budget.json')['reservations'])==1


def test_admission_rejects_changed_config_and_artifact(tmp_path,monkeypatch):
    row={'id':'case'};cfg={'tools':{'isabelle':'pinned'}};project=tmp_path/'project'
    monkeypatch.setattr(artifact,'configuration',lambda r,p:copy.deepcopy(cfg))
    monkeypatch.setattr(artifact,'project',lambda r,p:project)
    result={'project':str(project),'config':copy.deepcopy(cfg)}
    for field,hashfield in [('source_cache','source_sha256'),('wrapper','wrapper_sha256'),('baseline_record','baseline_sha256')]:
        p=tmp_path/field;p.write_text('{}');result[field]=str(p);result[hashfield]=digest(p)
    result['seal']=fingerprint(result);save(tmp_path/'preparation/case/admission.json',result)
    artifact.admission(row,tmp_path)
    cfg['tools']['isabelle']='changed'
    with pytest.raises(Failure):artifact.admission(row,tmp_path)
    cfg['tools']['isabelle']='pinned';Path(result['wrapper']).write_text('changed')
    with pytest.raises(Failure):artifact.admission(row,tmp_path)
