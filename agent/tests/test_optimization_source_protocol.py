"""Performance-only source protocol agrees with unchanged budget and renderer."""
from copy import deepcopy

from i2r_agent import optimization as opt, source_optimization, optimization_contracts, optimization_source_policy, optimization_scope


def state():
    entries = ['constant:Example.second', 'constant:Example.first']
    model = {'entries': entries, 'entities': {n: {'id': n, 'kind': 'constant'} for n in entries}}
    return {'files': {}, 'mapping': [], 'rust_config': {},
            'partition': {'owner': {}, 'boundaries': [], 'units': {}, 'order': []},
            'bundle': {'source_model': model, 'original_source_model': deepcopy(model), 'numeric_policy': {},
                       'sources': {'Export.thy': 'theory Export imports Main begin end'}}}


def test_source_available_budget_already_subtracts_rust_reserve_once(tmp_path, monkeypatch):
    budget = opt.Budget(tmp_path/'budget.json', 25, 3600)
    monkeypatch.setattr(budget, 'elapsed', lambda: 0)
    budget.begin_source()
    budget.data['calls'] = 2
    monkeypatch.setattr(budget, 'elapsed', lambda: 180)
    value = state(); request = opt.request(value, value, 'full', budget, [], {}, False, stage='source')
    counts = request['budget_accounting']
    assert counts['total_remaining'] == {'model_calls': 23, 'seconds': 3420}
    assert counts['rust_reserved'] == {'model_calls': 12, 'seconds': 1800}
    assert counts['phase_available'] == {'model_calls': min(23-12, 10-2), 'seconds': min(3420-1800, 1200-180)}
    assert request['remaining_calls'] == 8 and request['remaining_seconds'] == 1020
    # Eight source calls remain; being fewer than the twelve reserved Rust calls is not exhaustion.
    budget.begin_rust()
    rust = opt.request(value, value, 'full', budget, [], {}, False, stage='rust')['budget_accounting']
    assert rust['rust_reserved'] == {'model_calls': 0, 'seconds': 0}
    assert rust['phase_available'] == rust['total_remaining'] == counts['total_remaining']
    budget.close()


def test_export_name_protocol_matches_renderer_even_when_proposal_order_is_reversed():
    value = state(); protocol = opt.source_replacement_protocol(value)
    replacements = [{'source': n, 'rhs': 'helper_' + str(i),
                     'proof': 'by (simp add: i2r_entry_' + str(i) + '_def)'}
                    for i, n in enumerate(value['bundle']['original_source_model']['entries'])]
    definitions = 'definition helper_0 where "helper_0 = Example.second"\ndefinition helper_1 where "helper_1 = Example.first"'
    theory, export, roots = source_optimization.render(value['bundle'], {
        'definitions': definitions, 'replacements': list(reversed(replacements))})
    assert protocol['private_helpers_in_definitions'] and definitions in theory
    for row in protocol['exports']:
        assert roots[row['source']] == 'constant:Optimization.' + row['generated_entry']
        assert 'definition ' + row['generated_entry'] + ' where' in theory
        assert 'lemma ' + row['equivalence_theorem'] + ': "' + row['generated_entry'] + ' = ' + row['source'].split(':', 1)[1] + '"' in theory
        assert row['definition_theorem'] in theory
    assert export.index('Optimization.i2r_entry_0') < export.index('Optimization.i2r_entry_1')


def test_source_protocol_exposes_export_types_without_substituting_generic_helper_types():
    value = state(); original = value['bundle']['original_source_model']
    concrete = {'kind': 'type', 'name': 'Int.int', 'args': []}
    generic = {'kind': 'free', 'name': "'a", 'sort': ['Rings.comm_semiring_0']}
    original['entities'][original['entries'][0]]['source_type'] = concrete
    original['entities'][original['entries'][1]]['source_type'] = generic
    original['entities']['constant:Example.helper'] = {'source_type': generic}
    before = deepcopy(value)
    protocol = opt.source_replacement_protocol(value)
    assert [r['source_type'] for r in protocol['exports']] == [concrete, generic]
    assert 'internal helper' in protocol['type_authority']
    protocol['exports'][0]['source_type']['name'] = 'Changed'
    assert value == before


def test_source_generation_realization_and_admission_share_mathematical_case_rule():
    rule = optimization_contracts.MATHEMATICAL_CASE_GUIDANCE
    for system in [opt.SYSTEM, optimization_scope.ONLINE_SYSTEM, optimization_source_policy.SYSTEM]:
        assert rule in system
    assert 'No input-specific special cases' not in opt.SYSTEM
    assert 'unconditional Isabelle equivalence' in rule
    assert 'lookup table' in rule and 'cannot introduce' in rule



def test_source_proposal_allows_proved_recurrence_change_but_translation_and_rust_fix_current_source(tmp_path):
    budget = opt.Budget(tmp_path/'budget.json', 25, 3600); budget.begin_source()
    value = state()
    proposal = opt.request(value, value, 'full', budget, [], {}, False, stage='source')
    translation = opt.request(value, value, 'full', budget, [], {}, True, stage='source')
    assert proposal['stage_contract']['source_recurrence_change_allowed']
    assert proposal['allowed_actions'] == ['source', 'inspect', 'finish']
    assert not translation['stage_contract']['source_recurrence_change_allowed']
    assert translation['allowed_actions'] == ['rust', 'inspect', 'finish']
    assert 'computation_preservation' not in proposal['stage_contract']
    budget.begin_rust()
    full = opt.request(value, value, 'full', budget, [], {}, False, stage='rust')
    rust = opt.request(value, value, 'rust-only', budget, [], {}, False, stage='rust')
    for key in ['mode', 'allowed_actions', 'stage_contract', 'performance_contract', 'source_program']:
        assert full[key] == rust[key]
    assert full['mode'] == 'rust-only'
    assert translation['stage_contract']['computation_preservation'] == full['stage_contract']['computation_preservation']
    budget.close()
