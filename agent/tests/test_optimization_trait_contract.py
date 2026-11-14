"""Performance-only trait extension checks; no model, prover or compiler calls."""
from copy import deepcopy
from pathlib import Path

import pytest

from i2r_agent import optimization as opt, optimization_protocol as protocol
from i2r_agent.common import Failure


def files(text):
    return {'src/lib.rs': text}


BASE = 'pub trait Numeric { fn plus(&self, rhs: &Self) -> Self; }'


@pytest.mark.parametrize('member', [
    'fn extra(&self) -> Self;',
    'fn plus_owned(self, rhs: Self) -> Self { self.plus(&rhs) }',
    '#[doc(hidden)] #[inline] fn plus_owned(self, rhs: Self) -> Self { self.plus(&rhs) }',
    'type Extra;', 'type Extra = ();', 'const EXTRA: usize;', 'const EXTRA: usize = 1;'])
def test_public_trait_cannot_gain_required_default_or_hidden_members(member):
    candidate = BASE[:-1] + member + '}'
    with pytest.raises(Failure) as exc: protocol.ensure_public_trait_members(files(BASE), files(candidate))
    assert exc.value.code == 'optimization_trait_contract_changed'
    assert exc.value.evidence['added_members']['crate::Numeric']


def test_default_method_body_change_and_private_free_helper_are_allowed():
    original = files('pub trait Numeric { fn value(&self)->u8 { 1+1 } }')
    candidate = files('pub trait Numeric { fn value(&self)->u8 { helper() } } fn helper()->u8 { 2 }')
    protocol.ensure_public_trait_members(original, candidate)
    opt.ensure_interfaces({'files': original}, candidate)


@pytest.mark.parametrize('old,new', [
    ('pub trait T { fn f(&self){} }', 'pub trait T { fn f(&self); }'),
    ('pub trait T { fn f<T>(&self,x:T); }', 'pub trait T { fn f<T:Clone>(&self,x:T); }'),
    ('pub trait T { const N:u8=1; }', 'pub trait T { const N:u8; }')])
def test_existing_default_required_and_signature_obligations_use_original_interface_gate(old, new):
    protocol.ensure_public_trait_members(files(old), files(new))
    with pytest.raises(Failure) as exc: opt.ensure_interfaces({'files': files(old)}, files(new))
    assert exc.value.code == 'optimization_interface_changed'


def test_removing_associated_member_also_changes_frozen_member_set():
    with pytest.raises(Failure) as exc:
        protocol.ensure_public_trait_members(files('pub trait T { type Out; }'), files('pub trait T {}'))
    assert exc.value.evidence['removed_members'] == {'crate::T': [('type', 'Out')]}


@pytest.mark.parametrize('visibility', ['pub', 'pub(crate)', 'pub(super)', 'pub(in crate::inner)'])
def test_restricted_visibility_is_frozen_conservatively(visibility):
    original = files('mod inner { ' + visibility + ' trait T { fn f(); } }')
    candidate = files('mod inner { ' + visibility + ' trait T { fn f(); fn extra(){} } }')
    with pytest.raises(Failure) as exc: protocol.ensure_public_trait_members(original, candidate)
    assert 'crate::inner::T' in exc.value.evidence['added_members']


def test_qualified_trait_identity_distinguishes_same_name_modules_and_files():
    original = {'src/lib.rs': 'mod a { pub trait T { fn f(); } }',
                'src/b.rs': 'pub trait T { fn g(); }'}
    same = deepcopy(original)
    protocol.ensure_public_trait_members(original, same)
    same['src/b.rs'] = 'pub trait T { fn g(); fn new_member(){} }'
    with pytest.raises(Failure) as exc: protocol.ensure_public_trait_members(original, same)
    assert set(exc.value.evidence['added_members']) == {'crate::b::T'}


@pytest.mark.parametrize('candidate', ['pub trait T { fn f( }', 'pub trait T { fn f(); fn f(); }',
                                      'pub trait T { fn f(); } pub trait T { fn f(); }',
                                      'pub trait T { fn f(); injected_members!(); }'])
def test_invalid_ambiguous_or_unresolved_frozen_trait_body_fails_closed(candidate):
    with pytest.raises(Failure) as exc:
        protocol.ensure_public_trait_members(files('pub trait T { fn f(); }'), files(candidate))
    assert exc.value.code in {'optimization_trait_contract_parse_error',
                              'optimization_trait_contract_ambiguous', 'optimization_trait_contract_unresolved'}


