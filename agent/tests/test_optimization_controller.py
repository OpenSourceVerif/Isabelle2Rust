"""Bounded source-first search using real budgets, admission seals and selection.

Compiler/prover/timing/model I/O is replaced with deterministic fixtures. No
external service is contacted and no benchmark is run by these tests.
"""
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from i2r_agent import optimization as opt, optimization_scope as scope
from i2r_agent.common import Failure, read, save


def rust(label):
    return {'action': 'rust', 'files': {'src/lib.rs': f'pub fn f() {{ /* {label} */ }}'}}


def source(label='linear'):
    return {'action': 'source', 'direction_id': label,
            'source_assessment': 'Base.f repeats list traversal; use a proved linear traversal and equality lemma.'}


@pytest.fixture
def controller(tmp_path, monkeypatch):
    baseline = tmp_path/'baseline'
    save(baseline/'tasks/example/diagnostics/support-tests/frozen.json', [])
    model = {'entries': ['constant:Base.f'], 'entities': {'constant:Base.f': {
        'id': 'constant:Base.f', 'kind': 'function', 'name': 'Base.f',
        'source_type': {'kind': 'type', 'name': 'Nat.nat', 'args': []}, 'dependencies': []}}}
    original = {'files': {'src/lib.rs': 'pub fn f() { /* A0 */ }'}, 'rust_config': {},
                'mapping': [{'source': 'constant:Base.f', 'rust_item': 'crate::f'}],
                'partition': {'owner': {'constant:Base.f': 'unit'}, 'boundaries': []},
                'connector': {}, 'support_evidence': {'frozen_identity': 'frozen'},
                'bundle': {'numeric_policy': {}, 'sources': {'Base.thy': 'source'},
                           'source_model': model, 'original_source_model': deepcopy(model)}}
    cfg = {'translation': {}, 'budgets': {}, 'testing': {'process_timeout': 1}}
    events = []; requests = []; reviews = []; proposals = []; gains = []; review_decisions = []
    def freeze(run, row, directory, **kwargs):
        save(directory/'frozen.json', {'test': 'identity'})
        return deepcopy(original), deepcopy(cfg), {}, {'original_files': {}}
    monkeypatch.setattr(opt.numeric_experiment, 'freeze', freeze)
    monkeypatch.setattr(opt.source_optimization, 'source_context', lambda s: deepcopy(s['bundle']['source_model']))
    monkeypatch.setattr(opt, 'computation', lambda b, **kw: nullcontext())
    monkeypatch.setattr(opt, 'profile', lambda s, *a, **k: {'status': 'test-profile', 'version': opt.version(s)})
    def materialize(path, files, rc):
        path = Path(path); path.mkdir(parents=True, exist_ok=True)
        for name, value in files.items():
            f = path/name; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(value)
        return path
    def connection(path, *args):
        path = path/'harness'; path.mkdir(parents=True, exist_ok=True); return path
    monkeypatch.setattr(opt, 'materialize', materialize)
    monkeypatch.setattr(opt, 'connection', connection)
    def build(crate, cfg, case, directory, budget):
        value = {'source': str(crate), 'work': str(directory)}
        save(directory/'build-v2.json', value); return value
    monkeypatch.setattr(opt, 'timing_build', build)
    def prove(original, reply, cfg, executor, directory):
        events.append('prove')
        bundle = deepcopy(original['bundle']); new = 'constant:Optimized.f'
        entity = deepcopy(model['entities']['constant:Base.f']); entity['id'] = new
        bundle['source_model'] = {'entries': [new], 'entities': {new: entity}}
        bundle['source_equivalence'] = {'directory': str(directory), 'status': 'proved',
                                      'original_to_optimized': {'constant:Base.f': new}}
        save(directory/'extraction/program.json', bundle)
        return bundle
    def rebase(original, incumbent, bundle):
        state = deepcopy(incumbent); state['bundle'] = bundle
        state['mapping'] = [{'source': 'constant:Optimized.f', 'rust_item': 'crate::f'}]
        state['partition']['owner'] = {'constant:Optimized.f': 'unit'}
        return state
    monkeypatch.setattr(opt.source_optimization, 'prove', prove)
    monkeypatch.setattr(opt.source_optimization, 'rebase', rebase)
    def apply(state, reply, original, cfg, directory):
        events.append('apply'); result = deepcopy(state); result['files'].update(reply['files'])
        save(directory/'transaction.json', {'before': deepcopy(state), 'after': result}); return result
    monkeypatch.setattr(opt, 'apply_candidate', apply)
    def validate(state, cfg, tests, observations, directory, executor):
        events.append('validate')
        crate = materialize(directory/'candidate', state['files'], {})
        evidence = {'status': 'passed', 'candidate_version': opt.version(state)}
        save(directory/'validation.json', evidence); return crate, evidence
    monkeypatch.setattr(opt, 'build_and_validate', validate)
    def compare(*args):
        events.append('compare')
        return {'accepted': gains.pop(0) if gains else True, 'geomean_speedup': 2}
    monkeypatch.setattr(opt, 'compare', compare)
    class Provider:
        def __init__(self, cfg, directory):
            self.cfg = cfg; self.calls = 0; self.usage = {}; self.unknown_usage_requests = []
        def call(self, system, payload, **kwargs):
            self.calls += 1; payload = json.loads(payload)
            if kwargs['phase'] == 'performance_scope_admission':
                events.append('admit'); reviews.append(payload)
                decision = review_decisions.pop(0) if review_decisions else 'within_scope'
                return {'reviews': [{'candidate_id': payload['candidates'][0]['candidate_id'],
                    'decision': decision, 'reason': 'The supplied source transition is preserved.',
                    'rejection_changes': [{'origin': 'introduced', 'reference': 'original',
                        'source_ids': [next(iter(payload['source_graphs'].values()))['entries'][0]],
                        'before': {'path': 'src/lib.rs', 'excerpt': original['files']['src/lib.rs']},
                        'after': {'path': 'src/lib.rs', 'excerpt': payload['candidates'][0]['files']['src/lib.rs']},
                        'before_events': ['original stub'], 'after_events': ['changed stub'],
                        'explanation': 'Deterministic test reviewer rejects the supplied changed stub.'}],
                    'contract_evidence': {'obligations': 'satisfied', 'source_and_runtime': 'No primitive in this stub.',
                                          'guards_and_ranges': 'No numeric domain change.', 'advisory_conflicts': []},
                    'transition_evidence': {'eliminated_source_iterations': False, 'changed_source_recurrence': False,
                                            'changed_source_marking_schedule': False, 'changed_source_operation_order': False,
                                            'explanation': 'Same supplied transitions.'},
                    'operation_order_evidence': [{
                        'source_id': next(iter(payload['source_graphs'].values()))['entries'][0],
                        'source_equation': 'Stub function returns unit without business operations.',
                        'events': [], 'source_order': [], 'rust_order': [], 'identity_case': True, 'representation_relation': 'Identity stub realization.',
                        'comparison': 'preserved'}]}]}
            requests.append(payload)
            value = proposals.pop(0)
            if callable(value): return value(payload, self)
            return deepcopy(value)
    monkeypatch.setattr(opt, 'Provider', Provider)
    def run(script, mode='full', seconds=3600, calls=25, destination='search'):
        proposals.extend(script)
        return opt.optimize_case(baseline, {'id': 'example'}, mode, tmp_path/destination,
                                 {'max_model_calls': calls, 'max_seconds': seconds})
    return {'run': run, 'requests': requests, 'reviews': reviews, 'events': events,
            'original': original, 'gains': gains, 'review_decisions': review_decisions,
            'directory': tmp_path/'search'}


