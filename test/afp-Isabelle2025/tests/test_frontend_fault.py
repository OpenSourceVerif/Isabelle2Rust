"""Counterexamples for source-invariant verification, without native execution."""

import _paths  # Locate AFP tools independently of cwd and unittest discovery.
from pathlib import Path
import collections, json, os, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0, str(Path.cwd() / 'test/afp-Isabelle2025'))
import afp_common as common
import full
import full_audit
import full_report
import frontend_fault as fault


def const(name): return ('v0', name, 0, None)
def app(function, argument): return ('v5', function, argument)
def trueprop(term): return app(const('HOL.Trueprop'), term)
BOOL = '<v0 a0="HOL.bool" />'
FUN = '<v0 a0="fun"><item><v0 a0="HOL.bool" /></item><item>{}</item></v0>'
PARAMETER = '<item><v0 a0="HOL.bool" /></item>'


def quantified_goal(indices, result=BOOL, arity=2):
    typ = result
    for _ in range(arity): typ = FUN.format(typ)
    term = ('v2', 'Q', 65, typ)
    for index in indices: term = app(term, ('v3', index))
    term = trueprop(term)
    for name in ['inner', 'outer']:
        term = app(const('Pure.all'), ('v4', name, PARAMETER, term))
    return term


class InvariantCounterexamples(unittest.TestCase):
    def test_native_form_requires_every_distinct_bound_parameter(self):
        # This is the native higher-order pattern of the observed rightmost
        # goals: a Boolean-valued schematic function on both bound parameters.
        value = fault.flexible(quantified_goal([1, 0]))
        self.assertEqual((value['name'], value['index'], len(value['parameters'])), ('Q', 65, 2))

    def test_duplicate_parameter_does_not_certify_the_observed_pattern(self):
        # Repeating a Bound argument changes the higher-order unification
        # premise. Equal event counts must not substitute for the native form.
        with self.assertRaisesRegex(ValueError, 'distinct quantified parameters'):
            fault.flexible(quantified_goal([0, 0]))

    def test_non_boolean_result_cannot_be_conjunction_expansion(self):
        # A schematic function returning nat cannot be the Boolean goal to
        # which conjI applies, even when its argument and goal counts match.
        with self.assertRaisesRegex(ValueError, 'Wrong schematic function type'):
            fault.flexible(quantified_goal([1, 0], '<v0 a0="Nat.nat" />'))

    def test_wrong_function_arity_cannot_reuse_the_invariant(self):
        # All bound arguments must be represented in the schematic function's
        # actual type, not inferred solely from the application syntax.
        with self.assertRaisesRegex(ValueError, 'Wrong schematic function type'):
            fault.flexible(quantified_goal([1, 0], arity=1))

    def test_fixed_conjunction_is_finite_structure_not_flexible_expansion(self):
        # Ordinary conjI splits an existing conjunction. Its successful step
        # does not establish the self-preserving flexible-goal source defect.
        term = app(app(const('HOL.conj'), ('v2', 'P', 0, BOOL)), ('v2', 'Q', 0, BOOL))
        with self.assertRaisesRegex(ValueError, 'rigid'):
            fault.flexible(trueprop(term))

    def test_ambiguous_instrumentation_cannot_be_reversed_as_native_source(self):
        # A recorded logging edit must identify one exact occurrence; blindly
        # replacing multiple copies could conceal an algorithm change.
        with self.assertRaisesRegex(ValueError, 'Non-unique observation edit'):
            fault.undo('LOG LOG', [{'new': 'LOG', 'old': 'native'}])

    def test_group_failure_cannot_reuse_one_members_review(self):
        # An independently diagnosed source constant does not assign a result
        # to the other member of a failed shared-frontend request.
        with self.assertRaisesRegex(ValueError, 'singleton'):
            fault.validate_record({'scope': ['A.f', 'A.g'], 'source_fault': {'constant': 'A.f'}}, 'serializer')

    def test_altered_review_is_rejected_before_any_verdict_is_trusted(self):
        # A stale receipt cannot stand in for the proof bytes or original
        # native request, even when its stored constant and scope still match.
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory); formal = project / 'formal'; formal.mkdir()
            path = formal / 'source-fault-review.json'; path.write_text('{}')
            checksum = fault.sha(path); path.write_text('{"changed": true}')
            run = {'directory': 'formal', 'scope': ['A.f'], 'source_fault': {
                'constant': 'A.f', 'review': 'formal/source-fault-review.json', 'review_sha256': checksum}}
            with patch.object(common, 'PROJECT', project):
                with self.assertRaisesRegex(ValueError, 'bytes changed'):
                    fault.validate_record(run, 'serializer')


