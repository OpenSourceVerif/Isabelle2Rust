from __future__ import annotations

import fcntl
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from .common import ROOT,Failure,config,digest,merge,now,read,save
from .pipeline import build
from . import tool_sources


def plan(path):
    spec=read(path)
    if spec.get('asset_accumulation',False):raise Failure('disabled_feature','Asset accumulation is explicitly deferred')
    tasks=[]
    for case in spec['cases']:
        for variant,overrides in spec['variants'].items():
            if not all(re.fullmatch(r'[A-Za-z0-9_-]+',value) for value in [case,variant]):
                raise Failure('invalid_identifier','Case and variant IDs must be simple names')
            for repeat in range(1,spec.get('repetitions',1)+1):
                tasks.append({'case':case,'variant':variant,'repeat':repeat,
                    'id':f'{case}--{variant}--{repeat:02d}','overrides':merge(overrides,spec.get('case_overrides',{}).get(case,{}))})
    return spec,tasks


def run(path,run_id=None,resume=False,case_filter=None,variant_filter=None):
    spec,tasks=plan(path)
    if case_filter:tasks=[t for t in tasks if t['case'] in case_filter]
    if variant_filter:tasks=[t for t in tasks if t['variant'] in variant_filter]
    if not tasks:raise Failure('empty_study','No tasks selected')
    run_id=run_id or now().replace(':','').replace('-','').split('.')[0]+'-'+spec['id']
    if not re.fullmatch(r'[A-Za-z0-9_+T-]+',run_id):raise Failure('invalid_identifier','Run ID must be a simple name')
    directory=ROOT/'data/runs'/run_id
    if directory.exists() and not resume:raise Failure('run_exists','Use --resume to continue the same frozen study')
    directory.mkdir(parents=True,exist_ok=True)
    lock=(directory/'.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise Failure('run_locked','This study already has an active writer')
    try:
        frozen=directory/'study.json'
        identity={'tool_sources':tool_sources.manifest(),'spec':spec,'tasks':tasks,'code':{str(p.relative_to(ROOT)):digest(p) for folder in ['src','isabelle','prompts','config','skills']
            for p in (ROOT/folder).rglob('*') if p.is_file() and (p.suffix in {'.py','.ML','.thy','.toml','.md','.txt','.json'} or p.name in {'ROOT','ROOTS'})},
            'cases':{case:{str(p.relative_to(ROOT/'catalog/cases'/case)):digest(p) for p in (ROOT/'catalog/cases'/case).rglob('*') if p.is_file()}
                     for case in sorted({t['case'] for t in tasks})}}
        if spec.get('base',{}).get('generation',{}).get('workflow')in {'source-v6','segmented-v7','segmented-v8'}:
            from importlib.metadata import version
            identity['runtime_dependencies']={n:version(n) for n in ['tree-sitter','tree-sitter-rust']}
        if frozen.exists():
            if read(frozen)!=identity:raise Failure('stale_snapshot','Study code, configuration or inputs changed; start a new run')
        else:
            save(frozen,identity)
            for relative in identity['code']:
                destination=directory/'implementation'/relative
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/relative,destination)
            save(directory/'tool-sources.json',identity['tool_sources'])
        for case in sorted({t['case'] for t in tasks}):
            snapshot=directory/'inputs'/case
            if not snapshot.exists():shutil.copytree(ROOT/'catalog/cases'/case,snapshot)
        summary={'id':run_id,'started_at':now(),'status':'running','tasks':tasks,'results':{}}
        if (directory/'summary.json').exists():summary=read(directory/'summary.json')
        if resume:
            summary.update(status='running',resumed_at=now())
            summary.pop('finished_at',None)
        save(directory/'summary.json',summary)
    except BaseException:
        lock.close()
        raise
    try:
        for task in tasks:
            tool_sources.verify(identity['tool_sources'])
            td=directory/'trials'/task['id']; result_path=td/'result.json'
            previous=read(result_path) if result_path.exists() else {}
            knowledge=spec.get('base',{}).get('generation',{}).get('workflow') in {'knowledge-v5','source-v6','segmented-v7','segmented-v8'}
            recovering=resume and knowledge and previous.get('status') in {'provider_error','interrupted','running'}
            if previous.get('phase')=='finished' and not recovering:
                summary['results'][task['id']]=read(result_path)['status'];continue
            abandoned=None
            if td.exists() and not (knowledge and resume):
                abandoned=directory/'interrupted'/f"{task['id']}-{now().replace(':','')}"
                abandoned.parent.mkdir(exist_ok=True);shutil.move(td,abandoned)
            td.mkdir(parents=True,exist_ok=True)
            if recovering:
                history=td/'recovery';history.mkdir(exist_ok=True)
                save(history/(now().replace(':','')+'.json'),previous)
            if abandoned:
                previous_model=abandoned/'diagnostics/model'
                if previous_model.exists():shutil.copytree(previous_model,td/'diagnostics/model')
                save(td/'resume.json',{'previous_trial':str(abandoned),'budget':'continued; no model-call reset'})
            effective=merge(config(),spec.get('base',{}));effective=merge(effective,task['overrides'])
            if effective.get('generation',{}).get('workflow')in {'segmented-v7','segmented-v8'}:
                from .segmented_config import origins
                effective['_configuration_sources']=origins(effective,[('config/default.toml',read(ROOT/'config/default.toml')),('config/local.toml',read(ROOT/'config/local.toml')),('study.base',spec.get('base',{})),('variant/case_overrides',task['overrides'])])
            def progress(result):
                result={**result,'study':run_id,'variant':task['variant'],'repeat':task['repeat'],'task_id':task['id']}
                save(result_path,result)
                summary['results'][task['id']]=result['status'];save(directory/'summary.json',summary)
                print(f"{task['id']}: {result['phase']} / {result['status']}",file=sys.stderr,flush=True)
            seed=ROOT/'state/regressions'/f"{task['case']}.json"
            # Freeze initial regressions once per case so earlier variants do not
            # teach later variants during the same ablation campaign.
            frozen_reg=directory/'inputs'/task['case']/'regressions.json'
            if not frozen_reg.exists():save(frozen_reg,read(seed) if seed.exists() else [])
            result=build(directory/'inputs'/task['case'],td/'code',effective,td/'diagnostics',frozen_reg,progress,baseline_store=ROOT/'data/baselines')
            tool_sources.verify(identity['tool_sources'])
            summary['results'][task['id']]=result['status'];save(directory/'summary.json',summary)
        summary.update(status='finished',finished_at=now());save(directory/'summary.json',summary)
        from .context_evaluation import summarize
        summarize(directory)
        # Regression publication is case-scoped testing, not an asset/experience library.
        from .validation import add_regressions
        for task in tasks:
            d=directory/'trials'/task['id']/'diagnostics'
            for name in ['regressions.json','released-final-counterexamples.json']:
                if (d/name).exists():add_regressions(ROOT/'state/regressions'/f"{task['case']}.json",read(d/name))
    except KeyboardInterrupt:
        summary.update(status='interrupted');save(directory/'summary.json',summary);raise
    finally:lock.close()
    return summary