def test_proved_source_is_frozen_then_multiple_rust_refinements_are_accepted(controller):
    c = controller
    result = c['run']([source(), rust('source translation'), rust('refinement 1'), rust('refinement 2'),
                       {'action': 'finish', 'reason': 'Done'}])
    assert [r['stage'] for r in c['requests']] == ['source', 'source', 'rust', 'rust', 'rust']
    assert all(r['source_program']['entries'] == ['constant:Optimized.f'] for r in c['requests'][1:])
    assert c['events'] == ['prove'] + ['apply', 'validate', 'admit', 'compare'] * 3
    assert result['model_calls'] == 8
    assert result['source_stage']['model_calls'] == 3
    assert result['source_stage']['accepted'] and result['selected_source_optimized']
    assert 'refinement 2' in read(c['directory']/'selected-state.json')['files']['src/lib.rs']
    assert len(read(c['directory']/'scope-review/review.json')['reviews']) == 3
    assert result['scope_selection']['model_calls'] == 0
    assert result['stage_schema'] == 2 and result['completed_stage'] == 'rust'


def test_failed_source_screen_returns_to_a0_before_rust(controller):
    c = controller; c['gains'].extend([False, True])
    result = c['run']([source(), rust('unhelpful source'),
                       {'action': 'finish', 'source_assessment': 'No other useful source change', 'reason': 'Skip'},
                       rust('A0 refinement'), {'action': 'finish'}])
    assert not result['source_stage']['accepted'] and not result['selected_source_optimized']
    assert c['requests'][3]['source_program']['entries'] == ['constant:Base.f']
    assert c['requests'][3]['files'] == c['original']['files']
    assert 'A0 refinement' in read(c['directory']/'selected-state.json')['files']['src/lib.rs']