class SourceFailureCoverage(unittest.TestCase):
    def test_fresh_tuple_identity_matches_only_the_same_durable_command(self):
        # common.command returns an in-memory identity tuple; JSON writes the
        # same birth identity as an array. Preserve equality for that encoding,
        # while every actual subprocess-field change must still be rejected.
        actual = {'identity': ('boot', 123, 'birth'), 'status': 'failed',
                  'returncode': 1, 'command': ['isabelle', 'process']}
        durable = json.loads(json.dumps(actual))
        self.assertTrue(fault.same_command(actual, durable))
        for key, value in [('identity', ['boot', 123, 'other-birth']),
                           ('returncode', -15), ('status', 'passed'),
                           ('command', ['isabelle', 'build'])]:
            changed = dict(durable, **{key: value})
            self.assertFalse(fault.same_command(actual, changed), key)

    def test_adjudication_keeps_the_actual_failed_process_fields(self):
        # A reviewed source failure is shared across the six frontend users.
        # Its process remains failed and supplies no native finished witness.
        run = {'scope': ['A.f'], 'command': {'status': 'failed'}, 'finished': False,
               'attempts': [], 'source_fault': {'constant': 'A.f', 'review': 'review.json',
                                               'family': 'empty_overlap_merge_cycle'}}
        outcomes = full.resolve_candidates(['A.f'], [run])['A.f']
        self.assertTrue(all(value['status'] == 'failed' for value in outcomes.values()))
        self.assertTrue(all(value['stage'] == 'frontend_source_algorithm' for value in outcomes.values()))
        self.assertEqual(run['command']['status'], 'failed')
        self.assertFalse(run['finished'])

    def test_successful_independent_context_still_wins(self):
        # A review of one context cannot override an actual target success in
        # another context or leave source-failure metadata on that passed cell.
        failed = {'scope': ['A.f'], 'attempts': [], 'source_fault': {
            'constant': 'A.f', 'review': 'review.json', 'family': 'empty_overlap_merge_cycle'}}
        passed = {'attempts': [{'constants': ['A.f'], 'target': 'Rust', 'status': 'passed',
                               'evidence': 'Rust.xml'}]}
        values = full.resolve_candidates(['A.f'], [failed, passed, failed])['A.f']
        self.assertEqual(values['Rust']['status'], 'passed')
        self.assertNotIn('source_fault', values['Rust'])
        self.assertTrue(all(values[target]['status'] == 'failed' for target in full.TARGETS if target != 'Rust'))

    def test_resource_message_alone_keeps_its_resource_category(self):
        # Attribution requires the separately checked source evidence; ordinary
        # exhausting processes must not acquire a source-algorithm diagnosis.
        self.assertEqual(full_report.category('Run out of store - interrupting threads')[0], 'infrastructure')
        self.assertEqual(full_report.category('Verified shared frontend source algorithm failure: flexible_boolean_conjunction\nRun out of store')[0], 'source_algorithm')

    def test_report_status_prefix_keeps_the_verified_source_category(self):
        # Report construction prepends the process status before classification.
        # The marker is still a complete line and must not fall through to the
        # resource-message category carried in the original full native log.
        message = 'failed\nVerified shared frontend source algorithm failure: flexible_boolean_conjunction\nRun out of store'
        self.assertEqual(full_report.category(message)[0], 'source_algorithm')

    def test_one_review_does_not_cover_two_independent_source_owners(self):
        # Repeated internal names retain the original source-specific witness
        # requirement. A single source review cannot certify both declarations.
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            common.write_json(base / 'exports.json', {})
            common.write_json(base / 'frontend-fault-cases.json', {
                'schema': 1, 'serializer_sha256': 'serializer',
                'candidate_scope_sha256': full.scope_digest({'One.thy': ['A.f'], 'Other.thy': ['A.f']}),
                'cases': [{'entry': 'E', 'constant': 'A.f'}]})
            with patch.object(full, 'serializer_signature', return_value='serializer'):
                with self.assertRaisesRegex(ValueError, 'unambiguous source declaration'):
                    full.registered_source_fault(base, 'E', {'One.thy': ['A.f'], 'Other.thy': ['A.f']}, ['A.f'])

