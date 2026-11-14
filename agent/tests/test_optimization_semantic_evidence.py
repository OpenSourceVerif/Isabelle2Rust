"""Source-domain and primitive-event obligations; no model calls or benchmarks."""
from copy import deepcopy
from pathlib import Path
import hashlib

import pytest

from i2r_agent.common import Failure
from i2r_agent import optimization_scope as scope, optimization_contracts as contracts
from i2r_agent import optimization_source_authority as authority, numeric_interface

SOURCE = 'constant:Example.fold'
PRIMITIVE = 'constant:Groups.times_class.times'


@pytest.fixture
def state(tmp_path):
    # The current typed executable occurrence and an already-loaded source
    # catalog are separate authorities. Names by themselves never suffice.
    theory = tmp_path/'Groups.thy'
    theory.write_text('class ab_semigroup_mult = semigroup_mult +\n'
                      '  assumes mult_commute: "a * b = b * a"\nbegin\nend\n')
    var = {'kind': 'free', 'name': "'a", 'sort': ['Rings.comm_semiring_0']}
    typ = {'kind': 'type', 'name': 'fun', 'args': [var, {'kind': 'type', 'name': 'fun', 'args': [var, var]}]}
    model = {'entries': [SOURCE], 'entities': {
        SOURCE: {'id': SOURCE, 'kind': 'constant', 'name': 'Example.fold',
                 'type_variables': [{'name': "'a", 'sort': ['Rings.comm_semiring_0']}],
                 'instance_resolutions': [{'constant': 'Groups.times_class.times', 'type': typ,
                                            'implementation': 'Groups.times_class.times'}]},
        'class:Rings.comm_semiring_0': {'id': 'class:Rings.comm_semiring_0', 'kind': 'class',
                                      'supers': ['class:Groups.ab_semigroup_mult']},
        'class:Groups.ab_semigroup_mult': {'id': 'class:Groups.ab_semigroup_mult', 'kind': 'class', 'supers': []}}}
    return {'bundle': {'source_model': model, 'source_catalog': [{'theory': 'HOL.Groups', 'path': str(theory),
                     'sha256': hashlib.sha256(theory.read_bytes()).hexdigest()}], 'numeric_policy': {}},
            'files': {'src/lib.rs': 'pub fn fold() {}'}, 'mapping': [], 'rust_config': {},
            'partition': {'owner': {n: 'unit' for n in model['entities']}, 'boundaries': []}, 'connector': {}}


@pytest.fixture
def evidence(state):
    runtime = {'kind': 'controller_verified_paired_runtime', 'contract': numeric_interface.contract()}
    return {'primitive_operand_symmetry': {'source_laws': authority.context(state),
                                          'runtime_contracts': contracts.runtime_symmetry_contracts(runtime)}}


def review(evidence):
    law = evidence['primitive_operand_symmetry']['source_laws']['evidence'][0]
    runtime = next(r for r in evidence['primitive_operand_symmetry']['runtime_contracts'] if r['primitive'] == PRIMITIVE)
    return {'candidate_id': 'case', 'decision': 'within_scope', 'reason': 'Same primitive event and recurrence.',
        'contract_evidence': {'obligations': 'satisfied', 'source_and_runtime': 'Bound source/runtime evidence.',
                             'guards_and_ranges': 'Same checked intermediate and arbitrary result.', 'advisory_conflicts': []},
        'transition_evidence': {'eliminated_source_iterations': False, 'changed_source_recurrence': False,
            'changed_source_marking_schedule': False, 'changed_source_operation_order': False, 'explanation': 'Same fold steps.'},
        'operation_order_evidence': [{'source_id': SOURCE, 'source_equation': 'step a acc = a * acc',
            'events': [{'id': 'mul', 'source_operation': 'a times acc', 'rust_operation': 'acc times a',
                        'rust_locations': ['fold accumulator update'], 'correspondence': 'same_transition',
                        'primitive_equivalence': {'kind': 'operand_symmetry', 'primitive': PRIMITIVE,
                            'source_law_id': law['evidence_id'], 'runtime_contract_id': runtime['evidence_id'],
                            'same_operand_evaluation': True, 'same_primitive_sequence': True,
                            'same_association': True, 'same_recurrence_and_visits': True,
                            'no_new_generic_restrictions': True, 'value_and_definedness': 'preserved',
                            'implementation_domain': 'source_lawful_generic',
                            'implementation_evidence': 'Generic default delegates to the same source-lawful times; actual numeric override uses the verified operator.',
                            'explanation': 'One multiplication at the same step. Both checked products have identical representability; arbitrary products agree.'}}],
            'source_order': ['mul'], 'rust_order': ['mul'], 'identity_case': False,
            'representation_relation': 'Same accumulator value with owned left operand.', 'comparison': 'preserved'}]}


def validate(row, evidence):
    return scope.validate_admission_reply({'reviews': [row]}, 'case', {SOURCE}, evidence)


