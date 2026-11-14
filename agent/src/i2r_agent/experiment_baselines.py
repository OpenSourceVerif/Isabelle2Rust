"""Immutable references to validated cases from one or more generation runs."""
import argparse
from pathlib import Path
from .common import Failure, digest, read, save


FILES = ['outcome.json', 'diagnostics/segmented-checkpoint.json', 'diagnostics/effective-config.json']


def identity(run):
    run = Path(run)
    path = run / 'baseline-sources.json' if (run / 'baseline-sources.json').exists() else run / 'release.json'
    return digest(path)


def resolve(run, case):
    run = Path(run).resolve(); index = run / 'baseline-sources.json'
    if not index.exists():
        return run
    data = read(index)
    if data.get('schema') != 1 or case not in data['cases']:
        raise Failure('baseline_case_missing', case)
    record = data['cases'][case]; source = Path(record['run'])
    if digest(source / 'release.json') != record['release_sha256']:
        raise Failure('baseline_release_changed', case)
    for name, sha in record['files'].items():
        if digest(source / 'tasks' / case / name) != sha:
            raise Failure('baseline_case_changed', case + ':' + name)
    return source


def compose(runs, output):
    """Record provenance; never copy a result as if it were newly generated."""
    rows = {}
    for run in runs:
        run = Path(run).resolve()
        for case in read(run / 'selection.json')['ids']:
            task = run / 'tasks' / case
            if case in rows:
                raise Failure('duplicate_baseline_case', case)
            outcome = read(task / 'outcome.json')
            if not outcome.get('policy_accepted') or outcome['result']['status'] != 'passed':
                raise Failure('unvalidated_baseline', case)
            rows[case] = {'run': str(run), 'release_sha256': digest(run / 'release.json'),
                          'files': {name: digest(task / name) for name in FILES}}
    result = {'schema': 1, 'policy': 'Read-only composition of original validated runs; no new generation or correctness claims', 'cases': rows}
    path = Path(output) / 'baseline-sources.json'
    if path.exists() and read(path) != result:
        raise Failure('baseline_collection_changed', str(path))
    save(path, result); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='append', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); result = compose(args.run, args.output)
    print('Referenced', len(result['cases']), 'validated cases')
