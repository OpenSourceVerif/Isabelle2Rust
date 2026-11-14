"""Source proof type gate: authoritative constraints, not execution sorts."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from i2r_agent.common import Failure
from i2r_agent.source_optimization import checked_export_types, preserve_export_types, render

ROOTS = {'constant:MergeSort_Test.linorder_class.msort': 'constant:Optimization.i2r_entry_0'}

def fixture():
    return json.loads((Path(__file__).parent / 'fixtures' / 'msort005-type-fixture.json').read_text())

def evidence():
    return json.loads((Path(__file__).parent / 'fixtures' / 'msort005-trusted-export-types.json').read_text())

def test_recorded_msort_raw_types_explain_false_rejection():
    data = fixture()
    assert all(data['original'][k] == data['revised'][k] for k in
               ('execution_type', 'type_variables', 'execution_sorts', 'class_dependencies'))
    with pytest.raises(Failure, match='type scheme'):
        preserve_export_types({'entities': {next(iter(ROOTS)): data['original']}},
                              {'entities': {next(iter(ROOTS.values())): data['revised']}}, ROOTS)
    assert checked_export_types(evidence(), ROOTS)

@pytest.mark.parametrize('change', ['sort', 'concrete', 'structure', 'sharing'])
def test_real_constraint_or_structure_change_rejected(change):
    data = evidence(); typ = next(iter(data['revised'].values()))
    if change == 'sort':
        for a in typ['args']: a['args'][0]['sort'].append('Groups.plus')
    elif change == 'concrete':
        for a in typ['args']: a['args'][0] = {'kind': 'type', 'name': 'Nat.nat', 'args': []}
    elif change == 'structure': typ['args'][1]['name'] = 'Option.option'
    else: typ['args'][1]['args'][0]['name'] = "'b"
    with pytest.raises(Failure, match='type scheme'): checked_export_types(data, ROOTS)

@pytest.mark.parametrize('missing', ['authority', 'original', 'revised', 'sort', 'index'])
def test_missing_trusted_metadata_fails_closed(missing):
    data = evidence()
    if missing in ('sort', 'index'):
        del next(iter(data['original'].values()))['args'][0]['args'][0][missing]
    else: del data[missing]
    with pytest.raises(Failure): checked_export_types(data, ROOTS)

def test_render_emits_trusted_constraint_audit_and_unconditional_goal(tmp_path):
    old, new = next(iter(ROOTS.items()))
    bundle = {'original_source_model': {'entries': [old]},
              'sources': {'Export.thy': 'theory Export imports MergeSort_Test "I2R_Agent.Agent_Export" begin end'}}
    proposal = {'definitions': '', 'replacements': [{'source': old, 'rhs': old.split(':',1)[1], 'proof': 'by simp'}]}
    text, _, roots = render(bundle, proposal, tmp_path/'export-types.json')
    assert roots == ROOTS
    assert 'lemma i2r_equiv_0: "i2r_entry_0 = MergeSort_Test.linorder_class.msort"' in text
    assert text.count('Sign.the_const_constraint @{theory}') == 2
    assert 'Code_Preproc.sortargs' not in text
    assert text.index('val _ = File.write') > text.index('Thm_Deps.all_oracles')


def test_restore_sidecar_hash_and_legacy_behavior(tmp_path):
    from i2r_agent.common import save
    from i2r_agent.task_context import fingerprint
    from i2r_agent.source_optimization import verify_export_type_evidence
    assert verify_export_type_evidence({}, ROOTS) is False
    data = evidence(); save(tmp_path / 'export-types.json', data)
    proof = {'directory': str(tmp_path),
             'export_type_authority': 'Sign.the_const_constraint in imported original theory context',
             'export_type_evidence_sha256': fingerprint(data),
             'export_type_preservation': checked_export_types(data, ROOTS)}
    assert verify_export_type_evidence(proof, ROOTS)
    proof['export_type_evidence_sha256'] = 'changed'
    with pytest.raises(Failure): verify_export_type_evidence(proof, ROOTS)
    proof['export_type_evidence_sha256'] = fingerprint(data)
    (tmp_path / 'export-types.json').unlink()
    with pytest.raises(Failure): verify_export_type_evidence(proof, ROOTS)