def test_source_proof_failure_is_bounded_and_then_rust_can_continue(controller, monkeypatch):
    c = controller
    monkeypatch.setattr(opt.source_optimization, 'prove', lambda *a, **k: (_ for _ in ()).throw(Failure('proof_failed', 'bad proof')))
    script = [source('direction one')] * 5 + [source('direction two')] * 5 + [rust('fallback'), {'action': 'finish'}]
    result = c['run'](script)
    assert result['source_stage']['model_calls'] == 10
    assert result['source_stage']['stop'] == 'optimization_source_budget_exhausted'
    assert len(result['source_stage']['directions']) == 2
    assert c['requests'][10]['stage'] == 'rust'
    assert c['requests'][10]['files'] == c['original']['files']
    assert result['model_calls'] == 13 and result['budget']['calls'] == 13


def test_scope_rejection_never_becomes_next_search_basis(controller):
    c = controller; c['review_decisions'].extend(['requires_source_change', 'within_scope'])
    result = c['run']([rust('unproved stride'), rust('buffer reuse'), {'action': 'finish'}], mode='rust-only')
    assert c['requests'][1]['files'] == c['original']['files']
    assert c['events'].count('compare') == 1
    assert [r['status'] for r in result['attempts']] == ['optimization_scope_rejected', 'accepted', 'finished']
    assert len(read(c['directory']/'scope-review/review.json')['reviews']) == 1


def test_three_measured_no_gain_candidates_allow_later_gain_without_source_restart(controller):
    c = controller; c['gains'].extend([False, False, False])
    result = c['run']([{'action': 'finish', 'source_assessment': 'No useful source opportunity'},
                       rust('one'), rust('two'), rust('three'), rust('four'), {'action': 'finish'}])
    assert result['stop'] != 'three_candidates_without_acceptance'
    assert [r['stage'] for r in c['requests']] == ['source'] + ['rust'] * 5
    assert result['model_calls'] == 10 and result['improved']


def test_three_protocol_errors_do_not_end_search_before_valid_candidate(controller):
    c = controller
    def bad(*args): raise Failure('invalid_model_response', 'broken JSON')
    result = c['run']([bad, bad, bad, rust('real candidate'), {'action': 'finish'}], mode='rust-only')
    assert result['improved'] and result['model_calls'] == 6
    assert [a['status'] for a in result['attempts'][:3]] == ['invalid_model_response']*3
    assert result['stop'] != 'three_candidates_without_acceptance'


@pytest.mark.parametrize('mode', ['rust-only', 'full'])
def test_scope_rejections_do_not_consume_measured_stagnation_allowance(controller, mode):
    c = controller
    c['review_decisions'].extend(['requires_source_change'] * 3 + ['within_scope'])
    script = [rust('rejected one'), rust('rejected two'), rust('rejected three'),
              rust('admissible storage change'), {'action': 'finish'}]
    if mode == 'full':
        script.insert(0, {'action': 'finish', 'source_assessment': 'No useful source direction'})
    result = c['run'](script, mode=mode)
    rust_attempts = [a for a in result['attempts'] if a.get('action') == 'rust']
    assert [a['status'] for a in rust_attempts] == ['optimization_scope_rejected'] * 3 + ['accepted']
    assert result['improved'] and c['events'].count('compare') == 1
    assert result['stop'] != 'three_candidates_without_acceptance'
    assert result['model_calls'] == (10 if mode == 'full' else 9)


