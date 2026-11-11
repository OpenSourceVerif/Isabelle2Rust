"""Standalone preprocessing; no reference build, Rust generation or measurements."""
from pathlib import Path
from .common import Executor, Failure, now, save
from .preprocessing import preprocess
from .planning import prepare_plan
from .provider import Provider


def prepare(project,output,cfg):
    if cfg.get('generation',{}).get('workflow') not in {None,'knowledge-v5','source-v6','segmented-v7','segmented-v8'}:
        raise Failure('unknown_workflow',str(cfg['generation']['workflow']))
    if cfg.get('generation',{}).get('workflow')in {'segmented-v7','segmented-v8'}:
        from .segmented_config import configure
        cfg=configure(cfg)
    if cfg.get('generation',{}).get('workflow') in {'knowledge-v5','source-v6','segmented-v7','segmented-v8'}:
        from copy import deepcopy
        from .common import read
        from .knowledge import analyze
        cfg=deepcopy(cfg)
        if cfg['testing'].get('transport')=='auto':cfg['testing']['transport']='native-u128' if cfg['preprocessing']['numeric_mode']=='checked' else 'dashu-ubig'
        project=Path(project).resolve();output=Path(output).resolve()
        if output.exists() and any(output.iterdir()):raise Failure('output_exists',str(output))
        output.mkdir(parents=True,exist_ok=True)
        metadata=read(project/'case.json') if (project/'case.json').exists() else {}
        provider=Provider(cfg,output/'model');executor=Executor(output/'commands')
        result={'status':'running','started_at':now(),'kind':'semantic_analysis_only','workflow':cfg['generation']['workflow']}
        try:
            bundle=preprocess(project/metadata.get('algorithm_project','.'),cfg,output/'source',executor)
            for key in ['observation_binding','kernel','workload','contract']:bundle.pop(key,None)
            bundle,record=analyze(bundle,cfg,provider,output/'planning')
            save(output/'prepared-program.json',bundle);result.update(status='prepared',planning=record,output=str(output/'prepared-program.json'))
        except Failure as error:result.update(status=error.code,error=str(error),evidence=error.evidence)
        result.update(finished_at=now(),usage=provider.usage,model_calls=provider.calls,model_calls_by_phase=provider.phase_calls)
        save(output/'result.json',result);return result
    output=Path(output).resolve()
    if output.exists() and any(output.iterdir()):raise Failure('output_exists',str(output))
    if cfg.get('preprocessing',{}).get('mode')!='auto':raise Failure('invalid_config','prepare requires auto preprocessing')
    output.mkdir(parents=True,exist_ok=True)
    save(output/'effective-config.json',cfg)
    executor=Executor(output/'commands');provider=Provider(cfg,output/'model')
    result={'status':'running','started_at':now(),'kind':'preprocessing_only'}
    try:
        bundle=preprocess(Path(project).resolve(),cfg,output/'source',executor)
        bundle,record=prepare_plan(bundle,cfg,provider,output/'planning',executor)
        save(output/'prepared-program.json',bundle)
        result.update(status='prepared',planning=record,output=str(output/'prepared-program.json'))
    except Failure as error:
        result.update(status=error.code,error=str(error),evidence=error.evidence)
    finally:
        result.update(finished_at=now(),usage=provider.usage,model_calls=provider.calls,model_calls_by_phase=provider.phase_calls)
        save(output/'result.json',result)
    return result
