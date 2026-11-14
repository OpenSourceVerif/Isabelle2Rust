"""Acceptance branches, proof goals, frozen APIs and charged search limits."""
import argparse
from copy import deepcopy
from pathlib import Path
import pytest
from i2r_agent.common import Failure, read
from i2r_agent import experiment_config, source_optimization
from i2r_agent.optimization import Budget, ensure_interfaces, mutable_fork, selection_workloads


def test_performance_fork_reuses_nested_session_glue_without_global_mutation(tmp_path, monkeypatch):
    from i2r_agent import optimization as opt
    case = tmp_path / 'case'
    target = case / 'attempts/001/source/extraction/isabelle'
    theory = target / 'source/nested/Base.thy'
    theory.parent.mkdir(parents=True)
    contents = 'theory Base imports Main begin\ndefinition answer where "answer = (1::nat)"\nexport_code answer in Rust\nend\n'
    theory.write_text(contents)
    root = target / 'ROOT'
    root.write_text('session Example = HOL +\n theories Export\n')
    outside = tmp_path / 'unrelated'
    outside.mkdir(); (outside / 'ROOT').write_text('session Other = HOL +\n theories Export\n')
    (outside / 'nested').mkdir(); (outside / 'nested/Other.thy').write_text(contents)
    seen = []
    def execute(self, argv, **kwargs):
        seen.append(list(argv))
        assert 'directories "source/nested"' in root.read_text()
        return {'status': 'passed'}
    monkeypatch.setattr(opt.BudgetExecutor, 'run', execute)
    budget = opt.Budget(case / 'budget.json', 2, 60)
    executor = opt.make_executor(case / 'commands', budget)
    executor.run(['isabelle', 'build', '-d', str(target), '-d', str(outside), 'Example'])
    assert opt.BudgetExecutor.run is execute
    assert opt.Executor.run is not execute
    assert len(seen) == 1
    assert 'definition answer where "answer = (1::nat)"' in theory.read_text()
    assert 'export_code' not in theory.read_text()
    assert len(theory.read_text()) == len(contents)
    assert 'directories' not in (outside / 'ROOT').read_text()
    assert (outside / 'nested/Other.thy').read_text() == contents
    assert executor.cleanup_descendants is True
    budget.close()


def test_limits_are_independent_of_numeric_selection_and_frozen(tmp_path):
    parser = argparse.ArgumentParser(); experiment_config.arguments(parser)
    value = experiment_config.initialize(tmp_path, parser.parse_args(['--full', '--paired-numerics']))
    assert value['optimization_limits'] == {'max_model_calls': 25, 'max_seconds': 3600}
    assert experiment_config.initialize(tmp_path, parser.parse_args([])) == value
    with pytest.raises(Failure):
        experiment_config.initialize(tmp_path, parser.parse_args(['--optimization-calls', '26']))
    with pytest.raises(Failure):
        experiment_config.initialize(tmp_path / 'other', parser.parse_args(['--optimization-seconds', '0']))


def test_failed_requests_are_charged_and_incumbent_survives(tmp_path):
    class Provider:
        calls = 0
        cfg = {'budgets': {}}
        def call(self, *args, **kwargs):
            self.calls += 1
            raise Failure('provider_error', 'connection failed')
    provider = Provider(); budget = Budget(tmp_path / 'budget.json', 2, 3600)
    for _ in range(2):
        with pytest.raises(Failure, match='connection failed'):
            budget.call(provider, {})
    with pytest.raises(Failure) as error:
        budget.call(provider, {})
    assert error.value.code == 'optimization_calls_exhausted'
    assert read(tmp_path / 'budget.json')['calls'] == 2
    budget.close()
    resumed = Budget(tmp_path / 'budget.json', 2, 3600)
    assert resumed.data['calls'] == 2


def test_optimization_branch_does_not_unlock_original():
    original = {'source_candidate_lock': {'version': 'frozen'}, 'phase': 'finish',
                'files': {'src/lib.rs': 'old'}, 'unit': None}
    before = deepcopy(original); fork = mutable_fork(original, {'from': 'baseline'})
    fork['files']['src/lib.rs'] = 'changed'
    assert original == before
    assert 'source_candidate_lock' not in fork
    assert fork['optimization_origin'] == {'from': 'baseline'}


