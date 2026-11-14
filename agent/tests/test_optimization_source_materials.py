from copy import deepcopy
import argparse
import pytest
from i2r_agent import optimization_materials as material, optimization_source_text as text
from i2r_agent import experiment_config as config, optimization as opt
from i2r_agent.common import Failure, digest
from i2r_agent.task_context import Archive


def test_frozen_theory_read_does_not_follow_edited_external_file(tmp_path):
    path = tmp_path/'Example.thy'; path.write_text('lemma known: "P"\n  by simp\n')
    archive = Archive(tmp_path/'archive'); version = archive.put('source', path.read_text())
    bundle = {'_context_archive': str(archive.directory), 'sources': {},
              'source_versions': {str(path): version},
              'source_catalog': [{'path': str(path), 'theory': 'Example', 'available': True, 'sha256': digest(path)}]}
    path.write_text('changed disk contents')
    reply = {'request_sources': [{'path': str(path), 'start_line': 1, 'end_line': 1}]}
    result = material.read_sources(reply, bundle)
    assert result['sources'][0]['text'] == 'lemma known: "P"'
    assert result['sources'][0]['version'] == version
    assert material.merge(result, result) == result
    reply['request_sources'][0]['source_version'] = 'source-wrong'
    with pytest.raises(Failure, match='frozen source version'): material.read_sources(reply, bundle)


def test_unarchived_new_source_reads_are_hash_checked_and_catalog_scoped(tmp_path):
    path = tmp_path/'Example.thy'; path.write_text('known source')
    bundle = {'source_catalog': [{'path': str(path), 'available': True, 'sha256': digest(path)}]}
    request = {'request_sources': [{'path': str(path)}]}
    assert material.read_sources(request, bundle)['sources'][0]['text'] == 'known source'
    path.write_text('mutated source')
    with pytest.raises(Failure, match='catalog'): material.read_sources(request, bundle)
    with pytest.raises(Failure, match='catalog'): material.read_sources({'request_sources': [{'path': '/not/in/catalog'}]}, bundle)


def test_unicode_transport_preserves_original_and_encodes_guard_and_proof_fragments():
    symbols = text.encoding([r'\<Rightarrow> code: 0x0021d2'+'\n'+r'\<lambda> code: 0x0003bb'])
    original = {'action': 'source', 'definitions': 'fun f :: "nat ⇒ nat"',
                'replacements': [{'source': 'constant:E.f', 'rhs': 'λx. x', 'proof': 'by simp'}]}
    before = deepcopy(original); encoded, changes = text.encode_proposal(original, symbols)
    assert original == before
    assert encoded['definitions'] == r'fun f :: "nat \<Rightarrow> nat"'
    assert encoded['replacements'][0]['rhs'] == r'\<lambda>x. x'
    assert encoded['replacements'][0]['proof'] == 'by simp'
    assert len(changes) == 2
    assert text.encode_proposal(encoded, symbols) == (encoded, [])


def test_configurable_source_share_is_frozen_with_full_and_cannot_affect_off(tmp_path):
    parser = argparse.ArgumentParser(); config.arguments(parser)
    args = parser.parse_args(['--full','--source-calls','18','--source-seconds','2400',
                              '--rust-reserve-calls','5','--rust-reserve-seconds','600'])
    selection = config.initialize(tmp_path/'full', args)
    limits = selection['optimization_limits']
    assert (limits['max_model_calls'], limits['max_seconds']) == (25, 3600)
    budget = opt.Budget(tmp_path/'budget.json', 25, 3600, source_limits=limits['source_limits'])
    budget.begin_source()
    assert budget.data['source_phase']['calls'] == 18
    assert budget.data['source_phase']['reserve_calls'] == 5
    assert 2390 < budget.remaining() <= 2400
    budget.begin_rust()
    assert budget.remaining() > 3500
    budget.close()
    with pytest.raises(Failure, match='frozen'): config.initialize(tmp_path/'full', parser.parse_args(['--source-calls','19']))
    with pytest.raises(Failure, match='require --full'): config.initialize(tmp_path/'off', parser.parse_args(['--off','--source-calls','18']))
    with pytest.raises(Failure, match='fit the total'): config.initialize(tmp_path/'invalid', parser.parse_args(['--full','--source-calls','24']))
    assert config.initialize(tmp_path/'legacy', parser.parse_args(['--off'])) is None
    assert not (tmp_path/'legacy/experiment.json').exists()