def test_local_commutative_primitive_has_same_event_under_verified_source_and_runtime(evidence):
    assert validate(review(evidence), evidence)['decision'] == 'within_scope'


@pytest.mark.parametrize('missing', ['class', 'catalog', 'hash', 'occurrence_sort', 'typed_occurrence'])
def test_no_law_from_names_missing_class_or_unverified_source(state, evidence, missing):
    if missing == 'class': del state['bundle']['source_model']['entities']['class:Groups.ab_semigroup_mult']
    elif missing == 'catalog': state['bundle']['source_catalog'] = []
    elif missing == 'hash': state['bundle']['source_catalog'][0]['sha256'] = 'changed'
    elif missing == 'typed_occurrence': state['bundle']['source_model']['entities'][SOURCE]['instance_resolutions'] = []
    else:
        occurrence = state['bundle']['source_model']['entities'][SOURCE]['instance_resolutions'][0]
        occurrence['type']['args'][0]['sort'] = []
    row = review(evidence); evidence['primitive_operand_symmetry']['source_laws'] = authority.context(state)
    assert not evidence['primitive_operand_symmetry']['source_laws']['evidence']
    assert validate(row, evidence)['decision'] == 'uncertain'


def test_noncommutative_operation_cannot_reuse_multiplication_law(evidence):
    row = review(evidence)
    row['operation_order_evidence'][0]['events'][0]['primitive_equivalence']['primitive'] = 'constant:Groups.minus_class.minus'
    assert validate(row, evidence)['decision'] == 'uncertain'


@pytest.mark.parametrize('flag', ['same_operand_evaluation', 'same_primitive_sequence', 'same_association',
                                 'same_recurrence_and_visits', 'no_new_generic_restrictions'])
def test_local_law_does_not_waive_changed_computation_or_bounds(evidence, flag):
    row = review(evidence)
    row['operation_order_evidence'][0]['events'][0]['primitive_equivalence'][flag] = False
    assert validate(row, evidence)['decision'] == 'requires_source_change'


def test_checked_reassociation_has_different_overflow_domain_and_is_rejected(evidence):
    high = 2**127 - 1
    def checked(a, b):
        result = a + b
        if not -2**127 <= result <= high: raise OverflowError
        return result
    with pytest.raises(OverflowError): checked(checked(high, 1), -1)
    assert checked(high, checked(1, -1)) == high
    row = review(evidence)
    proof = row['operation_order_evidence'][0]['events'][0]['primitive_equivalence']
    proof.update(kind='reassociation', same_association=False, value_and_definedness='changed')
    assert validate(row, evidence)['decision'] == 'requires_source_change'


def test_acomp_business_permutation_cannot_be_hidden_by_primitive_law(evidence):
    row = review(evidence); pair = row['operation_order_evidence'][0]
    pair['events'].extend([{'id': name, 'source_operation': name, 'rust_operation': name,
                           'rust_locations': ['compile tree'], 'correspondence': 'same_transition'}
                          for name in ['right', 'left']])
    pair['source_order'] = ['mul', 'right', 'left']; pair['rust_order'] = ['left', 'right', 'mul']
    assert validate(row, evidence)['decision'] == 'requires_source_change'


def test_different_runtime_version_supplies_no_operand_symmetry_permission():
    runtime = {'kind': 'controller_verified_paired_runtime', 'contract': {'runtime_sha256': 'not-audited'}}
    assert contracts.runtime_symmetry_contracts(runtime) == []


def add_abstract_type(state):
    model = state['bundle']['source_model']; type_id = 'type:Example.abstract'
    variable = {'name': "'a", 'sort': ['Groups.zero']}
    model['entities'][type_id] = {'id': type_id, 'kind': 'type', 'abstract': True, 'variables': [variable],
        'constructors': [{'id': 'constant:Example.Abs', 'variables': [variable], 'fields': []}]}
    model['entities']['constant:Example.rep'] = {'id': 'constant:Example.rep', 'kind': 'constant',
        'execution_equations': [{'arguments': [{'abstraction': 'Example.Abs', 'text': 'Abs x',
                                               'term': {'kind': 'free', 'name': 'typed_original'}}],
                                 'rhs': {'abstraction': None, 'text': 'x'}, 'theorem': None, 'proper': True}]}
    state['partition']['owner'].update({type_id: 'unit', 'constant:Example.rep': 'unit'})
    return type_id


def obligation(type_id):
    return {'type_id': type_id, 'role': 'code_representation',
            'source_domain_evidence': 'Code certificate requires its justified representation domain.',
            'construction_and_adapter_evidence': 'Construction and input conversion establish that domain.',
            'mapped_helper_evidence': 'Projection is used on the same valid represented source values.',
            'usage_or_reachability_changed': False, 'invariant_dependency_changed': False,
            'change_scope': 'unchanged_helpers_and_use',
            'candidate': {'status': 'satisfied', 'evidence': 'Ownership only; no newly reachable domain.'}}