def test_frozen_interfaces_allow_body_changes_but_not_stronger_bounds():
    original = {'files': {'src/lib.rs': 'pub fn f<T>(x:T)->T{x}'}}
    ensure_interfaces(original, {'src/lib.rs': '#[inline] pub fn f<T>(x:T)->T{let y=x; y}\nfn helper() {}'})
    ensure_interfaces(original, {'src/lib.rs': 'pub fn f<T>(mut renamed: T) -> T {renamed}'})
    with pytest.raises(Failure):
        ensure_interfaces(original, {'src/lib.rs': 'pub fn f<T:Clone>(x:T)->T{x.clone()}'})
    with pytest.raises(Failure):
        ensure_interfaces({'files': {'src/lib.rs': 'impl X { pub fn f(&self){} }'}},
                          {'src/lib.rs': 'impl X { pub fn f(&mut self){} }'})


def test_optimization_envelopes_are_unambiguous_and_preserve_source():
    from i2r_agent.optimization_protocol import normalize
    body = {'files': {'src/lib.rs': 'pub fn f(){println!("rust\\n");}'}, 'strategy_version': 'exact'}
    expected = {'action': 'rust', **body}
    assert normalize(expected) == expected
    assert normalize({'rust': body}) == expected
    assert normalize({'rust': {'files': body['files']}, 'strategy_version': 'exact'}) == expected
    for value in [{'rust':body, 'source':{}}, {'rust':body, 'action':'finish'},
                  {'rust':body, 'strategy_version':'different'}, {'files':body['files']}]:
        with pytest.raises(Failure): normalize(value)


def test_structured_source_assessment_is_preserved_without_another_call():
    import json
    from i2r_agent.optimization_protocol import normalize
    from i2r_agent.optimization import source_direction
    assessment = {'hotspot': 'append copying', 'proof_route': ['induction', 'existing equality'],
                  'realization': {'buffer': 'owned storage with preserved order'}}
    proposal = {'action': 'source', 'direction_id': 'accumulator', 'source_assessment': assessment,
                'definitions': 'lemma exact: "x = x" by simp', 'replacements': []}
    result = normalize(proposal)
    assert json.loads(result['source_assessment']) == assessment
    assert proposal['source_assessment'] == assessment
    assert result['definitions'] == proposal['definitions']
    assert source_direction(result, [], 2) == 'accumulator'
    finished = normalize({'action': 'finish', 'source_assessment': assessment})
    assert json.loads(finished['source_assessment']) == assessment
    for empty in [{}, [], {'details': []}, {'details': ' '}]:
        assert normalize({'action': 'finish', 'source_assessment': empty})['source_assessment'] == empty


def test_full_algorithm_changes_require_proof_and_extraction_before_rust():
    from i2r_agent.optimization import check_stage_action
    check_stage_action('full', 'rust', False, 'rust')
    check_stage_action('full', 'source', False, 'source')
    check_stage_action('full', 'source', True, 'rust')
    check_stage_action('full', 'source', True, 'finish')
    for mode, stage, pending, action in [
            ('full','source',False,'rust'), ('full','rust',False,'source'),
            ('rust-only','rust',False,'source')]:
        with pytest.raises(Failure): check_stage_action(mode,stage,pending,action)


