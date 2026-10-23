#!/usr/bin/env python3
"""Register stable experiment IDs and publish task baselines and experiment-specific LLM candidates (no API calls)."""
import argparse
import hashlib
import json
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]
EXP = REPO / 'experiments'
REGISTRY = EXP / 'registry.json'
AFP = REPO / 'test/afp'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def registry():
    return read(REGISTRY) if REGISTRY.exists() else {'schema_version': 1, 'experiments': []}


def register(batch_id, title):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', batch_id):
        raise ValueError('Invalid batch ID')
    data = registry()
    existing = next((e for e in data['experiments'] if e['batch_id'] == batch_id), None)
    if existing:
        return existing
    number = max((int(e['experiment_id'].split('-')[1]) for e in data['experiments']), default=0) + 1
    entry = dict(experiment_id=f'EXP-{number:04d}', batch_id=batch_id, title=title,
                 artifact_root='test/afp',
                 artifact_manifest=f'experiments/results/artifacts/EXP-{number:04d}.json',
                 summary=f'experiments/results/{batch_id}.json',
                 record=f'experiments/batches/{batch_id}.md')
    data['experiments'].append(entry)
    write(REGISTRY, data)
    return entry


def lookup(identifier):
    return next(e for e in registry()['experiments']
                if identifier in (e['experiment_id'], e['batch_id']))