def test_new_or_private_traits_are_outside_existing_public_trait_member_inventory():
    original = files(BASE + ' trait Private { private_members!(); }')
    candidate = files(BASE + ' trait Private { different_private_members!(); } pub trait New { new_members!(); }')
    protocol.ensure_public_trait_members(original, candidate)
    assert set(protocol.public_trait_members(original)) == {'crate::Numeric'}


def test_trait_added_in_parent_still_cannot_extend_original_a0_contract():
    parent = files(BASE[:-1] + 'fn extra(&self){} }')
    with pytest.raises(Failure): protocol.ensure_public_trait_members(files(BASE), parent)
    # Comparing only to the parent would miss inherited extension: apply_candidate
    # must always use original A0, not the current incumbent.
    protocol.ensure_public_trait_members(parent, parent)


def test_apply_candidate_rejects_extension_before_other_candidate_checks(tmp_path, monkeypatch):
    original = {'files': files(BASE)}
    parent = {'files': files(BASE[:-1] + 'fn extra(&self){} }')}
    candidate = {'files': files(BASE[:-1] + 'fn extra(&self){} }'), 'rust_config': {}}
    monkeypatch.setattr(opt, 'apply_transaction', lambda *a, **k: candidate)
    monkeypatch.setattr(opt.numeric_interface, 'validate_candidate', lambda *a: pytest.fail('Must fail before numeric/coverage/compile checks'))
    for mode in ['rust-only', 'full']:
        state = {**parent, 'optimization_mode': mode}
        with pytest.raises(Failure) as exc:
            opt.apply_candidate(state, {'files': candidate['files'], 'strategy_updates': [{}]}, original, {}, tmp_path/mode)
        assert exc.value.code == 'optimization_trait_contract_changed'


def test_author_protocol_warns_before_generating_invalid_override_points():
    assert 'Existing A0 public traits' in protocol.EXAMPLES
    assert 'private free helpers' in protocol.EXAMPLES


@pytest.mark.parametrize('extends_trait', [False, True])
def test_legacy_positive_selection_cannot_bypass_trait_guard(tmp_path, extends_trait):
    from i2r_agent import optimization_matrix as matrix
    from i2r_agent.common import save, digest
    from i2r_agent.task_context import fingerprint
    from i2r_agent.translation_workflow import version
    original = {'files': files(BASE), 'mapping': [], 'partition': {}, 'rust_config': {},
                'connector': {}, 'bundle': {'source_model': {'entries': [], 'entities': {}}}}
    state = deepcopy(original)
    state['files'] = files(BASE[:-1] + 'fn extra(&self){} }' if extends_trait else
                           BASE + ' fn private_helper() {}')
    state['optimization_validation'] = {'status': 'passed', 'candidate_version': version(state)}
    directory = tmp_path/'optimization/example'
    statepath = directory/'selected-state.json'; save(statepath, state)
    review = {'reviews': [{'candidate_id': '001', 'decision': 'within_scope'}],
              'identity': {'candidates': [{'id': '001', 'version': version(state),
                  'source': fingerprint(state['bundle']['source_model'])}]}}
    save(directory/'scope-review/review.json', review)
    save(directory/'scope-review/selection.json', {'selected_candidate': '001'})
    result = {'status': 'complete', 'improved': True, 'selected_state': str(statepath),
              'selected_state_sha256': digest(statepath), 'selected_version': version(state),
              'baseline': {'candidate_version': version(original)}, 'output': str(directory/'output'),
              'output_files': {}, 'scope_selection': {'candidate': '001',
                  'review_sha256': digest(directory/'scope-review/review.json'),
                  'selection_sha256': digest(directory/'scope-review/selection.json')}}
    save(directory/'result.json', result)
    seals = {p: digest(p) for p in directory.rglob('*.json')}
    if extends_trait:
        with pytest.raises(Failure) as exc:
            matrix.selected(tmp_path, 'example', original)
        assert exc.value.code == 'optimization_trait_contract_changed'
    else:
        assert matrix.selected(tmp_path, 'example', original)[0] == state
    assert {p: digest(p) for p in seals} == seals