def test_full_controller_transitions_and_rejects_a_rust_shortcut(tmp_path, monkeypatch):
    import contextlib
    import json
    from i2r_agent import optimization as opt
    from i2r_agent.common import save
    baseline=tmp_path/'baseline'
    save(baseline/'tasks/example/diagnostics/support-tests/frozen.json', [])
    original={'files':{'src/lib.rs':'pub fn f() {}'},'rust_config':{},'mapping':[], 'partition':{},
              'connector':{},'support_evidence':{'frozen_identity':'frozen'},
              'bundle':{'numeric_policy':{},'sources':{'Base.thy':'source'},
                        'source_model':{'entries':[], 'entities':{}},
                        'original_source_model':{'entries':[]}}}
    cfg={'translation':{},'budgets':{},'testing':{'process_timeout':1}}
    def freeze(run,row,directory,**kwargs):
        save(directory/'frozen.json',{'test':'identity'})
        return deepcopy(original),deepcopy(cfg),{}, {'original_files':{}}
    monkeypatch.setattr(opt.numeric_experiment,'freeze',freeze)
    monkeypatch.setattr(opt,'version',lambda s:s['files']['src/lib.rs'])
    monkeypatch.setattr(opt.source_optimization,'source_context',lambda s:{})
    monkeypatch.setattr(opt.optimization_contracts,'context',lambda s:{})
    monkeypatch.setattr(opt,'computation',lambda b,**kw:contextlib.nullcontext())
    monkeypatch.setattr(opt,'profile',lambda *a,**k:{'status':'test-profile'})
    def materialize(path,files,rc):
        path=Path(path);path.mkdir(parents=True,exist_ok=True)
        for n,v in files.items():
            f=path/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(v)
        return path
    def connection(path,*args):
        path=path/'harness';path.mkdir(parents=True,exist_ok=True);return path
    monkeypatch.setattr(opt,'materialize',materialize)
    monkeypatch.setattr(opt,'connection',connection)
    monkeypatch.setattr(opt,'timing_build',lambda crate,cfg,case,directory,budget:{'source':str(crate),'work':str(directory)})
    requests=[]
    class FakeProvider:
        def __init__(self,cfg,directory):
            self.cfg=cfg;self.calls=0;self.usage={};self.unknown_usage_requests=[]
        def call(self,system,payload,**kwargs):
            self.calls+=1;requests.append(json.loads(payload))
            return [
                {'action':'rust','files':{'src/lib.rs':'unproved shortcut'}},
                {'action':'finish','reason':'No proved source improvement','source_assessment':'No worthwhile proof-backed replacement'},
                {'action':'finish','reason':'Fixed-source stage complete'},
            ][self.calls-1]
    monkeypatch.setattr(opt,'Provider',FakeProvider)
    monkeypatch.setattr(opt,'apply_candidate',lambda *a,**k:pytest.fail('Unproved source-stage Rust must never reach the transaction'))
    result=opt.optimize_case(baseline,{'id':'example'},'full',tmp_path/'search',
                             {'max_model_calls':25,'max_seconds':3600})
    assert [r['mode'] for r in requests]==['full','full','rust-only']
    assert [r['stage'] for r in requests]==['source','source','rust']
    assert requests[2]['original_source_files']=={}
    assert requests[1]['original_source_files']==original['bundle']['sources']
    assert requests[1]['feedback']['status']=='source_proof_required'
    assert [r['status'] for r in result['attempts']]==['source_proof_required','source_stage_complete','finished']
    assert result['completed_stage']=='rust' and result['model_calls']==3
    assert result['selected_version']==original['files']['src/lib.rs']


def test_source_goals_are_controller_owned_and_every_export_is_proved():
    bundle = {'original_source_model': {'entries': ['constant:Base.f', 'constant:Base.g']},
              'sources': {'Export.thy': 'theory Export imports Base "I2R_Agent.Agent_Export" begin\nend'}}
    proposal = {'definitions': '', 'replacements': [
        {'source': 'constant:Base.f', 'rhs': 'Base.f', 'proof': 'by (simp add: i2r_entry_0_def)'},
        {'source': 'constant:Base.g', 'rhs': 'Base.g', 'proof': 'by (simp add: i2r_entry_1_def)'}]}
    theory, export, roots = source_optimization.render(bundle, proposal)
    assert 'i2r_entry_0 = Base.f' in theory and 'i2r_entry_1 = Base.g' in theory
    assert 'Thm_Deps.all_oracles' in theory
    assert list(roots.values()) == ['constant:Optimization.i2r_entry_0', 'constant:Optimization.i2r_entry_1']
    assert 'export_code Optimization.i2r_entry_0 Optimization.i2r_entry_1' in export
    with pytest.raises(Failure):
        source_optimization.render(bundle, {**proposal, 'replacements': proposal['replacements'][:1]})
    # Source text is lexed by Isabelle, not searched with a comment-blind regex.
    comment = '(* the original theory (* nested *) *)'
    assert source_optimization.check_fragment(comment) == comment
    with pytest.raises(Failure): source_optimization.check_fragment(None)
    guard = source_optimization.source_guard(proposal)
    assert 'Token.explode' in guard and 'Token.is_command' in guard
    assert 'Code.equations_of_cert' in theory


def test_source_type_schemes_preserve_polymorphism_sorts_and_sharing():
    from i2r_agent.source_optimization import type_scheme, preserve_export_types
    def var(name, sort=['HOL.type']): return {'kind':'schematic','name':name,'index':0,'sort':sort}
    def fn(a,b): return {'kind':'type','name':'fun','args':[a,b]}
    a,b=var('a'),var('b')
    typ=fn(a,a)
    assert type_scheme(typ)==type_scheme(fn(b,b))
    for other in [fn(a,b),fn(var('a',['Groups.plus']),var('a',['Groups.plus'])),
                  fn({'kind':'type','name':'Nat.nat','args':[]},{'kind':'type','name':'Nat.nat','args':[]})]:
        with pytest.raises(Failure, match='type scheme'):
            preserve_export_types({'entities':{'old':{'source_type':typ}}},
                                  {'entities':{'new':{'source_type':other}}},{'old':'new'})


