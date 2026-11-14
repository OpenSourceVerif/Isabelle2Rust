"""Immutable, explicit case-to-run references for completed optimization runs.

Collections contain provenance only: no copied candidates, invented runs,
performance ranking, new search or reused timing samples. Direct-run resolution
and identity retain the matrix's previous behavior.
"""
import argparse
from collections.abc import Mapping
from pathlib import Path
import re

from .common import Failure, digest, read, save
from .task_context import fingerprint
from .translation_workflow import version


MANIFEST = 'optimization-sources.json'
MODES = {'rust-only', 'full'}
RUN_FILES = ('release.json', 'optimization-origin.json', 'optimization-report.json')
CASE_FILES = ('result.json', 'selected-state.json', 'scope-review/review.json', 'scope-review/selection.json')


def require(condition, code, detail):
    if not condition:
        raise Failure(code, str(detail))


def checked_file(path, expected=None):
    path = Path(path)
    require(path.is_file(), 'optimization_source_missing', path)
    actual = digest(path)
    require(expected is None or actual == expected, 'optimization_source_changed', path)
    return actual


def case_id(case):
    require(isinstance(case, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', case),
            'invalid_optimization_case', case)
    return case


def relative_file(name):
    require(isinstance(name, str), 'invalid_optimization_output_path', name)
    path = Path(name)
    require(not path.is_absolute() and '..' not in path.parts
            and name not in {'', '.'}, 'invalid_optimization_output_path', name)
    return path


def case_record(run, case, expected_mode=None):
    """Seal the original files and check their cross-links, without rewriting them."""
    run = Path(run).resolve(); case = case_id(case)
    require(not (run / MANIFEST).exists(), 'nested_optimization_collection', run)
    run_files = {name: checked_file(run / name) for name in RUN_FILES}
    release = read(run / 'release.json'); origin = read(run / 'optimization-origin.json')
    report = read(run / 'optimization-report.json')
    require(isinstance(release.get('identity'), str) and release['identity'], 'optimization_release_identity_missing', run)
    require(origin.get('release_identity') == release['identity'], 'optimization_release_mismatch', run)
    mode = origin.get('mode')
    require(mode in MODES and report.get('mode') == mode and (expected_mode is None or expected_mode == mode),
            'optimization_mode_mismatch', (case, expected_mode, mode))
    require(report.get('complete') is True, 'optimization_run_not_complete', run)
    reported = report.get('results')
    require(isinstance(reported, list) and all(isinstance(r, dict) and isinstance(r.get('case'), str) for r in reported),
            'optimization_report_invalid', run)
    require(len({r['case'] for r in reported}) == len(reported), 'duplicate_optimization_report_case', run)
    matches = [r for r in reported if r['case'] == case]
    require(len(matches) == 1, 'optimization_case_missing', (run, case))
    directory = run / 'optimization' / case
    files = {name: checked_file(directory / name) for name in CASE_FILES}
    result = read(directory / 'result.json'); state = read(directory / 'selected-state.json')
    require(result == matches[0] and result.get('case') == case and result.get('status') == 'complete'
            and result.get('mode') == mode, 'optimization_result_mismatch', (run, case))
    require(Path(result['selected_state']).resolve() == directory / 'selected-state.json'
            and result['selected_state_sha256'] == files['selected-state.json']
            and version(state) == result['selected_version'], 'optimization_selected_state_changed', case)
    scope = read(directory / 'scope-review/review.json'); selection = read(directory / 'scope-review/selection.json')
    if 'baseline_quality' in result or 'baseline_quality' in scope:
        require(result.get('baseline_quality') == scope.get('baseline_quality'),
                'optimization_baseline_quality_changed', case)
    link = result['scope_selection']; candidate = link.get('candidate')
    require(link['review_sha256'] == files['scope-review/review.json']
            and link['selection_sha256'] == files['scope-review/selection.json']
            and selection['review_sha256'] == files['scope-review/review.json']
            and selection['selected_candidate'] == candidate, 'optimization_scope_selection_changed', case)
    if result.get('improved'):
        validation = state.get('optimization_validation', {})
        require(candidate is not None and validation.get('status') == 'passed'
                and validation.get('candidate_version') == result['selected_version'],
                'optimization_selected_state_unvalidated', case)
        require(any(r.get('candidate_id') == candidate and r.get('decision') == 'within_scope'
                    for r in scope['reviews']), 'optimization_scope_unapproved', case)
        require(any(r.get('id') == candidate and r.get('version') == result['selected_version']
                    and r.get('source') == fingerprint(state['bundle']['source_model'])
                    for r in scope['identity']['candidates']), 'optimization_scope_version_changed', case)
    else:
        require(candidate is None and result['selected_version'] == result['baseline']['candidate_version'],
                'optimization_fallback_changed', case)
    output = Path(result['output']).resolve()
    require(output == directory / 'output', 'optimization_output_location_changed', case)
    output_files = result['output_files']
    require(isinstance(output_files, dict) and output_files, 'optimization_output_missing', case)
    actual_names = {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}
    require(actual_names == set(output_files), 'optimization_output_inventory_changed', case)
    for name, sha in output_files.items():
        checked_file(output / relative_file(name), sha)
    return {'run': str(run), 'mode': mode, 'release_identity': release['identity'],
            'run_files': run_files, 'files': files, 'selected_version': result['selected_version'],
            'selected_source_optimized': bool(result.get('selected_source_optimized')),
            'stage_schema': result.get('stage_schema'),
            'output': str(output), 'output_files': output_files}


def source_items(sources):
    items = list(sources.items()) if isinstance(sources, Mapping) else list(sources)
    require(items, 'empty_optimization_collection', 'Specify case-to-run references explicitly')
    rows = {}; ordered = []
    for item in items:
        require(isinstance(item, (tuple, list)) and len(item) == 2, 'invalid_optimization_reference', item)
        case, run = item; case_id(case)
        require(case not in rows, 'duplicate_optimization_case', case)
        rows[case] = run; ordered.append((case, Path(run).resolve()))
    return ordered


def plan_reference(plan):
    if plan is None:
        return None
    path = Path(plan).resolve()
    return {'path': str(path), 'sha256': checked_file(path)}


def validate_manifest(path, selected_case=None):
    data = read(path)
    require(data.get('schema') == 1 and data.get('mode') in MODES and isinstance(data.get('cases'), dict)
            and data['cases'], 'invalid_optimization_collection', path)
    require(isinstance(data.get('case_order'), list) and all(isinstance(c, str) for c in data['case_order'])
            and len(data['case_order']) == len(set(data['case_order']))
            and set(data['case_order']) == set(data['cases']), 'optimization_collection_case_order_changed', path)
    require(all(isinstance(r, dict) and isinstance(r.get('release_identity'), str)
                and isinstance(r.get('run'), str) for r in data['cases'].values()),
            'invalid_optimization_collection', path)
    identities = sorted({r['release_identity'] for r in data['cases'].values()})
    mixed = len(identities) > 1
    require(data.get('release_identities') == identities and data.get('mixed_controller_releases') == mixed,
            'optimization_collection_releases_changed', path)
    if mixed:
        require(isinstance(data.get('reason'), str) and data['reason'].strip() and data.get('plan'),
                'optimization_mixed_release_plan_required', path)
    if data.get('plan'):
        checked_file(data['plan']['path'], data['plan']['sha256'])
    for case, record in data['cases'].items():
        case_id(case)
        require(record['mode'] == data['mode'], 'optimization_mode_mismatch', case)
    if selected_case is not None:
        require(selected_case in data['cases'], 'optimization_case_missing', selected_case)
        targets = [selected_case]
    else:
        targets = data['case_order']
    for case in targets:
        record = data['cases'][case]
        # Comparing the reconstructed seal catches removed and newly added
        # output files as well as edits to all report/release/state/scope links.
        require(case_record(record['run'], case, data['mode']) == record,
                'optimization_collection_source_changed', case)
    return data


def identity(run):
    """Direct runs keep the previous optimization-report digest exactly."""
    run = Path(run).resolve(); path = run / MANIFEST
    if not path.exists():
        return digest(run / 'optimization-report.json')
    validate_manifest(path)
    return digest(path)


def resolve(run, case):
    """Resolve only explicit references; direct-run behavior is unchanged."""
    run = Path(run).resolve(); path = run / MANIFEST
    if not path.exists():
        return run
    data = validate_manifest(path, case)
    return Path(data['cases'][case]['run'])


def compose(sources, output, *, mode=None, reason=None, plan=None):
    """Compose caller-selected cases, never rank candidates or compare timings."""
    require(mode is None or mode in MODES, 'optimization_mode_mismatch', mode)
    pairs = source_items(sources); output = Path(output).resolve()
    require(all(not output.is_relative_to(run) and not run.is_relative_to(output) for _, run in pairs),
            'optimization_collection_overlaps_run', output)
    records = {}; effective_mode = mode
    for case, run in pairs:
        record = case_record(run, case, effective_mode)
        effective_mode = record['mode']; records[case] = record
    releases = sorted({r['release_identity'] for r in records.values()})
    mixed = len(releases) > 1; sealed_plan = plan_reference(plan)
    require(reason is None or isinstance(reason, str) and reason.strip(), 'invalid_optimization_collection_reason', reason)
    if mixed:
        require(reason and sealed_plan, 'optimization_mixed_release_plan_required', output)
    result = {'schema': 1, 'mode': effective_mode,
              'policy': 'Explicit immutable case-to-original-run references. No performance-based selection, copied candidates, invented runs, new optimization or reused timing samples.',
              'case_order': [case for case, _ in pairs], 'cases': records,
              'release_identities': releases, 'mixed_controller_releases': mixed,
              'reason': reason, 'plan': sealed_plan}
    path = output / MANIFEST
    if path.exists():
        validate_manifest(path)
        require(read(path) == result, 'optimization_collection_changed', path)
    else:
        require(not any((output / n).exists() for n in RUN_FILES), 'optimization_collection_is_run', output)
        save(path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', action='append', required=True, metavar='CASE=ORIGINAL_RUN')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=sorted(MODES))
    parser.add_argument('--reason')
    parser.add_argument('--plan', type=Path)
    args = parser.parse_args(); sources = []
    for spec in args.case:
        require('=' in spec, 'invalid_optimization_reference', spec)
        case, run = spec.split('=', 1)
        require(run, 'invalid_optimization_reference', spec)
        sources.append((case, run))
    result = compose(sources, args.output, mode=args.mode, reason=args.reason, plan=args.plan)
    print('Referenced', len(result['cases']), result['mode'], 'cases from', len(result['release_identities']), 'sealed releases')


if __name__ == '__main__':
    main()
