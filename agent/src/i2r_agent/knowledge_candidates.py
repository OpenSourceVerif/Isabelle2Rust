"""Offline extraction of adjacent failure/repair/replay evidence, never rules."""
import json
import re
from pathlib import Path
from .common import digest


def collect(diagnostics):
    diagnostics=Path(diagnostics).resolve();rows=[]
    steps=sorted(diagnostics.glob('segment-step-*/attempt.json'))
    for a,b,c in zip(steps,steps[1:],steps[2:]):
        fail,repair,replay=[json.loads(p.read_text()) for p in (a,b,c)]
        if fail.get('action_phase')!='compile' or fail.get('compilation',{}).get('status')!='compile_failed':continue
        if repair.get('action_phase')!='repair' or replay.get('action_phase')!='repair_replay':continue
        if len({d.get('unit') for d in (fail,repair,replay)})!=1:continue
        if fail.get('after_version')!=repair.get('state_version') or repair.get('after_version')!=replay.get('state_version'):continue
        diff=b.parent/'changes.diff';proof=c.parent/'original-replay.json'
        if not diff.is_file() or not diff.read_text().strip() or not proof.is_file():continue
        result=json.loads(proof.read_text());build=result.get('checks',{}).get('build',{})
        original=fail['compilation'].get('checks',{}).get('build',{})
        if result.get('status')!='passed' or build.get('status')!='passed' or build.get('returncode')!=0:continue
        if not original.get('command') or original['command']!=build.get('command'):continue
        codes=sorted(set(re.findall(r'\bE\d{4}\b',json.dumps(fail['compilation']))))
        if not codes:continue
        paths=[a,b,c,diff,proof]
        rows.append({'status':'unreviewed_candidate','validation_scope':'original compilation replay only; no semantic claim',
            'codes':codes,'unit':fail.get('unit'),'before_version':fail['state_version'],'after_version':replay['state_version'],
            'diagnostics':[d.get('message','') for d in fail['compilation'].get('diagnostics',[]) if d.get('level')=='error'],
            'patch_excerpt':diff.read_text()[:3000],'patch_truncated':len(diff.read_text())>3000,
            'evidence':[{'path':str(p),'sha256':digest(p)} for p in paths]})
    result_path=diagnostics/'result.json'
    run_result=({'status':json.loads(result_path.read_text()).get('status'),'path':str(result_path),'sha256':digest(result_path)} if result_path.is_file() else {'status':'unknown'})
    return {'schema':1,'run_result':run_result,'status':'requires_human_review','policy':'No automatic prompt/catalog promotion. Failed-only, unexecuted, different-condition and nonadjacent chains are excluded.','diagnostics':str(diagnostics),'candidates':rows}