def test_scope_review_requires_complete_explicit_decisions():
    from i2r_agent.optimization_scope import validate_reply
    row={'candidate_id':'001','decision':'within_scope','reason':'Same recurrence and visitation order'}
    assert validate_reply({'reviews':[row]},['001'])['001']==row
    for reply in [{'reviews':[]},{'reviews':[row,row]},
                  {'reviews':[{**row,'decision':'probably'}]},
                  {'reviews':[{**row,'reason':''}]}]:
        with pytest.raises(Failure): validate_reply(reply,['001'])


def test_scope_review_declares_json_and_carries_unchanged_baseline_interfaces():
    from i2r_agent.optimization_scope import SYSTEM, review_payload
    from i2r_agent.optimization_protocol import interfaces
    original={'files':{'src/lib.rs':'pub fn helper<T: Ord>(x:T)->T { x }'},
              'mapping':[], 'partition':{}, 'rust_config':{}, 'connector':{},
              'bundle':{'numeric_policy':{}, 'source_model':{'entries':[], 'entities':{}}}}
    assert 'json' in SYSTEM.lower()
    request=review_payload(original,[])
    assert request['frozen_interfaces']==interfaces(original['files'])
    assert 'timings' not in request and 'measured_evidence' not in request


def test_private_free_helper_can_change_ownership_and_name_without_changing_public_api():
    original = {'files': {'src/lib.rs': '''
pub fn consume(xs: Vec<u8>) -> Vec<u8> { helper(&xs) }
fn helper(xs: &[u8]) -> Vec<u8> { xs.to_vec() }
''', 'src/nested.rs': 'fn helper(x: &u8) -> u8 { *x }'}}
    candidate = {'src/lib.rs': '''
pub fn consume(xs: Vec<u8>) -> Vec<u8> { take(xs) }
fn take(xs: Vec<u8>) -> Vec<u8> { xs }
''', 'src/nested.rs': 'fn helper(x: u8) -> u8 { x }'}
    ensure_interfaces(original, candidate)
    from i2r_agent.optimization_protocol import interfaces
    assert set(interfaces(original['files'])) == {'crate::consume'}
    assert set(interfaces(candidate)) == {'crate::consume'}


@pytest.mark.parametrize('before,after', [
    ('pub(crate) fn helper(x: &u8) -> u8 { *x }', 'pub(crate) fn helper(x: u8) -> u8 { x }'),
    ('pub trait T { fn f(&self); }', 'pub trait T { fn f(self); }'),
    ('struct S; impl S { fn f(&self) {} }', 'struct S; impl S { fn f(self) {} }'),
    ('#[no_mangle] fn f(x:u8) {}', '#[no_mangle] fn f(x:u16) {}'),
    ('#[unsafe(export_name="api")] fn f(x:u8) {}', '#[unsafe(export_name="api")] fn f(x:u16) {}'),
])
def test_private_free_helper_exception_does_not_relax_visible_or_member_interfaces(before, after):
    with pytest.raises(Failure) as error:
        ensure_interfaces({'files': {'src/lib.rs': before}}, {'src/lib.rs': after})
    assert error.value.code == 'optimization_interface_changed'


def test_search_reserves_calls_for_final_acceptance(tmp_path):
    class Provider:
        calls=0
        cfg={'budgets':{}}
        def call(self,*args,**kwargs): self.calls+=1;return {}
    provider=Provider();budget=Budget(tmp_path/'budget.json',3,60,reserved_calls=2)
    budget.call(provider,{})
    with pytest.raises(Failure): budget.call(provider,{})
    budget.close()
    assert read(tmp_path/'budget.json')['calls']==1


def test_search_workload_selection_is_declared_without_timings():
    row = {'primary_workload': 'large', 'performance_workloads': [
        {'id': 'small', 'input': [1]}, {'id': 'middle', 'input': [3]},
        {'id': 'large', 'input': [9]}, {'id': 'other', 'input': [4]}]}
    assert [w['id'] for w in selection_workloads(row)] == ['small', 'large']


def test_parallel_searches_allow_two_preparations_and_charge_queue_time(tmp_path, monkeypatch):
    import time
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from i2r_agent.optimization import computation
    monkeypatch.setattr('i2r_agent.optimization.ROOT', tmp_path)
    active = []; observed = []; ready = threading.Barrier(3)
    def work(i):
        budget = Budget(tmp_path / str(i) / 'budget.json', 25, 10)
        ready.wait()
        with computation(budget):
            active.append(i); observed.append(len(active)); time.sleep(.02); active.remove(i)
        budget.close()
        return budget.data['charged_seconds']
    with ThreadPoolExecutor(max_workers=3) as pool:
        elapsed = list(pool.map(work, range(3)))
    assert max(observed) == 2
    assert max(elapsed) >= .04
