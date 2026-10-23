#!/usr/bin/env python3
"""Publish allowlisted historical artifacts from existing frozen runs; never read credentials."""
import hashlib
import json
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]

def publish(batch_id):
    run = EXP/'runs'/batch_id
    summary = json.loads((EXP/'results'/f'{batch_id}.json').read_text())
    prepared = json.loads((run/'prepared.json').read_text())
    protocol = prepared['protocol_sha256']
    frozen = prepared['frozen_sha256']
    artifacts = []
    def read(relative, expected):
        path = (run/relative).resolve()
        if not path.is_relative_to(run.resolve()):
            raise ValueError('Snapshot path outside run directory')
        payload = path.read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected:
            raise ValueError(f'{batch_id}: hash mismatch for {relative}')
        artifacts.append(dict(path=relative, sha256=actual, verified=True))
        return payload.decode('utf-8')
    config = json.loads(read('config.json', frozen['config.json']))
    plan_files = [p for p in protocol if p.startswith('experiments/plans/') and p.endswith('.md')]
    plans = {p:read('protocol-snapshot/'+p, protocol[p]) for p in plan_files}
    tasks = summary.get('config', {}).get('tasks', ['list-index'])
    prompts = {}
    for task in tasks:
        path = task+'/prompt.txt' if task+'/prompt.txt' in frozen else 'prompt.txt'
        prompts[task] = read(path, frozen[path])
    output = dict(batch_id=batch_id, provenance='Recovered from frozen run artifacts; original hashes checked.',
                  config=config, plans=plans, prompts=prompts, artifacts=artifacts,
                  protocol_sha256=protocol, frozen_sha256=frozen)
    destination = EXP/'results'/'snapshots'/f'{batch_id}.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    content = json.dumps(output,ensure_ascii=False,indent=2)+'\n'
    if destination.exists() and destination.read_text()!=content:
        raise ValueError(f'Refusing to overwrite a different historical snapshot: {destination}')
    destination.write_text(content)
    return destination

if __name__=='__main__':
    for bid in ['20261023-01-list-index-smoke','20261023-02-two-task-pilot']:
        print(publish(bid))