def test_short_total_budget_preserves_rust_phase(controller):
    c = controller
    result = c['run']([rust('within short budget'), {'action': 'finish'}], seconds=60)
    assert all(r['stage'] == 'rust' for r in c['requests'])
    assert result['source_stage']['stop'] == 'optimization_source_budget_exhausted'


def test_source_measurement_deadline_falls_back_without_spending_reserved_rust_time(controller, monkeypatch):
    c = controller; comparisons = []
    def compare(*args):
        budget = args[-1]; comparisons.append(budget.data['active_phase'])
        if budget.data['active_phase'] == 'source':
            budget.previous += 1201
            raise Failure('optimization_time_exhausted', 'Timing worker reached its phase deadline')
        return {'accepted': True}
    monkeypatch.setattr(opt, 'compare', compare)
    result = c['run']([source(), rust('source translation'), rust('fallback Rust'), {'action': 'finish'}])
    assert comparisons == ['source', 'rust']
    assert result['source_stage']['stop'] == 'optimization_source_budget_exhausted'
    assert result['budget']['charged_seconds'] >= 1201
    assert result['budget']['charged_seconds'] < 1800
    assert c['requests'][2]['files'] == c['original']['files']
    assert c['requests'][2]['source_program']['entries'] == ['constant:Base.f']
    assert not result['selected_source_optimized']


def test_source_direction_limit_counts_directions_not_proof_repairs():
    directions = []
    for name in ['one', 'one', 'two', 'two']:
        assert opt.source_direction(source(name), directions) == name
    with pytest.raises(Failure) as error:
        opt.source_direction(source('three'), directions)
    assert error.value.code == 'invalid_source_direction'
    assert error.value.evidence['registered_directions'] == ['one', 'two']
    assert directions == ['one', 'two']


def test_unknown_full_direction_label_does_not_end_source_or_run_an_extra_direction(controller, monkeypatch):
    c = controller; prove = opt.source_optimization.prove; proof_calls = []
    def repairable(original, reply, cfg, executor, directory):
        proof_calls.append(reply['direction_id'])
        if len(proof_calls) <= 2:
            raise Failure('tool_failed', 'A concrete proof subgoal remains')
        return prove(original, reply, cfg, executor, directory)
    monkeypatch.setattr(opt.source_optimization, 'prove', repairable)
    result = c['run']([source('partition'), source('accumulator'), source('renamed-partition'),
                       source('partition'), rust('proved repair'), {'action': 'finish'}])
    assert proof_calls == ['partition', 'accumulator', 'partition']
    assert result['source_stage']['directions'] == ['partition', 'accumulator']
    assert result['attempts'][2]['status'] == 'invalid_source_direction'
    assert c['requests'][3]['stage'] == 'source'
    assert c['requests'][3]['feedback']['evidence']['registered_directions'] == ['partition', 'accumulator']
    assert result['selected_source_optimized'] and result['model_calls'] == 7


def test_theory_reads_preserve_search_state_and_do_not_consume_failure_streak(controller):
    c = controller
    request = {'action': 'inspect', 'request_sources': [{'path': 'Base.thy', 'start_line': 1, 'end_line': 1}]}
    result = c['run']([request, request, request, rust('after reading'), {'action': 'finish'}], mode='rust-only')
    assert result['improved']
    assert [r['status'] for r in result['attempts']][:3] == ['source_material_read']*3
    assert c['requests'][3]['requested_source_material']['sources'][0]['text'] == 'source'
    assert len(c['requests'][3]['requested_source_material']['sources']) == 1
    assert c['events'] == ['apply', 'validate', 'admit', 'compare']


def test_source_time_cap_and_global_elapsed_are_never_reset(tmp_path):
    budget = opt.Budget(tmp_path/'budget.json', 25, 3600, reserved_calls=2)
    budget.begin_source(); start = budget.data['source_phase']['start_seconds']
    budget.previous += 1201
    with pytest.raises(Failure) as exc: budget.remaining()
    assert exc.value.code == 'optimization_source_budget_exhausted'
    budget.begin_rust()
    assert budget.remaining() < 2399 and budget.data['source_phase']['start_seconds'] == start
    budget.close()
    resumed = opt.Budget(tmp_path/'budget.json', 25, 3600, reserved_calls=2)
    assert resumed.elapsed() >= 1201
    resumed.close()