def test_abstract_metadata_and_typed_certificate_survive_without_unconditional_theorem(state):
    type_id = add_abstract_type(state)
    source = scope.compact_source(state)
    types = {r['id']: r for r in source['entities']}
    assert types[type_id]['abstract'] is True and types[type_id]['variables'][0]['sort'] == ['Groups.zero']
    equation = types['constant:Example.rep']['execution_equations'][0]
    assert equation['arguments'][0]['abstraction'] == 'Example.Abs' and equation['theorem'] is None
    role = contracts.abstract_representation_roles(state)[0]
    certificate = role['code_certificates'][0]
    assert certificate['logical_theorem_present'] is False
    assert certificate['abstraction_roles'][0]['typed_term']['name'] == 'typed_original'
    assert 'not an unconditional HOL equation' in certificate['authority_limit']
    assert role['declared_source_exports'] == [SOURCE]


def test_every_current_abstract_type_requires_structured_applicability(state, evidence):
    type_id = add_abstract_type(state)
    evidence['abstract_representation_roles'] = contracts.abstract_representation_roles(state)
    row = review(evidence)
    with pytest.raises(Failure): validate(row, evidence)
    row['abstract_type_obligations'] = [obligation(type_id)]
    assert validate(row, evidence)['decision'] == 'within_scope'


@pytest.mark.parametrize('status,decision', [('violated', 'requires_source_change'), ('unknown', 'uncertain')])
def test_candidate_obligations_still_fail_closed(state, evidence, status, decision):
    type_id = add_abstract_type(state); evidence['abstract_representation_roles'] = contracts.abstract_representation_roles(state)
    row = review(evidence); item = obligation(type_id)
    item['candidate']['status'] = status
    row['abstract_type_obligations'] = [item]
    assert validate(row, evidence)['decision'] == decision


def test_new_usage_of_unchanged_helper_reopens_current_domain_obligations(state, evidence):
    type_id = add_abstract_type(state); evidence['abstract_representation_roles'] = contracts.abstract_representation_roles(state)
    row = review(evidence); item = obligation(type_id)
    item['usage_or_reachability_changed'] = True
    item['change_scope'] = 'modified_or_activated'
    item['candidate'] = {'status': 'unknown', 'evidence': 'New raw values reach inherited projection; validity has not been shown.'}
    row['abstract_type_obligations'] = [item]
    assert validate(row, evidence)['decision'] == 'uncertain'


def test_source_law_evidence_hash_changes_admission_identity(state):
    option = {'id': 'case', 'state': state, 'record': {}}
    before = scope.admission_identity(state, option, scope.admission_payload(state, option, state))
    state['bundle']['source_catalog'][0]['sha256'] = 'no-longer-matching'
    after = scope.admission_identity(state, option, scope.admission_payload(state, option, state))
    assert before != after


def test_abstract_adapter_changes_are_part_of_review_cache_evidence(state):
    add_abstract_type(state)
    option = {'id': 'case', 'state': state, 'record': {}}
    before = scope.admission_identity(state, option, scope.admission_payload(state, option, state))
    state['connector'] = {'src/lib.rs': 'fn convert(raw: Vec<Int>) { let value = raw_constructor(raw); }'}
    after = scope.admission_identity(state, option, scope.admission_payload(state, option, state))
    assert before != after



def test_valid_law_cannot_be_reused_at_a_different_valid_source_occurrence(evidence):
    row = review(evidence); other = 'constant:Example.other'
    row['operation_order_evidence'][0]['source_id'] = other
    result = scope.validate_admission_reply({'reviews': [row]}, 'case', {SOURCE, other}, evidence)
    assert result['decision'] == 'uncertain'


def test_numeric_runtime_hash_does_not_prove_unknown_generic_override(evidence):
    row = review(evidence)
    row['operation_order_evidence'][0]['events'][0]['primitive_equivalence']['implementation_domain'] = 'unknown'
    assert validate(row, evidence)['decision'] == 'uncertain'


def test_explicitly_unknown_unchanged_role_requires_separate_baseline_disclosure(state, evidence):
    type_id = add_abstract_type(state); evidence['abstract_representation_roles'] = contracts.abstract_representation_roles(state)
    row = review(evidence); item = obligation(type_id); item['role'] = 'unknown'
    row['abstract_type_obligations'] = [item]
    with pytest.raises(Failure): validate(row, evidence)
    baseline = {'source_ids': [type_id]}
    row['inherited_baseline_findings'] = [{'source_ids': [type_id], 'status': 'unknown',
        'declared_root_impact': 'unknown', 'finding': 'Inherited representation role requires clarification.',
        'evidence': 'No new use or domain; candidate refinement does not resolve baseline root applicability.'}]
    assert scope.validate_admission_reply({'reviews': [row]}, 'case', {SOURCE}, evidence, baseline)['decision'] == 'within_scope'