@unittest.skipUnless(os.environ.get('AFP_NATIVE_FAULT_EVIDENCE_TEST') == '1',
                     'requires retained current-candidate native evidence; starts no ML')
class ReadOnlyNativeReviews(unittest.TestCase):
    def test_original_native_bytes_support_each_independent_source_case(self):
        # Each case supplies its own original singleton request and separate
        # observational input. No derived constant borrows another's verdict.
        # Optional native reviews use the configured current run. No dated
        # archive or checked-in experiment output is a prerequisite for tests.
        base = common.WORK
        registry = common.read_record(base / 'frontend-fault-cases.json', {})
        if not registry.get('cases'):
            self.skipTest('current run has no registered native source-fault evidence')
        _, current, _ = full.load(base)
        cases = []
        for case in registry['cases']:
            entry, constant = case['entry'], case['constant']
            requests = [run for run in current['entries'][entry].get('full_export', {}).get('runs', [])
                        if run.get('scope') == [constant] and run['command']['status'] == 'failed']
            self.assertEqual(len(requests), 1)
            cases.append((entry, constant, common.resolve_path(requests[0]['directory']),
                          common.resolve_path(case['observation']), case['family']))
        temporary = tempfile.TemporaryDirectory(prefix='afp-source-review-test-')
        self.addCleanup(temporary.cleanup)
        records = []
        for case_index, (entry, constant, formal, observation, family) in enumerate(cases):
            with self.subTest(constant=constant):
                paths = [formal / name for name in ['process.log', 'scope.txt', 'contexts/merged.xml']]
                before = {path: fault.sha(path) for path in paths}
                evidence = fault.review(formal, observation, constant, family, full.serializer_signature())
                self.assertEqual(evidence['constant'], constant)
                self.assertEqual(evidence['native_evidence']['command']['status'], 'failed')
                self.assertFalse(evidence['native_evidence']['original_finished_exists'])
                self.assertTrue(evidence['source_invariant']['source_observer_reverses_exactly'])
                if case_index == 0:
                    # Retain the native failed request and store only the
                    # derived review under an isolated test-output directory.
                    # The real exporter and its result database remain intact.
                    private = Path(temporary.name) / 'review'
                    private.mkdir()
                    run = {'directory': common.relative(formal), 'session': entry, 'scope': [constant],
                           'command': common.read_record(formal / 'process.log.json'),
                           'finished': False, 'attempts': []}
                    # Exercise the exact fresh-command representation as well
                    # as the original JSON sidecar used by independent review.
                    run['command']['identity'] = tuple(run['command']['identity'])
                    run['source_fault'] = fault.prepare_record(run, observation,
                                                               family, full.serializer_signature(), review_root=private)
                    scan = {'status': 'passed', 'theories': ['Fixture.thy']}
                    scope = {'Fixture.thy': [constant]}
                    record = {'scan': scan}
                    stage = record['full_export'] = {
                        'scope_sha256': full.scope_digest(scope), 'serializer_sha256': full.serializer_signature(),
                        'scan_sha256': full.entry_scan_signature(record), 'runs': [run]}
                    full.finish_export(stage, [constant])
                    self.assertEqual(stage['status'], 'complete')
                    self.assertTrue(all(value['status'] == 'failed' for value in stage['candidates'][constant].values()))
                    gate = full.export_checkpoint(private, {'order': ['Fixture']},
                                                  {'entries': {'Fixture': record}}, {'Fixture': scope})
                    self.assertTrue(gate['passed'], gate)
                    self.assertFalse(run['finished'])
                    self.assertEqual(run['command']['status'], 'failed')
                    # Audit this real singleton independently of the gate.
                    # The tiny fixture deliberately fails archive-wide checks;
                    # only the local evidence predicates may pass here.
                    fixture_data = {'order': ['Fixture'], 'entries': {
                        'Fixture': {'theories': [{'path': 'Fixture.thy'}]}}}
                    fixture_result = {'entries': {'Fixture': record}}
                    fixture_exports = {'Fixture': scope}
                    audited = full_audit.audit_data(private, fixture_data, fixture_result, fixture_exports)
                    self.assertFalse(audited['passed'])
                    for predicate, count in [('candidate has direct applicable witness', len(full.TARGETS)),
                                             ('export process has a verified terminal outcome', 1)]:
                        self.assertEqual(audited['checks'][predicate], count)
                        self.assertEqual(audited['issue_counts'].get(predicate, 0), 0)
                    self.assertEqual(audited['issue_counts'].get('source algorithm evidence rechecked', 0), 0)
                    common.write_json(private / 'valid-evidence-audit.json', audited)
                    review_path = common.PROJECT / run['source_fault']['review']
                    original_bytes = review_path.read_bytes(); review_path.write_bytes(original_bytes + b'\n')
                    tampered = full.export_checkpoint(private, {'order': ['Fixture']},
                                                      {'entries': {'Fixture': record}}, {'Fixture': scope})
                    self.assertFalse(tampered['passed'])
                    self.assertTrue(any(row['reason'] == 'invalid source algorithm evidence' for row in tampered['problems']))
                    rejected = full_audit.audit_data(private, fixture_data, fixture_result, fixture_exports)
                    self.assertEqual(rejected['issue_counts']['source algorithm evidence rechecked'], 1)
                    self.assertEqual(rejected['issue_counts']['export process has a verified terminal outcome'], 1)
                    self.assertEqual(rejected['issue_counts']['candidate has direct applicable witness'], len(full.TARGETS))
                    common.write_json(private / 'tampered-evidence-audit.json', rejected)
                    review_path.write_bytes(original_bytes)
                    # Generate the actual four-report path on this isolated
                    # fixture. Classification, complete raw log retention and
                    # failure occurrence identities are checked independently.
                    full_report.build_report(private, fixture_data, fixture_result, fixture_exports)
                    events = [json.loads(line) for line in (private / 'report/failures.jsonl').read_text().splitlines()]
                    self.assertEqual(len(events), 1)
                    self.assertEqual(events[0]['category'], 'source_algorithm')
                    self.assertIn((formal / 'process.log').read_text(), events[0]['error'])
                    self.assertEqual(collections.Counter(map(full_audit.failure_key, events)),
                                     full_audit.required_failure_inventory(private, fixture_data, fixture_result))
                    report_audit = full_audit.audit_data(private, fixture_data, fixture_result, fixture_exports)
                    before_issues = dict(report_audit['issue_counts'])
                    full_audit.audit_reports(private, fixture_data, fixture_result, fixture_exports, report_audit)
                    added = {key: count - before_issues.get(key, 0)
                             for key, count in report_audit['issue_counts'].items()
                             if count != before_issues.get(key, 0)}
                    self.assertEqual(added, {'final report matches current completed data': 1})
                    common.write_json(private / 'isolated-report-audit.json', report_audit)
                    common.write_json(private / 'validation.json', {
                        'passed': True, 'valid_source_failure_adjudicated': True,
                        'tampered_review_rejected': True, 'independent_audit_validated_and_rejected': True, 'four_reports_preserve_source_category_and_native_log': True,
                        'native_process_still_failed': True,
                        'native_finished_still_missing': True, 'formal_result_database_modified': False})
                self.assertEqual(before, {path: fault.sha(path) for path in paths})
                records.append({'constant': constant, 'family': family, 'passed': True})
        common.write_json(Path(temporary.name) / 'validation.json', {
            'checked': common.timestamp(), 'passed': True, 'cases': records,
            'formal_results_modified': False, 'export_gate_changed': False, 'native_code_started': False})


if __name__ == '__main__': unittest.main()