def test_exact_rejected_candidate_uses_cached_scope_decision(controller):
    c = controller; c['gains'].extend([False, False, False])
    result = c['run']([rust('same change')] * 3 + [{'action': 'finish'}], mode='rust-only')
    assert result['stop'] != 'three_candidates_without_acceptance'
    assert result['model_calls'] == 5  # Three proposals, one cached review, explicit finish.
    assert len(c['reviews']) == 1
    assert [read(Path(r['path'])/'scope-admission.json')['cached'] for r in result['attempts'][:3]] == [False, True, True]


def test_countdown_stride_cannot_be_admitted_and_cache_is_source_specific(controller, tmp_path):
    original = controller['original']; state = deepcopy(original); state['files'].update(rust('stride')['files'])
    class Provider:
        calls = 0
        cfg = {'budgets': {}}
        def call(self, system, payload, **kwargs):
            self.calls += 1; candidate = json.loads(payload)['candidates'][0]
            return {'reviews': [{'candidate_id': candidate['candidate_id'], 'decision': 'within_scope',
                'reason': 'Equivalent output, but visits only marked positions.',
                'rejection_changes': [{'origin': 'introduced', 'reference': 'original',
                    'source_ids': ['constant:Base.f'],
                    'before': {'path': 'src/lib.rs', 'excerpt': original['files']['src/lib.rs']},
                    'after': {'path': 'src/lib.rs', 'excerpt': candidate['files']['src/lib.rs']},
                    'before_events': ['visit every position'], 'after_events': ['visit marked positions'],
                    'explanation': 'New stride skips logical countdown visits.'}],
                'contract_evidence': {'obligations': 'satisfied', 'source_and_runtime': 'The arithmetic alone is exact.',
                    'guards_and_ranges': 'No narrowing claim; business visits still differ.', 'advisory_conflicts': []},
                'transition_evidence': {'eliminated_source_iterations': True, 'changed_source_recurrence': False,
                    'changed_source_marking_schedule': True, 'changed_source_operation_order': True,
                    'explanation': 'Skips copied-through countdown positions.'},
                'operation_order_evidence': [{'source_id': 'constant:Base.f',
                    'source_equation': 'Visit every countdown position.',
                    'events': [{'id': 'visit', 'source_operation': 'visit every position',
                                'rust_operation': 'visit marked positions', 'rust_locations': ['crate::f'],
                                'correspondence': 'different_transition'}],
                    'source_order': ['visit'], 'rust_order': ['visit'], 'identity_case': False, 'representation_relation': 'No order-preserving relation.',
                    'comparison': 'changed'}]}]}
    provider = Provider(); budget = opt.Budget(tmp_path/'scope-budget.json')
    def admission(attempt, value):
        path = tmp_path/'attempts'/attempt
        with pytest.raises(Failure) as exc:
            scope.admit(original, value, {'path': str(path)}, provider, budget, path)
        assert exc.value.code == 'optimization_scope_rejected'
        return read(path/'scope-admission.json')
    first = admission('001', state); second = admission('002', state)
    assert first['review']['decision'] == 'requires_source_change'
    assert second['cached'] and second['review']['candidate_id'] == '002'
    assert provider.calls == 1
    changed_source = deepcopy(state); changed_source['bundle']['source_model']['entities']['constant:Base.f']['name'] = 'Revised.f'
    assert not admission('003', changed_source)['cached']
    assert provider.calls == 2 and budget.data['calls'] == 2
    budget.close()


def test_final_seal_refuses_changed_admission_and_matrix_consumer_accepts_new_format(controller, tmp_path):
    import shutil
    from i2r_agent.optimization_matrix import selected
    c = controller; result = c['run']([rust('accepted'), {'action': 'finish'}], mode='rust-only')
    run = tmp_path/'delivery'; shutil.copytree(c['directory'], run/'optimization/example')
    state, delivered = selected(run, 'example', c['original'])
    assert 'accepted' in state['files']['src/lib.rs'] and delivered['stage_schema'] == 2
    link = result['attempts'][0]['scope_admission']; path = Path(link['path'])
    value = read(path); value['review']['decision'] = 'uncertain'; save(path, value)
    with pytest.raises(Failure) as exc:
        scope.finalize_admissions(c['original'], result['baseline'], result['attempts'], tmp_path/'tampered-review')
    assert exc.value.code == 'optimization_admission_changed'


