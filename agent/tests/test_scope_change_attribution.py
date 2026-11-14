"""Inherited partition schedules must not become mode-dependent rejections."""
from copy import deepcopy

import pytest

from i2r_agent.common import Failure
from i2r_agent import optimization_scope as scope, optimization_baseline_quality as quality


@pytest.fixture
def states():
    loop = 'for y in xs { if less(&y, &pivot) { left.push(y); } else if less_eq(&pivot, &y) { right.push(y); } }'
    original = {'files': {'src/lib.rs': 'let mut left = Vec::new();\n' + loop},
                'bundle': {'source_model': {'entries': ['constant:sort'], 'entities': {'constant:sort': {}}}}}
    candidate = deepcopy(original)
    candidate['files']['src/lib.rs'] = 'let mut left = Vec::with_capacity(xs.len());\n' + loop
    return original, candidate, loop


def rejection(before, after, before_events, after_events):
    return {'decision': 'requires_source_change', 'rejection_changes': [{
        'origin': 'introduced', 'reference': 'original', 'source_ids': ['constant:sort'],
        'before': {'path': 'src/lib.rs', 'excerpt': before},
        'after': {'path': 'src/lib.rs', 'excerpt': after},
        'before_events': before_events, 'after_events': after_events,
        'explanation': 'Compare actual prior Rust and candidate, not the source trace substituted for prior Rust.'}]}


def test_same_partition_cannot_reject_a_capacity_change(states):
    original, candidate, loop = states
    row = rejection(loop, loop, ['one partition'], ['one partition'])
    with pytest.raises(Failure, match='Unchanged implicated'):
        scope.validate_rejection_attribution(row, original, candidate)


def test_larger_excerpt_does_not_turn_storage_change_into_business_change(states):
    original, candidate, _ = states
    row = rejection(original['files']['src/lib.rs'], candidate['files']['src/lib.rs'],
                    ['one partition'], ['one partition'])
    with pytest.raises(Failure, match='Unchanged implicated'):
        scope.validate_rejection_attribution(row, original, candidate)


def test_invented_before_code_cannot_recast_inherited_fusion_as_new(states):
    original, candidate, loop = states
    row = rejection('filter(left, xs); filter(right, xs);', loop, ['left pass', 'right pass'], ['one partition'])
    with pytest.raises(Failure, match='verbatim'):
        scope.validate_rejection_attribution(row, original, candidate)


def test_real_new_partition_change_still_has_a_valid_negative_admission(states):
    original, candidate, loop = states
    original['files']['src/lib.rs'] = 'filter(left, xs); filter(right, xs);'
    row = rejection(original['files']['src/lib.rs'], loop, ['left pass', 'right pass'], ['one partition'])
    scope.validate_rejection_attribution(row, original, candidate)


def test_new_use_of_unchanged_helper_must_cite_changed_caller(states):
    original, candidate, _ = states
    original['files']['src/caller.rs'] = 'if nonzero(x) { divide(x); }'
    candidate['files']['src/caller.rs'] = 'divide(x);'
    row = rejection(original['files']['src/caller.rs'], candidate['files']['src/caller.rs'],
                    ['nonzero guard', 'divide'], ['divide'])
    change = row['rejection_changes'][0]; change['origin'] = 'activated'
    change['before']['path'] = change['after']['path'] = 'src/caller.rs'
    scope.validate_rejection_attribution(row, original, candidate)


def test_checked_revised_source_can_have_a_new_realization_obligation(states):
    original, candidate, loop = states
    candidate['bundle']['source_model']['entities']['constant:sort']['equation'] = 'revised'
    candidate['bundle']['source_equivalence'] = {'status': 'proved'}
    row = rejection(loop, loop, [], [])
    row['rejection_changes'][0].update(origin='revised_source', before=None)
    scope.validate_rejection_attribution(row, original, candidate)
    del candidate['bundle']['source_equivalence']
    with pytest.raises(Failure, match='actual checked'):
        scope.validate_rejection_attribution(row, original, candidate)


def test_inherited_pure_schedule_is_recorded_without_asserting_semantic_failure(states):
    original, candidate, _ = states
    finding = {'source_ids': ['constant:sort'], 'status': 'claim_limit',
               'declared_root_impact': 'not_affected', 'obligation_kind': 'source_computation_history',
               'finding': 'Original already fused the pure filter passes.',
               'evidence': 'Original and candidate use the same partition loop.'}
    row = {'decision': 'within_scope', 'inherited_baseline_findings': [finding]}
    scope.validate_rejection_attribution(row, original, candidate)
    assert not quality.summarize({}, [finding])['publication_hold']
    finding['status'] = 'violated'
    with pytest.raises(Failure, match='not a baseline semantic violation'):
        scope.validate_rejection_attribution(row, original, candidate)


def test_real_inherited_behavioral_violation_still_holds_all_modes(states):
    original, candidate, _ = states
    finding = {'source_ids': ['constant:sort'], 'status': 'violated',
               'declared_root_impact': 'affected', 'obligation_kind': 'observable_semantics',
               'finding': 'Original drops the pivot.', 'evidence': 'Singleton input returns an empty output.'}
    scope.validate_rejection_attribution({'decision': 'within_scope', 'inherited_baseline_findings': [finding]}, original, candidate)
    assert quality.summarize({}, [finding])['publication_hold']


@pytest.mark.parametrize('field', ['origin', 'reference'])
def test_malformed_attribution_enums_are_recoverable_protocol_failures(states, field):
    original, candidate, loop = states
    row = rejection(original['files']['src/lib.rs'], candidate['files']['src/lib.rs'], ['old'], ['new'])
    row['rejection_changes'][0][field] = ['invalid enum']
    with pytest.raises(Failure) as exc:
        scope.validate_rejection_attribution(row, original, candidate)
    assert exc.value.code == 'invalid_scope_review'