def publish(identifier):
    entry = lookup(identifier)
    summary_path = REPO / entry['summary']
    summary = read(summary_path)
    batch = EXP / 'runs' / entry['batch_id']
    ready = read(batch / 'prepared.json')
    # Check original frozen inputs before making a readable copy. Do not alter the originals.
    for relative, expected in ready.get('frozen_sha256', {}).items():
        path = batch / relative
        if digest(path) != expected:
            raise ValueError(f'Frozen artifact changed: {path}')
    single = 'runs' not in summary
    runs = summary.get('runs', [summary.get('run')])
    if single and 'list-index' not in summary['task'].get('task_id', ''):
        raise ValueError('Unknown single-task layout; supply an explicit task adapter')
    tasks = list(dict.fromkeys(r.get('task', 'list-index') for r in runs))
    destination = AFP
    files, candidates = [], []

    def copy(source, relative):
        content = source.read_bytes()
        target = destination / relative
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f'Artifact differs: {target}. Baseline changes require an explicit new version, not an experiment copy.')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(content)
        files.append(dict(path=str(target.relative_to(REPO)), sha256=digest(target),
                          original_path=str(source.relative_to(REPO))))
        return str(target.relative_to(REPO))

    for task in tasks:
        root = batch if single else batch / task
        base = root / 'baselines'
        source_files = sorted((root / 'source').glob('*.thy'))
        if not source_files:
            raise ValueError(f'Missing Isabelle source for {task}')
        if single and digest(root/'source/List_Index.thy') != ready['environment']['source_sha256']:
            raise ValueError('Isabelle source differs from recorded hash')
        for source in source_files:
            copy(source, Path(task) / 'isabelle' / source.name)
        session = base / 'session'
        # EXP-0002 reused the already exported List-Index baseline from EXP-0001.
        if not session.exists() and entry['batch_id'] == '20261023-02-two-task-pilot' and task == 'list-index':
            session = EXP / 'runs/20261023-01-list-index-smoke/baselines/session'
        for source in sorted(session.glob('*')):
            if source.name == 'ROOT' or source.suffix == '.thy':
                copy(source, Path(task) / 'isabelle/session' / source.name)
        for stage, source_dir in [('stage1', base/'generated/reference'), ('stage2', base/'optimized')]:
            if not (source_dir/'src/lib.rs').exists():
                raise ValueError(f'Missing {stage} for {task}')
            for source in sorted(source_dir.rglob('*')):
                if source.is_file() and 'target' not in source.relative_to(source_dir).parts and (source.suffix == '.rs' or source.name == 'Cargo.toml'):
                    copy(source, Path(task) / stage / source.relative_to(source_dir))
        exported = base / 'generated/reference.ocaml'
        if exported.read_bytes() != (base/'ocaml/exported_reference.ml').read_bytes():
            raise ValueError(f'OCaml export and tested reference differ: {task}')
        copy(exported, Path(task) / 'ocaml/reference.ml')
        for index, run in enumerate(runs, 1):
            if run.get('task', 'list-index') != task:
                continue
            run_id = run.get('run_id', f'run-{index:03d}')
            run_root = root / run_id
            selected = run.get('selected_attempt')
            for attempt in run.get('attempts', []):
                number = attempt['attempt']
                source = run_root / f'attempt-{number:02d}/candidate.rs'
                if not source.exists():
                    if number == selected:
                        raise ValueError(f'Missing selected candidate: {source}')
                    continue  # API errors can have no candidate.
                path = copy(source, Path(task) / 'llm' / entry['experiment_id'] / run_id / f'attempt-{number:02d}.rs')
                if number == selected:
                    expected = run.get('candidate_sha256', run.get('selected_candidate_sha256'))
                    if digest(source) != expected:
                        raise ValueError(f'Selected candidate hash mismatch: {source}')
                    candidates.append(dict(task=task, run_id=run_id, file=path, path_base='repository',
                                           sha256=expected, reference=f"{entry['experiment_id']}/{task}/{run_id}"))
    manifest = dict(schema_version=2, experiment_id=entry['experiment_id'], batch_id=entry['batch_id'],
                    files=files, selected_candidates=candidates,
                    note='Exact copies of recorded artifacts. isabelle/session contains export theories; AFP/HOL imports require the recorded Isabelle and AFP installation. Rust stages are generated crates; OCaml is the generated module. Harnesses and raw logs remain in the original run archive.')
    manifest_path = REPO / entry['artifact_manifest']
    if manifest_path.exists() and read(manifest_path) != manifest:
        raise ValueError('Published manifest differs; use a new experiment for changed inputs/results')
    write(manifest_path, manifest)
    # Task baselines are shared. Their manifest is independent of experiment identity.
    baseline_refs = {}
    for task in tasks:
        baseline_files = [dict(path=f['path'], sha256=f['sha256']) for f in files
                          if f['path'].startswith(f'test/afp/{task}/') and '/llm/' not in f['path']]
        baseline = dict(schema_version=1, task=task, files=baseline_files)
        baseline_path = AFP / task / 'baseline.json'
        if baseline_path.exists() and read(baseline_path) != baseline:
            raise ValueError(f'Shared baseline manifest differs: {task}')
        if not baseline_path.exists():
            write(baseline_path, baseline)
        baseline_refs[task] = dict(directory=f'test/afp/{task}',
                                   manifest=str(baseline_path.relative_to(REPO)),
                                   sha256=digest(baseline_path))
    summary.update(experiment_id=entry['experiment_id'], artifact_root='test/afp',
                   artifact_manifest=entry['artifact_manifest'], baseline_refs=baseline_refs,
                   candidates=candidates)
    write(summary_path, summary)
    return destination


def verify(identifier):
    entry = lookup(identifier)
    manifest = read(REPO/entry['artifact_manifest'])
    for item in manifest['files']:
        if digest(REPO/item['path']) != item['sha256']:
            raise ValueError(f"Artifact changed: {item['path']}")
    return len(manifest['files'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('register')
    p.add_argument('batch_id')
    p.add_argument('--title', required=True)
    for action in ['publish', 'verify']:
        sub.add_parser(action).add_argument('experiment_id')
    args = parser.parse_args()
    if args.action == 'register':
        print(register(args.batch_id, args.title)['experiment_id'])
    elif args.action == 'publish':
        print(publish(args.experiment_id))
    else:
        print(f'{args.experiment_id}: {verify(args.experiment_id)} files verified')


if __name__ == '__main__':
    main()