def test_every_call_up_to_total_allowance_can_be_used_and_failure_still_counts(tmp_path):
    class Provider:
        calls = 0
        cfg = {'budgets': {}}
        def call(self, *args, **kwargs):
            self.calls += 1
            raise Failure('provider_failed', 'charged attempt')
    provider = Provider(); budget = opt.Budget(tmp_path/'budget.json', 25, 3600)
    budget.begin_source()
    for _ in range(10):
        with pytest.raises(Failure, match='charged attempt'): budget.call(provider, {})
    with pytest.raises(Failure) as exc: budget.call(provider, {})
    assert exc.value.code == 'optimization_source_budget_exhausted'
    budget.begin_rust()
    for _ in range(15):
        with pytest.raises(Failure, match='charged attempt'): budget.call(provider, {})
    with pytest.raises(Failure) as exc: budget.call(provider, {})
    assert exc.value.code == 'optimization_calls_exhausted' and provider.calls == 25
    budget.close()


def test_legacy_results_are_read_only_and_unfinished_searches_require_new_directory(tmp_path, monkeypatch):
    legacy = tmp_path/'done'; save(legacy/'result.json', {'scope_selection': {'old': True}})
    monkeypatch.setattr(opt.numeric_experiment, 'freeze', lambda *a, **k: pytest.fail('Legacy result must be read-only'))
    assert opt.optimize_case('missing', {'id': 'old'}, 'full', legacy, {}) == {'scope_selection': {'old': True}}
    pending = tmp_path/'pending'; save(pending/'search-state.json', {'stage_schema': 1})
    with pytest.raises(Failure) as exc: opt.optimize_case('missing', {'id': 'old'}, 'full', pending, {})
    assert exc.value.code == 'optimization_stage_migration_required'


def test_exclusive_measurement_waits_for_shared_preparation_and_charges_wait(tmp_path, monkeypatch):
    # Keep the real resource coordinator here, unlike the controller fixture.
    monkeypatch.setattr(opt, 'ROOT', tmp_path)
    preparation_started = threading.Event(); release = threading.Event(); timing_started = threading.Event()
    def prepare():
        budget = opt.Budget(tmp_path/'prepare.json', 25, 10)
        with opt.computation(budget):
            preparation_started.set(); assert release.wait(2)
        budget.close()
    def measure():
        budget = opt.Budget(tmp_path/'measure.json', 25, 10)
        with opt.computation(budget, exclusive=True): timing_started.set()
        budget.close(); return budget.data
    with ThreadPoolExecutor(max_workers=2) as pool:
        prep = pool.submit(prepare); assert preparation_started.wait(2)
        measured = pool.submit(measure)
        assert not timing_started.wait(.04)
        release.set(); prep.result(); value = measured.result()
    assert timing_started.is_set() and value['resource_wait_seconds'] >= .04
    assert value['charged_seconds'] >= value['resource_wait_seconds']



def test_final_seal_binds_exact_parent_evidence(controller, tmp_path):
    c = controller; result = c['run']([rust('accepted'), {'action': 'finish'}], mode='rust-only')
    path = Path(result['attempts'][0]['path'])/'transaction.json'
    value = read(path); value['before']['files']['src/lib.rs'] = 'pub fn f() { other_parent(); }'; save(path, value)
    with pytest.raises(Failure) as exc:
        scope.finalize_admissions(c['original'], result['baseline'], result['attempts'], tmp_path/'tampered-parent')
    assert exc.value.code == 'optimization_admission_changed'


