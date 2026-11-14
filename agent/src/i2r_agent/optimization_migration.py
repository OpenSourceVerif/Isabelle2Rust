"""Explicit, journaled recovery of an unmodified search after a protocol defect.

No accepted candidate may predate this migration. Model calls, elapsed charges,
inputs and baseline identities remain frozen; saved replies may be replayed once.
"""
import argparse
import fcntl
import os
from pathlib import Path
from .common import Failure, digest, read, save
from .task_context import fingerprint
from . import fpp_runner, fpp_artifact


ALLOWED = {'agent/src/i2r_agent/' + name + '.py' for name in
           ['optimization', 'optimization_protocol', 'optimization_migration', 'source_optimization']}


def migrate(run, from_identity):
    def reject(message):
        raise Failure('optimization_migration_rejected', message)
    run = Path(run).resolve()
    if not (run / 'STOP_DISPATCH').exists():
        reject('Pause and drain the optimization controller first')
    with (run / 'controller.lock').open('a+') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal = run / 'optimization-protocol-migration.json'
        archive = run / 'optimization-protocol-migration'
        archive.mkdir(exist_ok=True)
        if journal.exists():
            record = read(journal)
            for name, sha in record['snapshot_hashes'].items():
                if digest(archive / name) != sha: reject('Changed migration snapshot: ' + name)
            old = read(archive / 'release-before.json')
            old_origin = read(archive / 'origin-before.json')
        else:
            old = read(run / 'release.json'); old_origin = read(run / 'optimization-origin.json')
        if old['identity'] != from_identity or fingerprint(old['files']) != from_identity:
            reject('Expected complete original release identity')
        ids = read(run / 'selection.json')['ids']
        rows = [r for r in fpp_artifact.manifest()['cases'] if r['id'] in ids]
        new = fpp_runner.release_data(run, rows, old['workers'])
        changed = {n for n in old['files'].keys() | new['files'].keys()
                   if old['files'].get(n) != new['files'].get(n)}
        if not changed or not changed <= ALLOWED:
            reject('Migration changes files outside the performance controller: ' + str(sorted(changed)))
        if {k:v for k,v in old.items() if k not in {'identity','files'}} != {
                k:v for k,v in new.items() if k not in {'identity','files'}}:
            reject('Selection, configurations, tools, concurrency or budgets changed')
        new_origin = {**old_origin, 'release_identity': new['identity']}
        if read(run / 'release.json') not in [old, new] or read(run / 'optimization-origin.json') not in [old_origin, new_origin]:
            reject('Live identities are not recorded migration endpoints')
        if not journal.exists():
            snapshots = {'release-before.json': old, 'release-after.json': new,
                         'origin-before.json': old_origin, 'origin-after.json': new_origin}
            replays = {}; calls = 0
            for folder in sorted((run / 'optimization').iterdir()):
                state = read(folder / 'search-state.json'); budget = read(folder / 'budget.json')
                if state['accepted_path'] or (folder / 'result.json').exists() or budget.get('active'):
                    reject('Only inactive searches without accepted candidates may migrate')
                from .translation_workflow import version
                if version(state['incumbent']) != state['provenance']['candidate_version']:
                    reject('Incumbent differs from the original validated baseline')
                calls += budget['calls']
                snapshots[folder.name + '/budget.json'] = budget
                snapshots[folder.name + '/search-state.json'] = state
                responses = sorted((folder / 'model').glob('*/response.json'))
                for path in reversed(responses):
                    raw = read(path)
                    if raw['choices'][0].get('finish_reason') != 'stop': continue
                    from .provider import decode_model_json
                    from .optimization_protocol import normalize
                    try:
                        normalize(decode_model_json(raw['choices'][0]['message']['content'], archive / folder.name / 'decode'))
                    except Failure:
                        continue
                    replays[folder.name] = {'response': str(path), 'sha256': digest(path),
                                           'model_call_already_charged': int(path.parent.name),
                                           'policy': 'latest complete decodable response; no source-string modification'}
                    break
            for name, value in snapshots.items(): save(archive / name, value)
            record = {'status':'prepared', 'from_identity':from_identity, 'to_identity':new['identity'],
                      'changed_files':sorted(changed), 'charged_model_calls_preserved':calls,
                      'policy':'protocol and validation recovery; no changed inputs, baselines, budgets or accepted outputs',
                      'replays':replays, 'snapshot_hashes':{n:digest(archive / n) for n in snapshots}}
            save(journal, record)
        elif record['to_identity'] != new['identity']:
            reject('Target implementation changed after migration was prepared')
        for case, replay in record['replays'].items(): save(run / 'optimization' / case / 'protocol-replay.json', replay)
        save(run / 'release.json', new); save(run / 'optimization-origin.json', new_origin)
        record['status'] = 'complete'; save(journal, record)
        return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--run', type=Path, required=True)
    p.add_argument('--from-identity', required=True); a = p.parse_args()
    os.environ['I2R_DATASET'] = 'performance'
    r = migrate(a.run, a.from_identity)
    print({k:r[k] for k in ['status','from_identity','to_identity','charged_model_calls_preserved']})
