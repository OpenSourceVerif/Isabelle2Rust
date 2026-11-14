"""Independent final 3-by-2 measurements from frozen selected implementations."""
import argparse
from copy import deepcopy
from pathlib import Path
import fcntl
import math
import shutil
import statistics
from .common import ROOT, Executor, Failure, digest, read, save
from . import numeric_experiment as numeric, numeric_interface as interface, optimization_baseline_quality as baseline_quality
from .experiment_baselines import identity as baseline_identity
from .optimization_experiments import identity as optimization_identity, resolve as optimization_resolve
from .segmented_config import materialize
from .translation_workflow import compile_crate, connection, version
from .kernel_build import build
from .kernel_timing import DEFAULTS, measure_group, balanced_rounds
from .task_context import fingerprint


def executable_identity(state, backend):
    """Context labels do not create new programs; all executable inputs do."""
    return fingerprint({'files':state['files'],'connector':state['connector'],
                        'rust_config':interface.backend_config(state['rust_config'],backend)})


def expand_aliases(measured,aliases,path):
    """Expose matrix cells backed by one measured executable, without fake runs."""
    result=deepcopy(measured)
    result['measurement_origin']=str(Path(path)/'measurement-v2.json')
    result['executable_aliases']={k:v for k,v in aliases.items() if v in measured['summary']}
    result['alias_policy']='Byte-identical business/connector/runtime configuration is built and measured once per numeric backend. Aliased cells share the same observations, not independent samples.'
    for field in ['summary','processes']:
        result[field]={k:measured[field][v] for k,v in result['executable_aliases'].items()}
    save(Path(path)/'matrix-measurement.json',result)
    return result


def selected(run, case, original):
    run = optimization_resolve(run, case)
    directory = Path(run) / 'optimization' / case
    result = read(directory / 'result.json'); statepath = directory / 'selected-state.json'
    if result['status'] != 'complete' or digest(statepath) != result['selected_state_sha256']:
        raise Failure('optimization_selection_changed', case)
    if any(digest(Path(result['output']) / n) != sha for n, sha in result['output_files'].items()):
        raise Failure('optimization_output_changed', case)
    state = read(statepath)
    if version(state) != result['selected_version'] or state['connector'] != original['connector'] or state['rust_config'] != original['rust_config']:
        raise Failure('optimization_selection_changed', case)
    if result['baseline']['candidate_version'] != version(original):
        raise Failure('optimization_baseline_mismatch', case)
    review = result.get('scope_selection', {})
    if (digest(directory / 'scope-review/review.json') != review.get('review_sha256') or
            digest(directory / 'scope-review/selection.json') != review.get('selection_sha256')):
        raise Failure('optimization_scope_review_changed', case)
    audit = read(directory / 'scope-review/review.json')
    if result.get('baseline_quality') != audit.get('baseline_quality'):
        raise Failure('optimization_baseline_quality_changed', case)
    if result['improved']:
        accepted = review.get('candidate')
        if not any(r['candidate_id'] == accepted and r['decision'] == 'within_scope' for r in audit['reviews']):
            raise Failure('optimization_scope_unapproved', case)
        if not any(r['id'] == accepted and r['version'] == version(state) and
                   r['source'] == fingerprint(state['bundle']['source_model'])
                   for r in audit['identity']['candidates']):
            raise Failure('optimization_scope_version_changed', case)
        evidence = state.get('optimization_validation', {})
        if evidence.get('status') != 'passed' or evidence.get('candidate_version') != version(state):
            raise Failure('optimization_selection_unvalidated', case)
    elif state['files'] != original['files']:
        raise Failure('optimization_selection_unvalidated', case)
    # A legacy positive review cannot bypass the current frozen trait contract
    # when its artifact is reused for a new measurement. Preserve its old files.
    from .optimization_protocol import ensure_public_trait_members
    ensure_public_trait_members(original['files'], state['files'])
    return state, result


def quality_review(results, output):
    """New automatic report; never overwrite an independent integrity review."""
    output = Path(output)
    manual = output / 'integrity-review.json'
    external = ({'path': str(manual), 'sha256': digest(manual),
                 'publication_hold': bool(read(manual).get('publication_hold'))} if manual.exists() else None)
    held = [r['case'] for r in results if r.get('publication_hold')]
    value = {'schema': 1, 'producer': baseline_quality.POLICY,
             'status': 'publication_hold' if held or (external and external['publication_hold']) else 'no_recorded_root_hold',
             'publication_hold': bool(held or (external and external['publication_hold'])),
             'held_cases': held, 'affected_modes': baseline_quality.MODES,
             'external_integrity_review': external,
             'cases': {r['case']: r.get('baseline_quality', {'status': 'legacy_no_findings_record'}) for r in results},
             'claim': 'No recorded hold is not a new correctness proof. Baseline findings from either arm apply to every mode of that baseline; no aggregate publication comparison is produced while any case is held.'}
    path = output / 'baseline-quality-review.json'
    if path.exists() and read(path).get('publication_hold') and not value['publication_hold']:
        return read(path)  # No automatic clearing of a previously recorded hold.
    save(path, value)
    return value


