#!/usr/bin/env python3
"""Supplementary, within-Full A0 -> S -> Full measurements.

S is the first accepted source rewrite PLUS its required validated Rust
realization, not pure HOL execution or isolated theorem-proving benefit.
Default check freezes evidence only. --action measure explicitly builds S's
numeric pair and collects fresh samples for all unique stage executables.
No model calls, candidate edits, test generation or reference executions.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from i2r_agent.common import ROOT, Executor, Failure, digest, now, read, save
from i2r_agent import kernel_build, kernel_timing, timing_drivers
from i2r_agent import numeric_experiment as numeric, numeric_interface as interface
from i2r_agent import optimization_scope, source_optimization, segmented_config, translation_workflow
from i2r_agent import optimization_matrix, optimization_protocol
from i2r_agent.optimization_matrix import executable_identity, selected
from i2r_agent.segmented_config import materialize
from i2r_agent.task_context import fingerprint
from i2r_agent.translation_workflow import compile_crate, connection, version


STAGES = ('A0', 'S', 'Full')
BACKENDS = ('arbitrary', 'checked')
LABEL = 'S = source rewrite plus required Rust realization'
OPTIONS = {**kernel_timing.DEFAULTS, 'processes': 6, 'order_design': 'williams',
           'samples_per_process': 10, 'short_batch_samples': 40}


def require(condition, code, detail):
    if not condition:
        raise Failure(code, str(detail))


class Evidence:
    def __init__(self):
        self.files = {}

    def file(self, path, expected=None):
        path = Path(path).resolve()
        require(path.is_file(), 'stage_evidence_missing', path)
        actual = digest(path)
        require(expected is None or actual == expected, 'stage_evidence_changed', path)
        self.files[str(path)] = actual
        return actual

    def json(self, path, expected=None):
        self.file(path, expected)
        return read(path)

    def hashes(self, values):
        for path, sha in values.items():
            self.file(path, sha)


def immutable_json(path, value):
    if path.exists():
        require(read(path) == value, 'source_stage_snapshot_changed', path)
    else:
        save(path, value)


def materialized_hashes(files, connector=False):
    prefixes = {'src/lib.rs', 'src/main.rs'} if connector else {'src/lib.rs'}
    return {n: hashlib.sha256((('#![forbid(unsafe_code)]\n' if n in prefixes else '') + text).encode()).hexdigest()
            for n, text in files.items()}


def check_build(path, evidence):
    built = evidence.json(path)
    evidence.hashes(built['source_hashes']); evidence.hashes(built['artifact_hashes'])
    evidence.file(kernel_build.__file__, built['builder_identity']['builder'])
    evidence.file(timing_drivers.__file__, built['builder_identity']['drivers'])
    sha = evidence.file(built['binary'])
    require(built['artifact_hashes'].get(built['binary']) == sha, 'stage_unsealed_binary', path)
    return built


def audit_source(original, intermediate, final, result, evidence):
    record = intermediate['record']; state = intermediate['state']; path = Path(record['path'])
    require(record.get('stage') == 'source' and record['status'] == 'accepted', 'stage_not_source_acceptance', path)
    require(record['parent_version'] == version(original), 'source_first_parent_changed', path)
    proof = state['bundle'].get('source_equivalence')
    require(proof and proof == final['bundle'].get('source_equivalence'), 'source_stage_proof_changed', path)
    proofpath = Path(proof['directory'])
    require(evidence.json(proofpath / 'proof.json') == proof, 'stage_proof_record_changed', path)
    require(proof['status'] == 'proved' and proof['skip_proofs'] is False and proof['oracle_dependencies'] == [],
            'stage_proof_not_checked', path)
    require(proof['original_source_hashes'] == original['bundle']['source_hashes'], 'stage_proof_source_changed', path)
    theory = proofpath / 'project/Optimization.thy'; evidence.file(theory)
    require(fingerprint(theory.read_text()) == proof['theory_sha256'], 'stage_theory_changed', theory)
    extracted = evidence.json(proofpath / 'extraction/program.json')
    build = evidence.json(proofpath / 'extraction/source-build.json')
    require(build['status'] == 'passed' and build['returncode'] == 0, 'stage_proof_build_failed', proofpath)
    roots = proof['original_to_optimized']
    require(set(extracted['source_model']['entries']) == set(roots.values()), 'stage_export_roots_changed', path)
    types = source_optimization.preserve_export_types(original['bundle']['original_source_model'], extracted['source_model'], roots)
    require(types == proof['export_type_preservation'], 'stage_export_types_changed', path)
    require(fingerprint(extracted['source_model']) == fingerprint(state['bundle']['source_model']) == fingerprint(final['bundle']['source_model']),
            'stage_fixed_source_changed', path)
    summary = result['source_stage']
    require(summary['accepted'] and summary['accepted_candidate'] == intermediate['id'], 'stage_summary_changed', path)
    require(any(r.get('status') == 'source_proved' and r.get('proof') == proof for r in result['attempts']),
            'stage_proof_transition_missing', path)
    # choices() checks transaction, validation version and actual candidate files.
    for option in [intermediate]:
        link = option['record']['scope_admission']
        scope = evidence.json(link['path'], link['sha256'])
        require(scope['identity']['policy'] == fingerprint(optimization_scope.ONLINE_SYSTEM)
                and scope['identity']['version'] == version(state)
                and scope['identity']['source'] == fingerprint(state['bundle']['source_model'])
                and scope['review']['decision'] == 'within_scope', 'stage_scope_changed', path)
        for name in ['transaction.json', 'validation.json', 'result.json']:
            evidence.file(path / name)
    require(state['connector'] == original['connector'] and state['rust_config'] == original['rust_config'],
            'stage_interface_or_config_changed', path)
    require(state['optimization_validation']['source_tests']['status'] == 'passed', 'stage_frozen_tests_failed', path)


def canonical_build(matrix_case, result, validation, mode, backend, state, evidence):
    logical = mode + '-' + backend; canonical = result['executable_aliases'][logical]
    require(result['executable_aliases'].get(canonical) == canonical and canonical.endswith('-' + backend),
            'stage_matrix_alias_invalid', logical)
    require(validation['executable_aliases'] == result['executable_aliases'], 'stage_matrix_alias_changed', logical)
    lanes = validation['lanes'][logical]
    require({r['lane'] for r in lanes} == {'ordinary', 'kernel'} and all(r['status'] == 'passed' for r in lanes),
            'stage_matrix_validation_failed', logical)
    pair = validation['same_source_pairs'][mode][backend]
    require(pair['business'] == materialized_hashes(state['files'])
            and pair['connector'] == materialized_hashes(state['connector'], connector=True),
            'stage_matrix_program_changed', logical)
    path = matrix_case / 'builds' / canonical / 'timing/build-v2.json'
    built = check_build(path, evidence)
    require(built['case'] == result['case'] and built['id'] == canonical, 'stage_matrix_build_changed', logical)
    crate = Path(built['source'])
    require(evidence.json(crate / 'rust-config.json') == interface.backend_config(state['rust_config'], backend),
            'stage_numeric_configuration_changed', logical)
    for category, prefix in [('business', crate), ('connector', crate / 'harness'), ('runtime', crate)]:
        for name, sha in pair[category].items():
            evidence.file(prefix / name, sha)
    lock = crate / 'harness/Cargo.lock'; evidence.file(lock, validation['lock_sha256'][logical])
    return {'build': built, 'record': str(path), 'canonical': canonical, 'lanes': lanes,
            'lock': str(lock), 'lock_sha256': digest(lock), 'source_pair': pair}


def search_costs(result):
    budget = result['budget']; phase = budget['source_phase']; source = result['source_stage']
    initial = phase['start_seconds']; source_seconds = source['seconds']
    return {'total_model_calls': budget['calls'], 'total_charged_seconds': budget['charged_seconds'],
            'initial_preparation_seconds': initial, 'source_and_required_realization_calls': source['model_calls'],
            'source_and_required_realization_seconds': source_seconds,
            'later_rust_calls': budget['calls'] - phase['start_calls'] - source['model_calls'],
            'later_rust_seconds': max(0, budget['charged_seconds'] - initial - source_seconds),
            'total_resource_wait_seconds': budget.get('resource_wait_seconds', 0),
            'cost_scope': 'Search wall time includes model waits, proof, compilation, validation, scope admission, development measurement and resource queues. Source-stage cost includes required Rust realization, not only HOL proof cost.'}


def prepare(matrix, manifest, output):
    evidence = Evidence(); top = evidence.json(matrix / 'matrix.json')
    require(top.get('complete') is True, 'source_stages_complete_matrix_required', matrix)
    if (matrix / 'integrity-review.json').exists():
        review = evidence.json(matrix / 'integrity-review.json')
        require(not review.get('publication_hold') and review.get('status') != 'pending', 'source_stages_matrix_on_hold', matrix)
    dataset = {r['id']: r for r in evidence.json(manifest)['cases']}
    modules = [kernel_timing, kernel_build, timing_drivers, numeric, interface, optimization_scope,
               source_optimization, segmented_config, translation_workflow, optimization_matrix, optimization_protocol]
    for module in modules:
        evidence.file(module.__file__)
    evidence.file(__file__)
    plans = {}; skipped = []
    for result in top['results']:
        case = result['case']; full_result = result['selections']['full']
        if not full_result.get('selected_source_optimized'):
            skipped.append({'case': case, 'reason': 'No selected source transformation; no artificial S point.'})
            continue
        require(full_result.get('stage_schema') == 2 and full_result['status'] == 'complete', 'source_stages_schema2_required', case)
        row = dataset[case]; where = output / case; matrix_case = matrix / case
        require(evidence.json(matrix_case / 'result.json') == result and result['status'] == 'measured', 'stage_matrix_case_changed', case)
        seal = evidence.json(matrix_case / 'matrix-seal.json', result['matrix_seal_sha256'])
        for module in [kernel_timing, kernel_build, timing_drivers]:
            evidence.file(module.__file__, seal['timing_implementation'][module.__name__])
        original, cfg, observations, frozen = numeric.freeze(full_result['baseline']['baseline_run'], row, where / 'baseline')
        original_frozen = matrix_case / 'baseline/frozen.json'
        require(evidence.json(original_frozen, seal['baseline']) == frozen, 'stage_baseline_cohort_changed', case)
        baseline = Path(full_result['baseline']['baseline_run']) / 'tasks' / case / 'diagnostics'
        evidence.file(baseline / 'segmented-checkpoint.json', frozen['checkpoint_sha256'])
        evidence.file(baseline / 'effective-config.json')
        evidence.file(baseline / 'support-tests' / (original['support_evidence']['frozen_identity'] + '.json'))
        fullpath = Path(full_result['selected_state']).parent
        require(not output.is_relative_to(fullpath.parent.parent), 'stage_output_inside_formal_run', output)
        require(evidence.json(fullpath / 'result.json') == full_result, 'stage_full_result_changed', case)
        final, checked = selected(fullpath.parent.parent, case, original)
        require(checked == full_result and version(original) == seal['states']['off']
                and version(final) == seal['states']['full'], 'stage_selection_changed', case)
        evidence.file(fullpath / 'selected-state.json', full_result['selected_state_sha256'])
        for name, sha in full_result['output_files'].items():
            evidence.file(Path(full_result['output']) / name, sha)
        for name, key in [('review.json', 'review_sha256'), ('selection.json', 'selection_sha256')]:
            evidence.file(fullpath / 'scope-review' / name, full_result['scope_selection'][key])
        options = optimization_scope.choices(original, full_result['baseline'], full_result['attempts'])
        sources = [o for o in options if o['record'].get('stage') == 'source']
        require(len(sources) == 1, 'source_stages_exactly_one_source_acceptance', case)
        intermediate = sources[0]; audit_source(original, intermediate, final, full_result, evidence)
        states = {'A0': original, 'S': intermediate['state'], 'Full': final}
        workload = next(w for w in row['performance_workloads'] if w['id'] == row['primary_workload'])
        require(result['primary_workload'] == row['primary_workload'], 'stage_primary_workload_changed', case)
        validation = evidence.json(matrix_case / 'validation.json'); reused = {}
        for stage, mode in [('A0', 'off'), ('Full', 'full')]:
            for backend in BACKENDS:
                reused[stage + '-' + backend] = canonical_build(matrix_case, result, validation, mode, backend, states[stage], evidence)
        master = reused['A0-arbitrary']['lock']
        require(len({v['lock_sha256'] for v in reused.values()}) == 1, 'stage_matrix_dependencies_changed', case)
        # Check the completed primary measurement belongs to these binaries and inputs.
        prior = next(w for w in result['rows'] if w['workload'] == workload['id'])
        measured = evidence.json(prior['record'])
        require(measured['status'] == 'passed' and measured['workload'] == workload['input']
                and measured['identity']['expected'] == observations[('kernel', tuple(workload['input']))],
                'stage_primary_measurement_changed', case)
        for key, item in reused.items():
            require(measured['identity']['binaries'].get(item['canonical']) == digest(item['build']['binary'])
                    or any(workload['input'] in lane['range_exclusions'] for lane in item['lanes']),
                    'stage_primary_binary_changed', key)
        plans[case] = {'states': states, 'cfg': cfg, 'observations': observations, 'reused': reused,
                       'workload': workload, 'master_lock': master, 'source_attempt': intermediate['id'],
                       'search_costs': search_costs(full_result)}
    identity = {'schema': 1, 'matrix': str(matrix), 'label': LABEL, 'stage_order': list(STAGES),
                'options': OPTIONS, 'source_files_sha256': evidence.files, 'skipped': skipped,
                'cases': {case: {'workload': p['workload'], 'source_attempt': p['source_attempt'],
                    'versions': {k: version(s) for k, s in p['states'].items()},
                    'executable_identities': {stage + '-' + backend: executable_identity(s, backend)
                        for stage, s in p['states'].items() for backend in BACKENDS},
                    'canonical_matrix_builds': {k: v['record'] for k, v in p['reused'].items()},
                    'search_costs': p['search_costs']} for case, p in plans.items()},
                'interpretation': 'Supplementary within-Full stages, not the independently searched Rust-only versus Full main comparison. All timings are fresh; no feedback to search. S includes required Rust realization.',
                'model_calls': 0, 'reference_executions': 0, 'source_test_regenerations': 0}
    immutable_json(output / 'intent.json', identity)
    return plans, identity


@contextmanager
def resource_lock(exclusive, costs):
    path = ROOT / 'cache/timing-v2.lock'; path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        costs['resource_wait_seconds'] += time.monotonic() - started
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


class LockedExecutor(Executor):
    def run(self, argv, **kwargs):
        argv = list(argv)
        if any(x in argv for x in ['build', 'test', 'clippy']) and '--manifest-path' in argv and '--locked' not in argv:
            argv.append('--locked')
        return super().run(argv, **kwargs)


def prepare_builds(case, plan, where):
    cfg = deepcopy(plan['cfg']); cfg['translation']['correctness_only'] = False
    cfg['translation']['performance_refinement'] = False
    builds = {}; aliases = {}; identities = {}; validation = {}; pairs = {}; exclusions = {}; locks = {}
    # Prefer already-built A0/Full. S aliases either one only on exact executable input identity.
    for stage in ['A0', 'Full', 'S']:
        state = plan['states'][stage]; pairs[stage] = {}
        for backend in BACKENDS:
            key = stage + '-' + backend; identity = executable_identity(state, backend)
            if identity in identities:
                canonical = identities[identity]; aliases[key] = canonical
                validation[key] = validation[canonical]; exclusions[key] = exclusions[canonical]
                locks[key] = locks[canonical]
                prior_stage, prior_backend = canonical.rsplit('-', 1)
                pairs[stage][backend] = pairs[prior_stage][prior_backend]
                continue
            identities[identity] = key; aliases[key] = key
            if key in plan['reused']:
                old = plan['reused'][key]
                builds[key] = {**old['build'], 'id': key}
                validation[key] = old['lanes']; pairs[stage][backend] = old['source_pair']; locks[key] = old['lock_sha256']
            else:
                work = where / 'builds' / key; rc = interface.backend_config(state['rust_config'], backend)
                crate = materialize(work / 'candidate', state['files'], rc)
                harness = connection(crate, state['connector'], rc, cfg)
                shutil.copyfile(plan['master_lock'], harness / 'Cargo.lock')
                executor = LockedExecutor(work / 'commands')
                compiled = compile_crate(harness, rc, cfg, executor, False)
                require(compiled['status'] == 'passed', 'source_stage_compile_failed', key)
                validation[key] = [numeric.validate_lane(compiled['binary'], plan['observations'], lane, backend,
                    executor, cfg['testing']['process_timeout']) for lane in ['ordinary', 'kernel']]
                pairs[stage][backend] = {'business': {n: digest(crate / n) for n in state['files']},
                    'connector': {n: digest(harness / n) for n in state['connector']},
                    'runtime': {n: digest(crate / n) for n in interface.managed_runtime(rc)}}
                require(pairs[stage][backend]['business'] == materialized_hashes(state['files'])
                        and pairs[stage][backend]['connector'] == materialized_hashes(state['connector'], connector=True),
                        'stage_materialized_source_changed', key)
                locks[key] = digest(harness / 'Cargo.lock')
                require(locks[key] == digest(plan['master_lock']), 'stage_dependencies_changed', key)
                builds[key] = kernel_build.build({'id': key, 'case': case, 'language': 'rust', 'kind': 'llm',
                    'source': str(crate), 'work': str(work / 'timing')}, cfg)
                require(digest(work / 'timing/crate/harness/Cargo.lock') == locks[key], 'stage_timing_dependencies_changed', key)
            exclusions[key] = {tuple(x) for lane in validation[key] for x in lane['range_exclusions']}
        require(pairs[stage]['arbitrary'] == pairs[stage]['checked'], 'stage_numeric_source_changed', stage)
    require(len(set(locks.values())) == 1, 'stage_dependency_pair_changed', case)
    report = {'lanes': validation, 'same_source_pairs': pairs, 'lock_sha256': locks, 'executable_aliases': aliases,
              'frozen_source_tests_reused': plan['states']['S']['optimization_validation']['source_tests'],
              'source_tests_policy': 'Reuse already-passed S source-contract evidence; newly compiled backend binaries replay cached reference outputs. Arbitrary-only large-number tests are not regenerated for checked.',
              'reference_executions': 0, 'model_calls': 0}
    save(where / 'validation.json', report)
    return builds, aliases, exclusions


def ratio(before, after):
    interval = numeric.interval(before, after)
    return {'runtime_ratio': after['median_ns'] / before['median_ns'],
            'runtime_ratio_ci95': [1 / interval[1], 1 / interval[0]],
            'speedup': before['median_ns'] / after['median_ns'], 'speedup_ci95': interval}


def measure_case(case, plan, identity, output):
    where = output / case; where.mkdir(parents=True, exist_ok=True)
    finished = where / 'result.json'; intent_sha = digest(output / 'intent.json')
    if finished.exists():
        result = read(finished)
        require(result['intent_sha256'] == intent_sha, 'stage_measurement_identity_changed', case)
        Evidence().file(result['record'], result['record_sha256'])
        Evidence().file(where / 'validation.json', result['validation_sha256'])
        return result
    costs = {'resource_wait_seconds': 0, 'preparation_seconds': 0, 'measurement_seconds': 0}
    with resource_lock(False, costs):
        started = time.monotonic(); Evidence().hashes(identity['source_files_sha256'])
        builds, aliases, excluded = prepare_builds(case, plan, where)
        costs['preparation_seconds'] = time.monotonic() - started
    values = plan['workload']['input']; measurement = where / 'measurements'
    available = [{**b, 'work': str(measurement / key)} for key, b in builds.items() if tuple(values) not in excluded[key]]
    options = {**OPTIONS, 'processes': kernel_timing.balanced_rounds(len(available), 6)}
    with resource_lock(True, costs):
        started = time.monotonic(); Evidence().hashes(identity['source_files_sha256'])
        for b in builds.values():
            Evidence().hashes(b['source_hashes']); Evidence().hashes(b['artifact_hashes'])
        measured = kernel_timing.measure_group(case, available, values,
            plan['observations'][('kernel', tuple(values))], options, measurement)
        costs['measurement_seconds'] = time.monotonic() - started
        Evidence().hashes(identity['source_files_sha256'])
    expanded = {key: measured['summary'][canonical] for key, canonical in aliases.items() if canonical in measured['summary']}
    ratios = {}
    for backend in BACKENDS:
        for name, before, after in [('S/A0', 'A0', 'S'), ('Full/S', 'S', 'Full'), ('Full/A0', 'A0', 'Full')]:
            a, b = before + '-' + backend, after + '-' + backend
            if a in expanded and b in expanded:
                ratios[name + '-' + backend] = ratio(expanded[a], expanded[b])
    result = {'case': case, 'status': 'measured', 'label': LABEL, 'primary_workload': plan['workload']['id'],
              'source_attempt': plan['source_attempt'], 'median_ns': {k: v['median_ns'] for k, v in expanded.items()},
              'stage_ratios': ratios, 'executable_aliases': aliases,
              'ratio_convention': 'S/A0 and Full/S name runtime ratios (lower is better); speedup is the reciprocal (higher is better).',
              'interval_method': '95% percentile paired process-round bootstrap via numeric_experiment.interval; 2000 fixed-seed resamples. Identical aliased cells retain the same observations.',
              'alias_policy': 'Exact business/connector/backend configuration identity shares one binary and the same new samples, never independent observations.',
              'range_excluded': [k for k in aliases if k not in expanded], 'unique_measured_executables': len(available),
              'process_rounds': options['processes'], 'record': str(measurement / 'measurement-v2.json'),
              'record_sha256': digest(measurement / 'measurement-v2.json'),
              'validation_sha256': digest(where / 'validation.json'),
              'search_costs': plan['search_costs'], 'supplementary_experiment_costs': costs,
              'intent_sha256': intent_sha, 'model_calls': 0, 'reference_executions': 0, 'measured_at': now()}
    save(finished, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=ROOT.parent / 'artifact/datasets/performance/manifest.json')
    parser.add_argument('--action', choices=['check', 'measure'], default='check')
    args = parser.parse_args(); matrix = args.matrix.resolve(); output = args.output.resolve()
    require(not output.is_relative_to(matrix) and not matrix.is_relative_to(output), 'stage_separate_output_required', output)
    # Reject protected destinations before even check mode freezes evidence.
    for row in read(matrix / 'matrix.json')['results']:
        selection = row['selections']['full']
        for protected in [Path(selection['selected_state']).resolve().parents[2],
                          Path(selection['baseline']['baseline_run']).resolve()]:
            require(not output.is_relative_to(protected) and not protected.is_relative_to(output),
                    'stage_output_overlaps_formal_run', output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'controller.lock').open('a+') as controller:
        fcntl.flock(controller, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plans, identity = prepare(matrix, args.manifest.resolve(), output)
        if args.action == 'check':
            print('Checked', len(plans), 'selected source-optimized cases; no builds or timing. ' + LABEL)
            return
        results = []
        for case, plan in plans.items():
            results.append(measure_case(case, plan, identity, output))
            save(output / 'source-first-stages.json', {'complete': False, 'label': LABEL, 'results': results})
        save(output / 'source-first-stages.json', {'complete': True, 'label': LABEL,
            'results': results, 'skipped': identity['skipped'], 'intent_sha256': digest(output / 'intent.json'),
            'model_calls': 0, 'reference_executions': 0})
        print('Measured', len(results), 'within-Full stage comparisons; main RQ2 selections unchanged.')


if __name__ == '__main__':
    main()
