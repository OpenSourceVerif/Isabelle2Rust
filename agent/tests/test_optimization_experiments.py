"""Provenance-only optimization collections: no search or timing in these tests."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from i2r_agent.common import Failure, digest, read, save
from i2r_agent.task_context import fingerprint
from i2r_agent.translation_workflow import version


from i2r_agent import optimization_experiments as sources
from i2r_agent import optimization_matrix as matrix


class ReferenceCollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def run_fixture(self, name, *, case='alpha', mode='rust-only', release='release-1', improved=True):
        """Entirely synthetic local unit fixture, never a formal experiment."""
        run = self.root / name; directory = run / 'optimization' / case
        original = {'files': {'src/lib.rs': 'pub fn f() -> u8 { 0 + 0 }'}, 'mapping': {'root': 'f'},
                    'rust_config': {'numeric': 'arbitrary'}, 'partition': [],
                    'connector': {'src/main.rs': 'frozen observer'},
                    'bundle': {'source_model': {'root': 'f'}}}
        state = deepcopy(original)
        if improved:
            state['files']['src/lib.rs'] = 'pub fn f() -> u8 { 0 }'
            state['optimization_validation'] = {'status': 'passed', 'candidate_version': version(state)}
        save(directory / 'selected-state.json', state)
        cid = '002' if improved else None
        review = {'identity': {'candidates': ([{'id': cid, 'version': version(state),
                  'source': fingerprint(state['bundle']['source_model'])}] if improved else [])},
                  'reviews': ([{'candidate_id': cid, 'decision': 'within_scope'}] if improved else [])}
        save(directory / 'scope-review/review.json', review)
        review_sha = digest(directory / 'scope-review/review.json')
        save(directory / 'scope-review/selection.json', {'selected_candidate': cid, 'review_sha256': review_sha})
        output = directory / 'output'; (output / 'src').mkdir(parents=True)
        (output / 'src/lib.rs').write_text(state['files']['src/lib.rs'])
        (output / 'Cargo.lock').write_text('frozen dependencies')
        result = {'case': case, 'mode': mode, 'status': 'complete', 'stage_schema': 2,
                  'improved': improved, 'selected_source_optimized': False,
                  'selected_state': str(directory / 'selected-state.json'),
                  'selected_state_sha256': digest(directory / 'selected-state.json'),
                  'selected_version': version(state), 'baseline': {'candidate_version': version(original)},
                  'scope_selection': {'candidate': cid, 'review_sha256': review_sha,
                    'selection_sha256': digest(directory / 'scope-review/selection.json')},
                  'output': str(output), 'output_files': {
                    'src/lib.rs': digest(output / 'src/lib.rs'), 'Cargo.lock': digest(output / 'Cargo.lock')}}
        save(directory / 'result.json', result)
        save(run / 'release.json', {'identity': release})
        save(run / 'optimization-origin.json', {'mode': mode, 'release_identity': release})
        save(run / 'optimization-report.json', {'mode': mode, 'complete': True, 'results': [result]})
        return run, original, state

    def compose(self, run, **kwargs):
        return sources.compose([('alpha', run)], self.root / 'collection', **kwargs)

    def assert_fails(self, fn, code=None):
        with self.assertRaises(Failure) as caught:
            fn()
        if code:
            self.assertEqual(caught.exception.code, code)

    def test_references_original_files_only_and_matrix_restores_same_state(self):
        run, original, expected = self.run_fixture('run')
        before = {str(p.relative_to(run)): digest(p) for p in run.rglob('*') if p.is_file()}
        record = self.compose(run)
        collection = self.root / 'collection'
        self.assertEqual(sources.resolve(collection, 'alpha'), run)
        self.assertEqual(sources.identity(collection), digest(collection / sources.MANIFEST))
        self.assertEqual(record['cases']['alpha']['release_identity'], 'release-1')
        self.assertEqual(record['cases']['alpha']['run_files']['optimization-report.json'], digest(run / 'optimization-report.json'))
        self.assertEqual([p.name for p in collection.iterdir()], [sources.MANIFEST])
        self.assertEqual(before, {str(p.relative_to(run)): digest(p) for p in run.rglob('*') if p.is_file()})
        from_collection = matrix.selected(collection, 'alpha', original)
        from_direct = matrix.selected(run, 'alpha', original)
        self.assertEqual(from_collection, from_direct)
        self.assertEqual(from_collection[0], expected)

    def test_direct_identity_and_resolve_preserve_previous_behavior(self):
        run = self.root / 'old-layout'
        save(run / 'optimization-report.json', {'legacy': 'no new artifact requirements'})
        self.assertEqual(sources.identity(run), digest(run / 'optimization-report.json'))
        self.assertEqual(sources.resolve(run, 'case-that-is-not-checked-here'), run)

    def test_idempotent_compose_is_byte_stable(self):
        run, _, _ = self.run_fixture('run')
        result = self.compose(run); before = sources.identity(self.root / 'collection')
        self.assertEqual(self.compose(run), result)
        self.assertEqual(sources.identity(self.root / 'collection'), before)

    def test_existing_collection_cannot_be_repointed(self):
        old, _, _ = self.run_fixture('old'); new, _, _ = self.run_fixture('new')
        self.compose(old)
        self.assert_fails(lambda: self.compose(new), 'optimization_collection_changed')

    def test_missing_duplicate_and_invalid_case_rejected(self):
        run, _, _ = self.run_fixture('run')
        self.assert_fails(lambda: sources.compose([], self.root / 'empty'), 'empty_optimization_collection')
        self.assert_fails(lambda: sources.compose([('alpha', run), ('alpha', run)], self.root / 'dup'), 'duplicate_optimization_case')
        self.assert_fails(lambda: sources.compose([('missing', run)], self.root / 'missing'), 'optimization_case_missing')
        self.assert_fails(lambda: sources.compose([('../alpha', run)], self.root / 'bad'), 'invalid_optimization_case')
        self.compose(run)
        self.assert_fails(lambda: sources.resolve(self.root / 'collection', 'missing'), 'optimization_case_missing')

    def test_modes_cannot_be_combined_even_with_mixed_release_plan(self):
        rust, _, _ = self.run_fixture('rust')
        full, _, _ = self.run_fixture('full', case='beta', mode='full')
        plan = self.root / 'plan.txt'; plan.write_text('A registered cohort correction, not ranking by speed.')
        self.assert_fails(lambda: sources.compose([('alpha', rust), ('beta', full)], self.root / 'mixed',
                          reason='registered correction', plan=plan), 'optimization_mode_mismatch')
        self.assert_fails(lambda: self.compose(rust, mode='full'), 'optimization_mode_mismatch')

    def test_mixed_releases_require_reason_and_sealed_plan(self):
        one, _, _ = self.run_fixture('one')
        two, _, _ = self.run_fixture('two', case='beta', release='release-2')
        refs = [('alpha', one), ('beta', two)]
        plan = self.root / 'plan.txt'; plan.write_text('Use predetermined replacements because of a controller fix.')
        self.assert_fails(lambda: sources.compose(refs, self.root / 'missing-both'), 'optimization_mixed_release_plan_required')
        self.assert_fails(lambda: sources.compose(refs, self.root / 'missing-plan', reason='controller fix'), 'optimization_mixed_release_plan_required')
        self.assert_fails(lambda: sources.compose(refs, self.root / 'missing-reason', plan=plan), 'optimization_mixed_release_plan_required')
        result = sources.compose(refs, self.root / 'mixed', reason='registered controller fix', plan=plan)
        self.assertEqual(result['release_identities'], ['release-1', 'release-2'])
        self.assertTrue(result['mixed_controller_releases'])
        self.assertEqual(sources.resolve(self.root / 'mixed', 'beta'), two)
        sources.identity(self.root / 'mixed')
        plan.write_text('changed after collection was sealed')
        self.assert_fails(lambda: sources.identity(self.root / 'mixed'), 'optimization_source_changed')

    def test_sealed_files_reject_byte_changes_even_when_json_meaning_is_unchanged(self):
        # Whitespace preserves all cross-links except the hash being tested.
        for target in list(sources.RUN_FILES) + ['optimization/alpha/' + p for p in sources.CASE_FILES] + ['optimization/alpha/output/src/lib.rs']:
            with self.subTest(target=target):
                run, _, _ = self.run_fixture('run-' + str(len(list(self.root.iterdir()))))
                out = self.root / ('collection-' + str(len(list(self.root.iterdir()))))
                sources.compose([('alpha', run)], out)
                path = run / target; path.write_bytes(path.read_bytes() + b'\n')
                self.assert_fails(lambda: sources.resolve(out, 'alpha'))
                self.assert_fails(lambda: sources.identity(out))

    def test_output_inventory_rejects_addition_removal_and_edited_hash(self):
        for change in ['extra', 'removed', 'changed-record']:
            with self.subTest(change=change):
                run, _, _ = self.run_fixture(change); out = self.root / ('collection-' + change)
                sources.compose([('alpha', run)], out)
                if change == 'extra':
                    (run / 'optimization/alpha/output/unrecorded.rs').write_text('new')
                elif change == 'removed':
                    (run / 'optimization/alpha/output/src/lib.rs').unlink()
                else:
                    manifest = read(out / sources.MANIFEST)
                    manifest['cases']['alpha']['output_files']['src/lib.rs'] = '0' * 64
                    save(out / sources.MANIFEST, manifest)
                self.assert_fails(lambda: sources.resolve(out, 'alpha'))

    def test_all_cases_checked_by_identity_and_requested_case_checked_by_resolve(self):
        one, _, _ = self.run_fixture('one')
        two, _, _ = self.run_fixture('two', case='beta')
        out = self.root / 'collection'; sources.compose([('alpha', one), ('beta', two)], out)
        (two / 'optimization/beta/output/Cargo.lock').write_text('tampered')
        self.assertEqual(sources.resolve(out, 'alpha'), one)
        self.assert_fails(lambda: sources.resolve(out, 'beta'))
        self.assert_fails(lambda: sources.identity(out))

    def test_incomplete_run_duplicate_report_and_mismatched_result_rejected(self):
        for change, error in [('incomplete', 'optimization_run_not_complete'),
                              ('duplicate', 'duplicate_optimization_report_case'),
                              ('mismatch', 'optimization_result_mismatch')]:
            with self.subTest(change=change):
                run, _, _ = self.run_fixture(change); path = run / 'optimization-report.json'; report = read(path)
                if change == 'incomplete': report['complete'] = False
                elif change == 'duplicate': report['results'].append(deepcopy(report['results'][0]))
                else: report['results'][0]['selected_version'] = 'different'
                save(path, report)
                self.assert_fails(lambda: sources.case_record(run, 'alpha'), error)

    def test_scope_admission_validation_and_release_links_are_required_before_compose(self):
        for change, error in [('release', 'optimization_release_mismatch'),
                              ('validation', 'optimization_selected_state_unvalidated'),
                              ('scope', 'optimization_scope_unapproved'),
                              ('scope-version', 'optimization_scope_version_changed')]:
            with self.subTest(change=change):
                run, _, _ = self.run_fixture(change); d = run / 'optimization/alpha'
                result = read(d / 'result.json')
                if change == 'release':
                    save(run / 'optimization-origin.json', {'mode': 'rust-only', 'release_identity': 'wrong'})
                elif change == 'validation':
                    state = read(d / 'selected-state.json'); state['optimization_validation']['status'] = 'failed'
                    save(d / 'selected-state.json', state)
                    result['selected_state_sha256'] = digest(d / 'selected-state.json')
                else:
                    review = read(d / 'scope-review/review.json')
                    if change == 'scope': review['reviews'][0]['decision'] = 'out_of_scope'
                    else: review['identity']['candidates'][0]['version'] = 'different'
                    save(d / 'scope-review/review.json', review)
                    result['scope_selection']['review_sha256'] = digest(d / 'scope-review/review.json')
                    selection = read(d / 'scope-review/selection.json')
                    selection['review_sha256'] = result['scope_selection']['review_sha256']
                    save(d / 'scope-review/selection.json', selection)
                    result['scope_selection']['selection_sha256'] = digest(d / 'scope-review/selection.json')
                save(d / 'result.json', result)
                save(run / 'optimization-report.json', {'mode': 'rust-only', 'complete': True, 'results': [result]})
                self.assert_fails(lambda: sources.case_record(run, 'alpha'), error)

    def test_valid_fallback_is_referenceable_but_stays_baseline(self):
        run, original, _ = self.run_fixture('fallback', improved=False)
        self.compose(run)
        state, result = matrix.selected(self.root / 'collection', 'alpha', original)
        self.assertFalse(result['improved']); self.assertEqual(state, original)

    def test_nested_and_overlapping_collections_rejected(self):
        run, _, _ = self.run_fixture('run'); self.compose(run)
        self.assert_fails(lambda: sources.compose([('alpha', self.root / 'collection')], self.root / 'nested'), 'nested_optimization_collection')
        self.assert_fails(lambda: sources.compose([('alpha', run)], run / 'nested'), 'optimization_collection_overlaps_run')
        self.assert_fails(lambda: sources.compose([('alpha', run)], self.root), 'optimization_collection_overlaps_run')

    def test_collection_identity_changes_when_explicit_cohort_mapping_changes(self):
        one, _, _ = self.run_fixture('one'); two, _, _ = self.run_fixture('two')
        sources.compose([('alpha', one)], self.root / 'first')
        sources.compose([('alpha', two)], self.root / 'second')
        self.assertNotEqual(sources.identity(self.root / 'first'), sources.identity(self.root / 'second'))

    def test_matrix_origin_seals_collection_identity_and_rejects_a_changed_cohort(self):
        rust, _, _ = self.run_fixture('rust')
        full, _, _ = self.run_fixture('full', mode='full')
        replacement, _, _ = self.run_fixture('replacement')
        rc = self.root / 'rust-collection'; fc = self.root / 'full-collection'
        sources.compose([('alpha', rust)], rc); sources.compose([('alpha', full)], fc)
        other = self.root / 'other'; sources.compose([('alpha', replacement)], other)
        baseline = self.root / 'baseline'; save(baseline / 'release.json', {'baseline': 'fixture'})
        measured = {'case': 'alpha', 'primary_workload': 'fixture', 'rows': [
            {'workload': 'fixture', 'ratios': {'fixture-ratio': {'speedup': 1.0}}}]}
        # Controller control-flow test only: no binaries, measurement or shared locks.
        with patch.object(matrix, 'ROOT', self.root / 'isolated-agent'), \
                patch.object(matrix, 'measure_case', return_value=measured) as measure:
            matrix.run(baseline, rc, fc, [{'id': 'alpha'}], self.root / 'matrix')
            self.assertEqual(measure.call_count, 1)
            origin = read(self.root / 'matrix/origin.json')
            self.assertEqual(origin['optimization_reports'], {
                'rust-only': sources.identity(rc), 'full': sources.identity(fc)})
            self.assert_fails(lambda: matrix.run(baseline, other, fc, [{'id': 'alpha'}], self.root / 'matrix'),
                              'matrix_origin_changed')
            self.assertEqual(measure.call_count, 1)


if __name__ == '__main__':
    unittest.main()