def measure_case(baseline, rust, full, row, directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    original, cfg, observations, seal = numeric.freeze(baseline, row, directory / 'baseline')
    states = {'off': original}; selections = {}
    for key, run in [('rust-only', rust), ('full', full)]:
        states[key], selections[key] = selected(run, row['id'], original)
    quality = baseline_quality.merge_selected(original, selections)
    save(directory / 'baseline-quality-review.json', quality)
    manual = directory.parent / 'integrity-review.json'
    external_hold = manual.exists() and bool(read(manual).get('publication_hold'))
    if quality['publication_hold'] or external_hold:
        held = {'case': row['id'], 'status': 'publication_hold', 'publication_hold': True,
                'affected_modes': baseline_quality.MODES, 'baseline_quality': quality, 'rows': [],
                'selections': selections, 'model_calls': 0, 'reference_executions': 0,
                'external_integrity_review': {'path': str(manual), 'sha256': digest(manual)} if external_hold else None}
        save(directory / 'publication-hold.json', held)
        return held
    cfg = deepcopy(cfg); cfg['translation']['correctness_only'] = False
    from . import kernel_timing, kernel_build, timing_drivers
    seal = {'baseline': digest(directory / 'baseline/frozen.json'),
            'baseline_quality_sha256': digest(directory / 'baseline-quality-review.json'),
            'timing_implementation':{m.__name__:digest(m.__file__) for m in [kernel_timing,kernel_build,timing_drivers]},
            'states': {k: version(v) for k, v in states.items()},
            'selected_state_files': {k: r['selected_state_sha256'] for k, r in selections.items()},
            'controller': digest(__file__), 'protocol_options': {**DEFAULTS, **cfg['performance'].get('v2', {}),
                                                                 'processes': 6, 'order_design':'williams', 'short_batch_samples':40},
            'executable_reuse':'identical business, connector and backend configuration share one build and measurement'}
    sealpath = directory / 'matrix-seal.json'
    if sealpath.exists() and read(sealpath) != seal:
        raise Failure('matrix_changed', str(directory))
    save(sealpath, seal)
    finished = directory / 'result.json'
    if finished.exists():
        cached = read(finished)
        if cached.get('baseline_quality') != quality or cached.get('publication_hold') is not False:
            raise Failure('matrix_baseline_quality_changed', str(finished))
        return cached
    builds = {}; excluded = {}; validation = {}; source_pairs = {}; lock_hashes = {}; identities={}; aliases={}
    for mode, state in states.items():
        source_pairs[mode] = {}
        for backend in ['arbitrary', 'checked']:
            key = mode + '-' + backend; path = directory / 'builds' / key
            identity=executable_identity(state,backend)
            if identity in identities:
                canonical=identities[identity];aliases[key]=canonical
                validation[key]=validation[canonical];excluded[key]=excluded[canonical]
                lock_hashes[key]=lock_hashes[canonical]
                prior_mode,prior_backend=canonical.rsplit('-',1)
                source_pairs[mode][backend]=source_pairs[prior_mode][prior_backend]
                continue
            identities[identity]=key;aliases[key]=key
            rc = interface.backend_config(state['rust_config'], backend)
            crate = materialize(path / 'candidate', state['files'], rc)
            harness = connection(crate, state['connector'], rc, cfg)
            master = directory / 'builds/off-arbitrary/candidate/harness/Cargo.lock'
            if key != 'off-arbitrary':
                shutil.copyfile(master, harness / 'Cargo.lock')
            executor = Executor(path / 'commands')
            compiled = compile_crate(harness, rc, cfg, executor, False)
            if compiled['status'] != 'passed':
                raise Failure('matrix_compile_failed', key, compiled)
            validation[key] = [numeric.validate_lane(compiled['binary'], observations, lane, backend,
                                                     executor, cfg['testing']['process_timeout']) for lane in ['ordinary', 'kernel']]
            excluded[key] = {tuple(x) for lane in validation[key] for x in lane['range_exclusions']}
            lock_hashes[key] = digest(harness / 'Cargo.lock')
            source_pairs[mode][backend] = {'business': {n: digest(crate / n) for n in state['files']},
                                          'connector': {n: digest(harness / n) for n in state['connector']},
                                          'runtime': {n: digest(crate / n) for n in interface.managed_runtime(rc)}}
            builds[key] = build({'id': key, 'case': row['id'], 'language': 'rust', 'kind': 'llm',
                                  'source': str(crate), 'work': str(path / 'timing')}, cfg)
        if source_pairs[mode]['arbitrary'] != source_pairs[mode]['checked']:
            raise Failure('matrix_numeric_source_changed', mode)
    if len(set(lock_hashes.values())) != 1:
        raise Failure('matrix_dependencies_changed', row['id'])
    save(directory / 'validation.json', {'lanes': validation, 'same_source_pairs': source_pairs,
                                        'lock_sha256': lock_hashes, 'executable_aliases':aliases,
                                        'reference_executions': 0, 'model_calls': 0})
    rows = []
    for workload in row['performance_workloads']:
        path = directory / 'measurements' / workload['id']; values = workload['input']
        available = [{**b, 'work': str(path / key)} for key, b in builds.items() if tuple(values) not in excluded[key]]
        options={**seal['protocol_options'],'processes':balanced_rounds(len(available),seal['protocol_options']['processes'])}
        measured = measure_group(row['id'], available, values, observations[('kernel', tuple(values))],
                                 options, path)
        measured = expand_aliases(measured,aliases,path)
        summary = measured['summary']; ratios = {}
        for backend in ['arbitrary', 'checked']:
            for mode in ['rust-only', 'full']:
                a, b = 'off-' + backend, mode + '-' + backend
                if a in summary and b in summary:
                    ratios[mode + '-vs-off-' + backend] = {
                        'speedup': summary[a]['median_ns'] / summary[b]['median_ns'],
                        'ci95': numeric.interval(summary[a], summary[b])}
        for mode in states:
            a, b = mode + '-arbitrary', mode + '-checked'
            if a in summary and b in summary:
                ratios[mode + '-numeric'] = {'speedup': summary[a]['median_ns'] / summary[b]['median_ns'],
                                             'ci95': numeric.interval(summary[a], summary[b])}
        rows.append({'workload': workload['id'], 'median_ns': {k: v['median_ns'] for k, v in summary.items()},
                     'ratios': ratios, 'range_excluded': [k for k in aliases if k not in summary],
                     'executable_aliases':measured['executable_aliases'],
                     'record': str(path / 'matrix-measurement.json')})
    result = {'case': row['id'], 'primary_workload': row['primary_workload'], 'status': 'measured',
              'rows': rows, 'selections': selections, 'same_source_within_numeric_pair': True,
              'publication_hold': False, 'baseline_quality': quality,
              'unique_executables':len(builds),'executable_aliases':aliases,
              'reference_executions': 0, 'model_calls': 0, 'matrix_seal_sha256': digest(sealpath)}
    save(finished, result); return result


def run(baseline, rust, full, rows, output):
    baseline, rust, full, output = (Path(p).resolve() for p in (baseline, rust, full, output))
    output.mkdir(parents=True, exist_ok=True)
    origin = {'baseline_identity': baseline_identity(baseline), 'cases': [r['id'] for r in rows],
              'optimization_reports': {k: optimization_identity(v) for k, v in [('rust-only', rust), ('full', full)]},
              'selection': 'Arbitrary-only development search; at least six fresh process rounds per unique executable, complete Williams-balanced cycles for each workload; identical fallback cells share measurements; no final feedback to search'}
    if (output / 'origin.json').exists() and read(output / 'origin.json') != origin:
        raise Failure('matrix_origin_changed', str(output))
    save(output / 'origin.json', origin)
    results = []; lockpath = ROOT / 'cache/timing-v2.lock'; lockpath.parent.mkdir(parents=True, exist_ok=True)
    with (output / 'controller.lock').open('a+') as controller, lockpath.open('a+') as timing:
        fcntl.flock(controller, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.flock(timing, fcntl.LOCK_EX)
        for row in rows:
            results.append(measure_case(baseline, rust, full, row, output / row['id']))
            review = quality_review(results, output)
            save(output / 'matrix.json', {'complete': False, 'publication_hold': review['publication_hold'],
                                         'held_cases': review['held_cases'], 'results': results})
    review = quality_review(results, output)
    if review['publication_hold']:
        report = {'complete': False, 'status': 'publication_hold', 'publication_hold': True,
                  'measured': sum(r.get('status') == 'measured' for r in results),
                  'held_cases': review['held_cases'], 'results': results, 'primary_geomean_speedups': {},
                  'baseline_quality_review_sha256': digest(output / 'baseline-quality-review.json')}
        save(output / 'matrix.json', report)
        return report
    primary = [next(w for w in r['rows'] if w['workload'] == r['primary_workload']) for r in results]
    keys = set.intersection(*(set(p['ratios']) for p in primary))
    report = {'complete': True, 'publication_hold': False, 'measured': len(results), 'results': results,
              'baseline_quality_review_sha256': digest(output / 'baseline-quality-review.json'),
              'primary_geomean_speedups': {k: math.exp(statistics.mean(math.log(p['ratios'][k]['speedup']) for p in primary)) for k in sorted(keys)}}
    save(output / 'matrix.json', report); return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['baseline', 'rust', 'full', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=ROOT.parent / 'artifact/datasets/performance/manifest.json')
    args = parser.parse_args()
    result = run(args.baseline, args.rust, args.full, read(args.manifest)['cases'], args.output)
    print('Measured', result['measured'], 'case matrices; status:', result.get('status', 'complete'))
