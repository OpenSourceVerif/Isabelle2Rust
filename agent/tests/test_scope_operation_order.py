"""Operation-order admission regressions. Fake reviewers only; no model requests."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from i2r_agent.common import Failure, read, save


@pytest.fixture
def scope():
    from i2r_agent import optimization_scope
    return optimization_scope


@pytest.fixture
def valid_review():
    return {'candidate_id': '001', 'decision': 'within_scope', 'reason': 'Current source business transitions match.',
        'contract_evidence': {'obligations': 'satisfied', 'source_and_runtime': 'No numeric primitive is affected.',
            'guards_and_ranges': 'No new numeric guard or carrier assumptions.', 'advisory_conflicts': []},
        'transition_evidence': {'eliminated_source_iterations': False, 'changed_source_recurrence': False,
            'changed_source_marking_schedule': False, 'changed_source_operation_order': False,
            'explanation': 'Compare construction/recursive transitions, not the final output sequence.'},
        'operation_order_evidence': [{'source_id': 'constant:Example.fold',
            'source_equation': 'fold (Branch l r) acc = fold l (fold r (Op # acc))',
            'events': [{'id': key, 'source_operation': source, 'rust_operation': rust,
                        'rust_locations': ['crate::fold_rev, Branch case'], 'correspondence': 'same_transition'}
                       for key, source, rust in [('op', 'construct Op', 'push Op'),
                                                 ('right', 'recurse right', 'visit right subtree'),
                                                 ('left', 'recurse left', 'visit left subtree')]],
            'source_order': ['op', 'right', 'left'], 'rust_order': ['op', 'right', 'left'], 'identity_case': False,
            'representation_relation': 'decode(v)=reverse(v), preserving each business transition',
            'comparison': 'preserved'}]}


def validate(scope, row):
    return scope.validate_admission_reply({'reviews': [row]}, '001', {'constant:Example.fold'})


def test_reversed_storage_preserving_business_order_is_accepted(scope, valid_review):
    assert validate(scope, valid_review)['decision'] == 'within_scope'


def test_single_review_envelope_preserves_evidence_and_semantic_rejection(scope, valid_review):
    evidence = valid_review.pop('operation_order_evidence')
    evidence[0]['rust_order'] = ['left', 'right', 'op']
    raw = {'reviews': [valid_review], 'operation_order_evidence': evidence}
    before = deepcopy(raw)
    normalized, moved = scope.normalize_admission_envelope(raw)
    assert raw == before and moved == ['operation_order_evidence']
    assert normalized['reviews'][0]['operation_order_evidence'] == evidence
    assert scope.validate_admission_reply(normalized, '001', {'constant:Example.fold'})['decision'] == 'requires_source_change'


@pytest.mark.parametrize('kind', ['duplicate', 'multiple_reviews'])
def test_ambiguous_review_envelope_is_rejected(scope, valid_review, kind):
    raw = {'reviews': [valid_review], 'operation_order_evidence': valid_review['operation_order_evidence']}
    if kind == 'multiple_reviews':
        raw['reviews'] = [dict(valid_review, candidate_id='001'), dict(valid_review, candidate_id='002')]
        for row in raw['reviews']: row.pop('operation_order_evidence')
    with pytest.raises(Failure, match='Ambiguous or duplicate'):
        scope.normalize_admission_envelope(raw)


@pytest.mark.parametrize('flag', ['changed_source_operation_order', 'changed_source_recurrence',
                                 'eliminated_source_iterations', 'changed_source_marking_schedule'])
def test_any_true_change_flag_cannot_be_overridden_by_within_scope(scope, valid_review, flag):
    valid_review['transition_evidence'][flag] = True
    assert validate(scope, valid_review)['decision'] == 'requires_source_change'


def test_paired_order_mismatch_rejects_even_with_all_flags_false(scope, valid_review):
    valid_review['operation_order_evidence'][0]['rust_order'] = [
        'left', 'right', 'op']
    # The model says preserved and all flags false, but its paired evidence
    # contradicts that conclusion. The controller must reject deterministically.
    assert validate(scope, valid_review)['decision'] == 'requires_source_change'


@pytest.mark.parametrize('comparison, expected', [('changed', 'requires_source_change'), ('unknown', 'uncertain')])
def test_nonpreserved_comparison_cannot_be_accepted(scope, valid_review, comparison, expected):
    valid_review['operation_order_evidence'][0]['comparison'] = comparison
    assert validate(scope, valid_review)['decision'] == expected


@pytest.mark.parametrize('remove', ['changed_source_operation_order', 'operation_order_evidence', 'rust_order'])
def test_missing_order_fields_fail_closed(scope, valid_review, remove):
    if remove == 'changed_source_operation_order': del valid_review['transition_evidence'][remove]
    elif remove == 'operation_order_evidence': del valid_review[remove]
    else: del valid_review['operation_order_evidence'][0][remove]
    with pytest.raises(Failure) as error: validate(scope, valid_review)
    assert error.value.code == 'invalid_scope_review'


@pytest.mark.parametrize('field, value', [('source_id', 'constant:Original.obsolete'),
    ('events', []), ('source_order', 'op'),
    ('representation_relation', ''), ('comparison', 'probably')])
def test_malformed_or_obsolete_order_evidence_fails_closed(scope, valid_review, field, value):
    valid_review['operation_order_evidence'][0][field] = value
    with pytest.raises(Failure): validate(scope, valid_review)


@pytest.mark.parametrize('field', ['source_id', 'comparison'])
def test_unhashable_order_identity_or_comparison_is_a_protocol_failure(scope, valid_review, field):
    valid_review['operation_order_evidence'][0][field] = ['malformed list instead of string']
    with pytest.raises(Failure) as error: validate(scope, valid_review)
    assert error.value.code == 'invalid_scope_review'


def test_identity_source_can_have_empty_business_trace(scope, valid_review):
    pair = valid_review['operation_order_evidence'][0]
    pair.update(events=[], source_order=[], rust_order=[], identity_case=True, source_equation='identity x = x',
                representation_relation='Identity; no business construction or recursive transition occurs.')
    assert validate(scope, valid_review)['decision'] == 'within_scope'


def test_approved_primitive_identity_does_not_require_physical_list_cell_events(scope, valid_review):
    pair = valid_review['operation_order_evidence'][0]
    pair.update(source_id='constant:List.append', events=[], source_order=[], rust_order=[], identity_case=True,
                source_equation='append xs [] = xs',
                representation_relation='Approved exact append primitive: empty-right returns the owned left container; no business element computation.')
    result = scope.validate_admission_reply({'reviews': [valid_review]}, '001', {'constant:List.append'})
    assert result['decision'] == 'within_scope'


def test_legacy_review_parser_remains_read_only_compatible(scope):
    row = {'candidate_id': 'old', 'decision': 'within_scope', 'reason': 'Historical review without new order fields'}
    assert scope.validate_reply({'reviews': [row]}, ['old']) == {'old': row}


@pytest.fixture
def admission_io(valid_review):
    state = {'files': {'src/lib.rs': 'pub fn fold() {}'}, 'mapping': [], 'rust_config': {},
             'partition': {'owner': {'constant:Example.fold': 'unit'}, 'boundaries': []},
             'bundle': {'source_model': {'entries': ['constant:Example.fold'], 'entities': {
                 'constant:Example.fold': {'id': 'constant:Example.fold', 'kind': 'constant', 'name': 'Example.fold'}}}}}
    class Reviewer:
        calls = 0
        def call(self, system, payload, **kwargs):
            self.calls += 1
            result = deepcopy(valid_review)
            result['candidate_id'] = json.loads(payload)['candidates'][0]['candidate_id']
            return {'reviews': [result]}
    class Budget:
        calls = 0
        def call(self, provider, payload, system=None, phase=None):
            assert phase == 'performance_scope_admission'
            self.calls += 1
            return provider.call(system, json.dumps(payload), phase=phase)
    return state, Reviewer(), Budget()


def test_new_admission_uses_one_call_then_exact_cache(scope, admission_io, tmp_path):
    state, reviewer, budget = admission_io
    for number in ['001', '002']:
        path = tmp_path/'attempts'/number
        result = scope.admit(state, state, {'path': str(path)}, reviewer, budget, path)
        assert result['decision'] == 'within_scope'
    assert reviewer.calls == 1 and budget.calls == 1
    assert read(tmp_path/'attempts/002/scope-admission.json')['cached']


@pytest.mark.parametrize('failure_code', ['invalid_model_response', 'incomplete_response'])
def test_malformed_review_gets_one_charged_schema_repair(scope, admission_io, tmp_path, failure_code):
    state, reviewer, budget = admission_io
    valid = reviewer.call
    def reply(system, payload, **kwargs):
        if reviewer.calls == 0:
            reviewer.calls += 1
            raise Failure(failure_code, 'broken JSON')
        assert json.loads(payload)['response_format_feedback']['code'] == failure_code
        return valid(system, payload, **kwargs)
    reviewer.call = reply
    directory = tmp_path/'attempts/001'
    result = scope.admit(state, state, {'path': str(directory)}, reviewer, budget, directory)
    assert result['decision'] == 'within_scope' and reviewer.calls == budget.calls == 2
    assert len(read(directory/'scope-format-errors.json')) == 1


def test_schema_repair_is_bounded_and_never_manufactures_admission(scope, admission_io, tmp_path):
    state, reviewer, budget = admission_io
    def broken(*args, **kwargs):
        reviewer.calls += 1
        raise Failure('invalid_model_response', 'broken JSON')
    reviewer.call = broken
    directory = tmp_path/'attempts/001'
    with pytest.raises(Failure, match='broken JSON'):
        scope.admit(state, state, {'path': str(directory)}, reviewer, budget, directory)
    assert reviewer.calls == budget.calls == 2
    assert not (directory/'scope-admission.json').exists()


def test_rejected_order_is_charged_once_and_not_silently_reaudited(scope, admission_io, valid_review, tmp_path):
    state, reviewer, budget = admission_io
    candidate = deepcopy(state)
    candidate['files']['src/lib.rs'] = 'pub fn fold() { changed(); }'
    valid_review['transition_evidence']['changed_source_operation_order'] = True
    valid_review['rejection_changes'] = [{'origin': 'introduced', 'reference': 'original',
        'source_ids': ['constant:Example.fold'],
        'before': {'path': 'src/lib.rs', 'excerpt': state['files']['src/lib.rs']},
        'after': {'path': 'src/lib.rs', 'excerpt': candidate['files']['src/lib.rs']},
        'before_events': ['op', 'right', 'left'], 'after_events': ['left', 'right', 'op'],
        'explanation': 'Newly reordered business events.'}]
    for number in ['001', '002']:
        path = tmp_path/'attempts'/number
        with pytest.raises(Failure) as error:
            scope.admit(state, candidate, {'path': str(path)}, reviewer, budget, path)
        assert error.value.code == 'optimization_scope_rejected'
    assert reviewer.calls == 1 and budget.calls == 1


def test_author_and_reviewer_share_contract_and_completed_old_result_is_not_reaudited(scope, monkeypatch, tmp_path):
    from i2r_agent import optimization
    assert scope.COMPUTATION_PRESERVATION_CONTRACT == optimization.stage_contract('rust', False)['computation_preservation']
    assert 'computation_preservation' not in optimization.stage_contract('source', False)
    assert scope.COMPUTATION_PRESERVATION_CONTRACT in scope.ONLINE_SYSTEM
    assert 'changed_source_operation_order' in scope.ONLINE_SYSTEM
    directory = tmp_path/'legacy'
    legacy = {'scope_selection': {'historical_review': 'unchanged'}, 'stage_schema': 2}
    save(directory/'result.json', legacy)
    monkeypatch.setattr(optimization.numeric_experiment, 'freeze', lambda *a, **k: pytest.fail('No old run mutation'))
    monkeypatch.setattr(scope, 'admit', lambda *a, **k: pytest.fail('No old admission replay'))
    assert optimization.optimize_case('unused', {'id': 'legacy'}, 'full', directory, {}) == legacy


@pytest.mark.parametrize('source_text,rust_text', [
    ('construct False', 'write false'), ('predecessor k in Suc k', 'guarded m minus one')])
def test_semantic_event_correspondence_is_independent_of_prose(scope, valid_review, source_text, rust_text):
    event = valid_review['operation_order_evidence'][0]['events'][0]
    event.update(source_operation=source_text, rust_operation=rust_text)
    assert validate(scope, valid_review)['decision'] == 'within_scope'


def test_repeated_event_occurrences_are_preserved_and_extra_repetition_rejected(scope, valid_review):
    pair = valid_review['operation_order_evidence'][0]
    pair['source_order'] = pair['rust_order'] = ['op', 'op', 'right', 'left']
    assert validate(scope, valid_review)['decision'] == 'within_scope'
    pair['rust_order'] = ['op', 'right', 'left']
    assert validate(scope, valid_review)['decision'] == 'requires_source_change'


@pytest.mark.parametrize('field,value', [('correspondence', []), ('rust_locations', []),
    ('source_operation', ''), ('id', []), ('rust_operation', None)])
def test_malformed_event_rows_fail_closed(scope, valid_review, field, value):
    valid_review['operation_order_evidence'][0]['events'][0][field] = value
    with pytest.raises(Failure) as error: validate(scope, valid_review)
    assert error.value.code == 'invalid_scope_review'


def test_duplicate_event_ids_and_unbound_order_references_fail_closed(scope, valid_review):
    pair = valid_review['operation_order_evidence'][0]
    pair['events'].append(deepcopy(pair['events'][0]))
    with pytest.raises(Failure): validate(scope, valid_review)
    pair['events'].pop()
    pair['rust_order'].append('unbound')
    with pytest.raises(Failure): validate(scope, valid_review)


def test_omitted_table_event_is_malformed_but_explicit_deleted_business_operation_rejected(scope, valid_review):
    pair = valid_review['operation_order_evidence'][0]
    pair['rust_order'].remove('op')
    with pytest.raises(Failure): validate(scope, valid_review)
    pair['events'][0].update(rust_operation=None, rust_locations=[], correspondence='different_transition')
    assert validate(scope, valid_review)['decision'] == 'requires_source_change'


def test_unknown_event_correspondence_cannot_be_admitted(scope, valid_review):
    valid_review['operation_order_evidence'][0]['events'][0]['correspondence'] = 'unknown'
    assert validate(scope, valid_review)['decision'] == 'uncertain'


def test_empty_trace_without_explicit_source_identity_is_invalid(scope, valid_review):
    valid_review['operation_order_evidence'][0].update(events=[], source_order=[], rust_order=[])
    with pytest.raises(Failure): validate(scope, valid_review)


def test_same_id_does_not_override_different_business_operands(scope, valid_review):
    event = valid_review['operation_order_evidence'][0]['events'][0]
    event.update(source_operation='x times accumulator', rust_operation='accumulator times x',
                 correspondence='different_transition')
    assert validate(scope, valid_review)['decision'] == 'requires_source_change'


def test_attribution_has_complete_diffs_hashes_and_baseline_parent_dedup(scope, admission_io):
    original, _, _ = admission_io
    original = deepcopy(original)
    original['files'].update({'src/removed.rs': 'removed', 'src/same.rs': 'unchanged'})
    candidate = deepcopy(original)
    candidate['files']['src/lib.rs'] = 'pub fn fold() { changed(); }'
    del candidate['files']['src/removed.rs']
    candidate['files']['src/added.rs'] = 'new'
    value = scope.attribution(original, candidate, deepcopy(original))
    assert value['parent_to_candidate'] == {'same_as': 'original_to_candidate'}
    delta = value['original_to_candidate']
    assert {r['path']: r['status'] for r in delta['files']} == {
        'src/lib.rs': 'modified', 'src/removed.rs': 'deleted', 'src/same.rs': 'unchanged', 'src/added.rs': 'added'}
    assert '+pub fn fold() { changed(); }' in delta['unified_diff']
    assert '-removed' in delta['unified_diff'] and '+new' in delta['unified_diff']
    assert 'No newline at end of file' in delta['unified_diff']
    # Complete candidate plus complete hunks provides inherited context without repeating A0.
    parent = deepcopy(original); parent['files']['src/lib.rs'] = 'pub fn fold() { previous(); }'
    value = scope.attribution(original, candidate, parent)
    assert '-pub fn fold() { previous(); }' in value['parent_to_candidate']['unified_diff']
    assert value['original_to_candidate']['context'] != value['parent_to_candidate']['context']


def test_payload_keeps_unchanged_helpers_and_sources_for_inherited_obligations(scope, admission_io):
    original, _, _ = admission_io
    original = deepcopy(original); original['files']['src/inherited.rs'] = 'pub fn raw_constructor() {}'
    candidate = deepcopy(original); candidate['files']['src/lib.rs'] = 'pub fn fold() { optimized(); }'
    payload = scope.admission_payload(original, {'id': '001', 'state': candidate, 'record': {}}, original)
    assert payload['candidates'][0]['files'] == candidate['files']
    assert 'inherited correctness' in payload['candidates'][0]['change_attribution']['rule']


def test_cache_identity_binds_parent_baseline_and_review_evidence(scope, admission_io, tmp_path):
    original, reviewer, budget = admission_io
    candidate = deepcopy(original); candidate['files']['src/lib.rs'] = 'pub fn fold() { optimized(); }'
    parent = deepcopy(original)
    def admit(number, baseline, before):
        path = tmp_path/'attempts'/number
        return scope.admit(baseline, candidate, {'path': str(path)}, reviewer, budget, path, parent=before)
    first = admit('001', original, parent)
    assert admit('002', original, parent)['identity'] == first['identity']
    assert reviewer.calls == 1
    parent['files']['src/lib.rs'] = 'pub fn fold() { inherited(); }'
    assert admit('003', original, parent)['identity'] != first['identity']
    baseline = deepcopy(original); baseline['files']['src/lib.rs'] = 'pub fn fold() { baseline(); }'
    assert admit('004', baseline, parent)['identity'] != first['identity']
    parent['mapping'] = [{'source': 'constant:Example.fold', 'rust_item': 'crate::fold'}]
    admit('005', baseline, parent)
    assert reviewer.calls == 4



def test_batch_source_context_does_not_alias_different_native_boundaries(scope, admission_io):
    original, _, _ = admission_io
    first = deepcopy(original); second = deepcopy(original)
    first['partition']['boundaries'] = [{'source': 'constant:Example.fold', 'kind': 'native', 'conditions': ['first guard']}]
    second['partition']['boundaries'] = [{'source': 'constant:Example.fold', 'kind': 'native', 'conditions': ['second guard']}]
    payload = scope.review_payload(original, [{'id': 'first', 'state': first, 'record': {}},
                                               {'id': 'second', 'state': second, 'record': {}}])
    assert len(payload['source_graphs']) == 2
    for candidate, expected in zip(payload['candidates'], ['first guard', 'second guard']):
        assert payload['source_graphs'][candidate['source_graph']]['boundaries'][0]['conditions'] == [expected]


def test_checked_source_evidence_is_bound_without_author_prose_or_run_paths(scope, admission_io):
    original, _, _ = admission_io
    state = deepcopy(original)
    state['bundle']['source_equivalence'] = {'status': 'proved', 'directory': '/a/private/proof-run',
        'proposal': {'reason': 'author performance argument'}, 'export_type_authority': 'trusted authority',
        'export_type_evidence_sha256': 'first-type-evidence', 'original_to_optimized': {'old': 'new'}}
    option = {'id': 'one', 'state': state, 'record': {'source_optimized': True}}
    payload = scope.admission_payload(original, option, original)
    supplied = payload['candidates'][0]['checked_source_evidence']
    assert 'directory' not in supplied and 'proposal' not in supplied
    assert supplied['export_type_evidence_sha256'] == 'first-type-evidence'
    first = scope.admission_identity(original, option, payload)
    state['bundle']['source_equivalence']['export_type_evidence_sha256'] = 'changed-type-evidence'
    changed = scope.admission_identity(original, option, scope.admission_payload(original, option, original))
    assert changed != first
