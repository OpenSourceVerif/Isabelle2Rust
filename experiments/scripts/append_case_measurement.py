#!/usr/bin/env python3
"""Append new measurements to a case round; preserve history and update the latest table."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from build_dashboard import get_data

REPO = Path(__file__).resolve().parents[2]


def append(case_id, round_id, record_path):
    path = REPO/'experiments/cases.json'
    catalog = json.loads(path.read_text())
    case = next(c for c in catalog['cases'] if c['id'] == case_id)
    if round_id not in {r['id'] for r in case['rounds']}:
        raise ValueError('Register the case round before attaching measurements')
    source = json.loads(record_path.read_text())
    stamp = dt.datetime.fromisoformat(source['measured_at'].replace('Z','+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('measured_at requires a timezone')
    scope = source['scope']
    if scope not in ['end_to_end', 'kernel']:
        raise ValueError('scope must be end_to_end or kernel')
    if not source.get('protocol') or not source.get('rows'):
        raise ValueError('Actual protocol and nonempty rows are required')
    existing = next(c for c in get_data()['cases'] if c['id'] == case_id)
    times = [dt.datetime.fromisoformat(v['measured_at'].replace('Z','+00:00'))
             for v in existing['performance_views'] if v.get('measured_at')]
    if times and stamp < max(times):
        raise ValueError('Older measurements cannot be appended as a latest update')
    hashes = {i['implementation_id']:i['code_sha256'] for i in existing['implementations']}
    seen = set()
    for row in source['rows']:
        if row.get('code_sha256') != hashes.get(row['implementation']) or row['implementation'] not in hashes:
            raise ValueError('Implementation ID or source hash mismatch')
        key = (row['implementation'],row['length'],row['query'],row['values'])
        if key in seen:
            raise ValueError('Duplicate implementation/workload in measurement')
        seen.add(key)
        for field in ['median_ns','min_ns','max_ns']:
            if not isinstance(row[field], (int,float)) or not math.isfinite(row[field]) or row[field] <= 0:
                raise ValueError('Timings must be positive finite nanoseconds')
        if not row['min_ns'] <= row['median_ns'] <= row['max_ns']:
            raise ValueError('Invalid timing interval')
        if not isinstance(row['successful_rounds'],int) or row['successful_rounds'] < 1:
            raise ValueError('successful_rounds must be a positive integer')
    records = case.setdefault('performance_records', [])
    sequence = max((r['sequence'] for r in records), default=0)+1
    number = max((int(r['id'][1:]) for r in records), default=0)+1
    identifier = f'M{number:03d}'
    target = REPO/'experiments/cases'/case_id/round_id/(identifier+'.json')
    if target.exists():
        raise ValueError('Measurement file already exists; refusing to overwrite')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(record_path.read_bytes())
    records.append(dict(id=identifier, round_id=round_id, sequence=sequence, scope=scope,
                        kind='normalized', source=str(target.relative_to(REPO/'experiments')),
                        sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    return f'{case_id}/{round_id}/{identifier}'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('case_id');p.add_argument('round_id');p.add_argument('--record',type=Path,required=True)
    args=p.parse_args()
    print(append(args.case_id,args.round_id,args.record))


if __name__=='__main__':
    main()
