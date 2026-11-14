"""Shared authority and fail-closed admission; no model/compiler/timing I/O."""
from copy import deepcopy

import pytest

from i2r_agent import optimization as opt, optimization_scope as scope
from i2r_agent import optimization_contracts as contracts, numeric_interface
from i2r_agent.common import Failure


@pytest.fixture
def state():
    runtime = numeric_interface.contract()
    root = 'constant:Example.walk'
    primitive = 'constant:Nat.minus_nat_inst.minus_nat'
    model = {'entries': [root], 'entities': {
        root: {'id': root, 'name': 'Example.walk', 'kind': 'constant', 'dependencies': [primitive],
               'execution_equations': [{'arguments': [{'text': 'Suc k'}, {'text': 'x # xs'}],
                   'rhs': {'text': 'x # walk k xs'}}]},
        primitive: {'id': primitive, 'name': 'Nat.minus_nat_inst.minus_nat', 'kind': 'constant',
                    'execution_equations': [{'arguments': [{'text': 'Suc m'}, {'text': 'Suc n'}],
                                            'rhs': {'text': 'minus_nat m n'}}]}}}
    return {'files': {'src/lib.rs': 'pub fn walk() {}'}, 'mapping': [{'source': root, 'rust_item': 'crate::walk'}],
        'rust_config': {'numeric_interface': {k: v for k, v in runtime.items() if k != 'guidance'}},
        'partition': {'owner': {root: 'unit'}, 'boundaries': [{
            'source': primitive, 'kind': 'native', 'basis': 'Natural subtraction',
            'conditions': ['Truncate at zero; never unsigned wrapping.',
                           'Only used in another function; walk uses Suc pattern cases.']}],
            'units': {}, 'order': []},
        'bundle': {'source_model': model, 'original_source_model': deepcopy(model), 'sources': {},
                   'numeric_policy': {'mode': 'arbitrary', 'numeric_interface': runtime}}}


def test_verified_runtime_and_real_guards_remain_authoritative_without_rewriting_analysis(state):
    before = deepcopy(state)
    material = contracts.context(state)
    assert material['numeric_runtime']['contract'] == numeric_interface.contract()
    assert material['numeric_runtime']['kind'] == 'controller_verified_paired_runtime'
    assert 'Nat subtraction truncates at zero' in material['numeric_runtime']['contract']['guidance']
    assert 'only used' in contracts.GUIDANCE.lower()
    assert 'Do not discard a real obligation' in contracts.GUIDANCE
    assert 'complete exact fallback' in contracts.GUIDANCE
    assert state == before
    # No unregistered subtraction contract is invented by this projection.
    assert material['registered_native_contracts']['contracts'] == []


@pytest.mark.parametrize('target', ['rust_config', 'numeric_policy'])
def test_changed_numeric_runtime_fails_before_model_evidence_is_supplied(state, target):
    value = state['rust_config'] if target == 'rust_config' else state['bundle']['numeric_policy']
    value['numeric_interface']['runtime_sha256'] = 'changed'
    with pytest.raises(Failure) as error: contracts.context(state)
    assert error.value.code == 'numeric_runtime_changed'


def test_generation_review_share_exact_contract_and_review_is_mode_neutral(state):
    class Budget:
        data = {'max_model_calls': 25, 'calls': 0, 'max_seconds': 3600}
        reserved_calls = 0
        def remaining(self): return 3600
        def elapsed(self): return 0
    requests = [opt.request(state, state, mode, Budget(), [], {}, False) for mode in ['rust-only', 'full']]
    assert requests[0]['performance_contract'] == requests[1]['performance_contract'] == contracts.context(state)
    reviews = []
    for mode in ['rust-only', 'full']:
        tagged = deepcopy(state); tagged['optimization_mode'] = mode
        reviews.append(scope.review_payload(state, [{'id': 'same', 'state': tagged, 'record': {}}]))
    assert reviews[0] == reviews[1]
    assert reviews[0]['candidates'][0]['performance_contract'] == requests[0]['performance_contract']
    assert contracts.GUIDANCE in opt.SYSTEM and contracts.GUIDANCE in scope.ONLINE_SYSTEM
    graph = next(iter(reviews[0]['source_graphs'].values()))
    # Keep original declarations and separately provide actual primitive equations.
    assert graph['boundaries'] == requests[0]['source_program']['boundaries']
    original_boundary = state['partition']['boundaries'][0]
    assert all(graph['boundaries'][0][k] == v for k, v in original_boundary.items())
    assert 'basis_and_conditions' in graph['boundaries'][0]['evidence_provenance']
    assert any(e['id'] == 'constant:Nat.minus_nat_inst.minus_nat' for e in graph['entities'])


def evidence(status='satisfied'):
    return {'obligations': status,
            'source_and_runtime': 'Suc k becomes k; verified Nat.sub_trunc computes exact natural subtraction.',
            'guards_and_ranges': 'Else branch establishes m != 0, so sub_trunc(m,1)=k; no machine narrowing.',
            'advisory_conflicts': [{'claim': 'Only used in another function',
                'authoritative_resolution': 'The use-site description cannot prohibit this same guarded Suc predecessor transition.'}]}


@pytest.mark.parametrize('status, expected', [('satisfied', 'within_scope'),
    ('violated', 'requires_source_change'), ('unknown', 'uncertain')])
def test_guard_or_domain_evidence_cannot_be_overridden_by_positive_verdict(status, expected):
    row = {'decision': 'within_scope', 'reason': 'Same recurrence', 'contract_evidence': evidence(status)}
    assert contracts.validate_evidence(row)['decision'] == expected


@pytest.mark.parametrize('change', [lambda r: r.pop('contract_evidence'),
    lambda r: r['contract_evidence'].update(obligations=[]),
    lambda r: r['contract_evidence'].update(guards_and_ranges=''),
    lambda r: r['contract_evidence'].update(advisory_conflicts='none'),
    lambda r: r['contract_evidence']['advisory_conflicts'][0].pop('authoritative_resolution')])
def test_malformed_contract_evidence_is_rejected(change):
    row = {'decision': 'within_scope', 'reason': 'Same recurrence', 'contract_evidence': evidence()}
    change(row)
    with pytest.raises(Failure) as error: contracts.validate_evidence(row)
    assert error.value.code == 'invalid_scope_review'


def test_numeric_exactness_does_not_waive_skipped_business_iterations():
    row = {'candidate_id': 'p', 'decision': 'within_scope', 'reason': 'Arithmetic is exact',
           'contract_evidence': evidence(),
           'transition_evidence': {'eliminated_source_iterations': True, 'changed_source_recurrence': False,
               'changed_source_marking_schedule': False, 'changed_source_operation_order': False,
               'explanation': 'Skip unchanged positions using an exact offset.'},
           'operation_order_evidence': [{'source_id': 'constant:Example.walk',
               'source_equation': 'walk (Suc k) (x # xs) = x # walk k xs',
               'events': [{'id': 'visit', 'source_operation': 'visit each position',
                           'rust_operation': 'visit marked offsets', 'rust_locations': ['walk'],
                           'correspondence': 'different_transition'}],
               'source_order': ['visit'], 'rust_order': ['visit'], 'identity_case': False, 'representation_relation': 'Different visits', 'comparison': 'changed'}]}
    assert scope.validate_admission_reply({'reviews': [row]}, 'p', {'constant:Example.walk'})['decision'] == 'requires_source_change'
