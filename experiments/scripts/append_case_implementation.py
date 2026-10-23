#!/usr/bin/env python3
"""Append a recorded implementation to an existing case round, without allocating EXP IDs."""
import argparse
import hashlib
import json
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]


def append(case_id, round_id, code_path, record_path):
    catalog_path = REPO/'experiments/cases.json'
    catalog = json.loads(catalog_path.read_text())
    case = next(c for c in catalog['cases'] if c['id'] == case_id)
    round_ = next(r for r in case['rounds'] if r['id'] == round_id)
    record = json.loads(record_path.read_text())
    run_id = record['run_id']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('run_id must be a simple, unique identifier within the round')
    if not isinstance(record.get('config'), dict) or not isinstance(record.get('result'), dict):
        raise ValueError('record requires config and result objects; unknown results must be explicit')
    if record.get('kind', 'llm') not in ['llm', 'manual']:
        raise ValueError('kind must be llm or manual')
    # Existing historic runs are part of the same round; never shadow one.
    summary_path = REPO/'experiments/results'/f"{round_['batch_id']}.json"
    summary = json.loads(summary_path.read_text())
    original = summary.get('runs', [dict(summary.get('run', {}), task=case_id, run_id='run-001')])
    known = {r['run_id'] for r in original if r.get('task') == case_id}
    for addition in round_.get('additions', []):
        known.add(json.loads((REPO/'experiments'/addition).read_text())['run_id'])
    if run_id in known:
        raise ValueError(f'Run already exists: {case_id}/{round_id}/{run_id}')
    code = code_path.read_bytes()
    sha = hashlib.sha256(code).hexdigest()
    expected = record['result'].get('candidate_sha256', record['result'].get('selected_candidate_sha256'))
    if expected and expected != sha:
        raise ValueError('Code hash does not match the result record')
    target = REPO/case['source_root']/'llm'/round_id/run_id/'candidate.rs'
    record_target = REPO/'experiments/cases'/case_id/round_id/(run_id+'.json')
    if target.exists() or record_target.exists():
        raise ValueError('Destination already exists; refusing to overwrite')
    # Preserve exact result/config data; attach a portable code reference alongside them.
    record.update(case_id=case_id, round_id=round_id, code_path=str(target.relative_to(REPO)), code_sha256=sha)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(code)
    record_target.parent.mkdir(parents=True, exist_ok=True)
    record_target.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
    round_.setdefault('additions', []).append(str(record_target.relative_to(REPO/'experiments')))
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n')
    return f'{case_id}/{round_id}/{run_id}'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('case_id')
    p.add_argument('round_id')
    p.add_argument('--code', type=Path, required=True)
    p.add_argument('--record', type=Path, required=True)
    a = p.parse_args()
    print(append(a.case_id, a.round_id, a.code, a.record))


if __name__ == '__main__':
    main()
