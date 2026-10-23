#!/usr/bin/env python3
"""Publish small reviewable summaries and a local source/log archive after v2 finishes.

The archive excludes build products; it is not an independent/off-device backup.
"""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

import run_pilot_v2 as pilot
from afp_artifacts import publish


def main():
    root=pilot.BATCH
    ready=pilot.verify()
    config=json.loads((root/'config.json').read_text())
    runs=json.loads((root/'generation-results.json').read_text())
    performance=json.loads((root/'performance.json').read_text())
    ledger=json.loads((root/'ledger.json').read_text())
    assert ledger['in_flight'] is None
    assert len(runs)==len(config['tasks'])*config['independent_runs_per_task']
    for task in config['tasks']:
        target=pilot.EXP/'prompts'/('%s-%s.txt'%(pilot.BATCH_ID,task))
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(root/task/'prompt.txt',target)
    usage={field:sum(a['usage'].get(field,0) for r in runs for a in r['attempts'])
           for field in ['prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens']}
    summary=dict(batch_id=pilot.BATCH_ID,config=config,environment=ready['environment'],
                 baselines=ready['tasks'],runs=runs,usage=usage,ledger=ledger,
                 protocol_sha256=ready['protocol_sha256'],frozen_sha256=ready['frozen_sha256'],
                 performance=dict(protocol=performance['protocol'],aggregates=performance['aggregates'],
                                  total_samples=len(performance['samples']),
                                  failed_samples=sum(x['status']!='passed' for x in performance['samples'])))
    pilot.save(pilot.EXP/'results'/(pilot.BATCH_ID+'.json'),summary)
    publish(pilot.BATCH_ID)  # Registered ID; reuse task baselines; publish candidates under test/afp/<task>/llm/EXP-NNNN.
    rows=performance['aggregates']
    with (pilot.EXP/'results'/(pilot.BATCH_ID+'-performance.csv')).open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    index={(r['implementation'],r['length'],r['query']):r for r in rows}
    table=['| 长度 | 查询 | Stage 1 μs | Stage 2 μs | OCaml μs | 3 个候选 μs 范围 | 相对 Stage 2 加速范围 |',
           '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for n in config['performance']['lengths']:
        for query in config['performance']['queries']:
            def us(name):
                return index[(name,n,query)]['median_ns']/1000
            candidates=[us(r['run_id']) for r in runs if r['task']=='list-index' and r['status']=='passed']
            low,high=min(candidates),max(candidates)
            table.append('| %d | %s | %.3f | %.3f | %.3f | %.3f–%.3f | %.2f–%.2f× |'%
                         (n,query,us('stage1'),us('stage2'),us('ocaml'),low,high,us('stage2')/high,us('stage2')/low))
    (pilot.EXP/'results'/(pilot.BATCH_ID+'-performance.md')).write_text(
        '# List-Index 探索性计时\n\n各实现为 7 轮的每调用耗时中位数。候选范围覆盖 3 次生成，不选择最快者。\n'
        '计入输入准备和表示转换，排除解析和输出；不是孤立内核比较。完整范围见批次协议。\n\n'+
        '\n'.join(table)+'\n\n原始每轮数据保存在本地 performance.json；CSV 同时保留每个实现的最小/最大值。\n')
    # Collect source and logs only; original data remain untouched.
    files=[]
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        rel=p.relative_to(root)
        if 'target' in rel.parts or '__pycache__' in rel.parts:
            continue
        if p.suffix in {'.cmi','.cmx','.o','.a','.cmxa','.cmo'} or p.name=='reference':
            continue
        if p.name=='archive-manifest.json':
            continue
        files.append(p)
    manifest={str(p.relative_to(root)):pilot.digest(p) for p in sorted(files)}
    pilot.save(root/'archive-manifest.json',manifest)
    archives=pilot.EXP/'runs/_archives'
    archives.mkdir(exist_ok=True)
    archive=archives/(pilot.BATCH_ID+'.tar.gz')
    if archive.exists():
        raise RuntimeError('Archive exists; will not overwrite it.')
    with tarfile.open(archive,'w:gz') as tar:
        for p in files+[root/'archive-manifest.json']:
            tar.add(p,arcname=str(Path(pilot.BATCH_ID)/p.relative_to(root)),recursive=False)
    # Verify every archived source/log file against the manifest.
    with tarfile.open(archive,'r:gz') as tar:
        for name,sha in manifest.items():
            assert hashlib.sha256(tar.extractfile(pilot.BATCH_ID+'/'+name).read()).hexdigest()==sha
    pilot.save(pilot.EXP/'results'/(pilot.BATCH_ID+'-archive.json'),
               dict(path=str(archive.relative_to(pilot.REPO)),sha256=pilot.digest(archive),bytes=archive.stat().st_size,
                    files=len(manifest),independent_backup=False,excludes='build products',verified=True))
    print('\n'.join(table))
    print('Usage:',json.dumps(usage),'estimated peak cost USD:',ledger['estimated_peak_cost_usd'])
    print('Archive verified:',len(manifest),'files;',archive.stat().st_size,'bytes')


if __name__=='__main__':
    main()
