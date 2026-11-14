"""Current source + explicit boundary + verified runtime jointly grant lowering."""
from copy import deepcopy
from pathlib import Path

import pytest

from i2r_agent import numeric_interface, optimization_contracts, optimization_primitives as primitives
from i2r_agent.common import Failure, read
from i2r_agent.default_adaptations import operational_identity


@pytest.fixture
def state():
    rows = read(Path(__file__).parent / 'fixtures/performance-primitive-identities.json')['primitives']
    entities = {sid: deepcopy(row['entity']) for sid, row in rows.items()}
    root = 'constant:Example.root'
    entities[root] = {'id': root, 'kind': 'constant', 'dependencies': list(entities)}
    runtime = numeric_interface.contract()
    return {'bundle': {'source_model': {'entries': [root], 'entities': entities},
                      'numeric_policy': {'mode': 'arbitrary', 'numeric_interface': runtime}},
            'rust_config': {'numeric_interface': {k: v for k, v in runtime.items() if k != 'guidance'}},
            'partition': {'boundaries': []}}


def select(state, sid):
    proposal = next(r for r in primitives.context(state)['available_adapters'] if r['source'] == sid)
    state['partition']['boundaries'].append(deepcopy(proposal))


def test_all_exact_typed_operations_available_but_none_silently_enabled(state):
    before = deepcopy(state); material = primitives.context(state)
    assert not material['contracts'] and state == before
    assert len(material['available_adapters']) == len(primitives.SPECS)
    for name, sha, *_ in primitives.SPECS:
        sid = 'constant:' + name
        assert operational_identity(state['bundle']['source_model']['entities'][sid]) == sha
        select(state, sid)
    assert len(primitives.context(state)['contracts']) == len(primitives.SPECS)


@pytest.mark.parametrize('field,value', [('source_type', primitives.NAT),
    ('execution_equations', []), ('dependencies', ['constant:Untrusted.change'])])
def test_type_equation_and_dependency_drift_revoke_available_and_active(state, field, value):
    sid = 'constant:Nat.times_nat_inst.times_nat'; select(state, sid)
    state['bundle']['source_model']['entities'][sid][field] = value
    material = primitives.context(state)
    assert sid not in {r['source'] for r in material['available_adapters'] + material['contracts']}


def test_source_reextraction_recomputes_catalog_without_granting_business_replacement(state):
    sid = 'constant:Nat.times_nat_inst.times_nat'; root = 'constant:Example.root'
    old = deepcopy(state); old['bundle']['source_model']['entities'][root]['dependencies'] = []
    assert not primitives.context(old)['available_adapters']
    assert sid in {r['source'] for r in primitives.context(state)['available_adapters']}
    # Calling a library operation as the exported business root makes it mandatory.
    state['bundle']['source_model']['entries'] = [sid]
    assert sid not in {r['source'] for r in primitives.context(state)['available_adapters']}
    assert old['bundle']['source_model']['entities'][root]['dependencies'] == []


@pytest.mark.parametrize('kind,count', [('native', 1), ('inlined', 1), ('trait', 0), ('native', 2)])
def test_only_one_explicit_native_or_inline_declaration_activates(state, kind, count):
    sid = 'constant:Nat.times_nat_inst.times_nat'
    state['partition']['boundaries'] = [{'source': sid, 'kind': kind}] * count
    active = primitives.context(state)['contracts']
    assert bool(active) == (kind in {'native', 'inlined'} and count == 1)


@pytest.mark.parametrize('target', ['rust_config', 'numeric_policy'])
def test_runtime_hash_mismatch_blocks_catalog(state, target):
    cfg = state['rust_config'] if target == 'rust_config' else state['bundle']['numeric_policy']
    cfg['numeric_interface']['runtime_sha256'] = 'tampered'
    with pytest.raises(Failure) as error: primitives.context(state)
    assert error.value.code == 'numeric_runtime_changed'


def test_modes_share_contracts_and_nonpaired_does_not_gain_unverified_adapters(state):
    select(state, 'constant:Nat.times_nat_inst.times_nat')
    left = deepcopy(state); right = deepcopy(state)
    left['optimization_mode'] = 'rust-only'; right['optimization_mode'] = 'full'
    assert primitives.context(left) == primitives.context(right)
    assert optimization_contracts.context(state)['registered_native_contracts'] == primitives.context(state)
    state['bundle']['numeric_policy'] = {'mode': 'arbitrary'}
    state['rust_config'] = {}
    assert not primitives.context(state)['contracts']
    assert 'available_adapters' not in primitives.context(state)