@pytest.mark.parametrize('decision', ['within_scope', 'requires_source_change'])
def test_full_source_skip_uses_identical_rust_gate_to_rust_only(controller, tmp_path, decision):
    c = controller
    c['review_decisions'].append(decision)
    full = c['run']([{'action': 'finish', 'source_assessment': 'No useful source transform'},
                     rust('same candidate'), {'action': 'finish'}])
    full_payload = deepcopy(c['reviews'][-1]); full_request = deepcopy(c['requests'][1])
    # Use an isolated search directory with the same frozen A0 and proposal.
    c['review_decisions'].append(decision)
    c['requests'].clear(); c['reviews'].clear()
    direct = c['run']([rust('same candidate'), {'action': 'finish'}], mode='rust-only', destination='direct')
    direct_payload = deepcopy(c['reviews'][-1])
    for payload in [full_payload, direct_payload]: payload['candidates'][0].pop('candidate_id')
    assert full_payload == direct_payload
    assert full_request['mode'] == c['requests'][0]['mode'] == 'rust-only'
    assert full_request['allowed_actions'] == c['requests'][0]['allowed_actions'] == ['rust', 'inspect', 'finish']
    assert full_request['stage_contract'] == c['requests'][0]['stage_contract']
    expected = 'accepted' if decision == 'within_scope' else 'optimization_scope_rejected'
    assert full['attempts'][1]['status'] == direct['attempts'][0]['status'] == expected



def test_source_scope_rejection_then_skip_restores_a0_and_enters_common_rust_gate(controller):
    c = controller; c['review_decisions'].extend(['requires_source_change', 'within_scope'])
    result = c['run']([source(), rust('failed source realization'),
                       {'action': 'finish', 'source_assessment': 'No further source opportunity'},
                       rust('A0 realization'), {'action': 'finish'}])
    assert c['requests'][3]['stage'] == 'rust' and c['requests'][3]['mode'] == 'rust-only'
    assert c['requests'][3]['files'] == c['original']['files']
    assert c['requests'][3]['source_program']['entries'] == ['constant:Base.f']
    assert c['events'].count('compare') == 1
    assert not result['source_stage']['accepted']
    assert result['attempts'][1]['status'] == 'optimization_scope_rejected'
    assert result['attempts'][3]['status'] == 'accepted'



def test_source_restore_verifies_trusted_type_sidecar_and_refuses_tampering(controller, tmp_path):
    from i2r_agent import source_optimization
    from i2r_agent.task_context import fingerprint
    c = controller
    result = c['run']([source(), rust('source realization'), {'action': 'finish'}])
    proof = result['attempts'][0]['proof']; record = result['attempts'][1]
    typ = {'kind': 'type', 'name': 'Nat.nat', 'args': []}
    evidence = {'authority': 'Sign.the_const_constraint',
                'original': {'constant:Base.f': typ}, 'revised': {'constant:Optimized.f': typ}}
    proof.update(export_type_authority='Sign.the_const_constraint in imported original theory context',
                 export_type_evidence_sha256=fingerprint(evidence),
                 export_type_preservation=source_optimization.checked_export_types(evidence, proof['original_to_optimized']))
    save(Path(proof['directory'])/'export-types.json', evidence)
    restored = scope.restore(c['original'], result['baseline'], record, proof)
    assert restored['bundle']['source_equivalence']['export_type_evidence_sha256'] == fingerprint(evidence)
    evidence['revised']['constant:Optimized.f'] = {'kind': 'type', 'name': 'Int.int', 'args': []}
    save(Path(proof['directory'])/'export-types.json', evidence)
    with pytest.raises(Failure) as exc: scope.restore(c['original'], result['baseline'], record, proof)
    assert exc.value.code == 'source_type_evidence_changed'


def test_source_triage_has_its_own_policy_and_translation_returns_to_rust_policy(controller, monkeypatch):
    from i2r_agent import optimization_source_policy
    systems = []; original_call = opt.Budget.call
    def call(self, provider, payload, system=None, phase='performance_optimization'):
        if phase == 'performance_optimization': systems.append(system)
        return original_call(self, provider, payload, system=system, phase=phase)
    monkeypatch.setattr(opt.Budget, 'call', call)
    result = controller['run']([source(), rust('realization'), {'action':'finish','reason':'Done'}])
    assert systems == [optimization_source_policy.SYSTEM, opt.SYSTEM, opt.SYSTEM]
    assert result['selected_source_optimized']
    systems.clear()
    direct = controller['run']([rust('direct'), {'action':'finish','reason':'Done'}], mode='rust-only', destination='direct')
    assert systems == [opt.SYSTEM, opt.SYSTEM] and not direct['selected_source_optimized']
