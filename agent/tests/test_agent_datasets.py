"""Dataset isolation and input integrity for the shared experiment runner."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from i2r_agent import dataset_artifact as art
from i2r_agent.common import digest


def test_unit_inputs_are_complete_and_hash_locked(monkeypatch):
    monkeypatch.setenv('I2R_DATASET', 'unit')
    data = art.manifest()
    assert len(data['cases']) == 488
    assert len({row['root'] for row in data['cases']}) == 482
    assert len({row['original_source'] for row in data['cases']}) == 54
    assert len({row['id'] for row in data['cases']}) == 488
    for row in data['cases']:
        for name, expected in row['files'].items():
            assert digest(art.ARTIFACT / row['project'] / name) == expected


def test_fpp_projects_reconstruct_from_dataset_directory(monkeypatch, tmp_path):
    monkeypatch.setenv('I2R_DATASET', 'fpp')
    data = art.manifest()
    for row in data['cases']:
        assert row['project'].startswith('datasets/fpp/projects/')
        project = art.project(row, tmp_path)
        for name, expected in row['files'].items():
            assert digest(project / name) == expected
        for name, source in row['source_mounts'].items():
            assert digest(project / name) == source['derived_sha256']


def test_datasets_share_effective_config(monkeypatch, tmp_path):
    configs = []
    for dataset in ['fpp', 'unit']:
        monkeypatch.setenv('I2R_DATASET', dataset)
        for row in art.manifest()['cases']:
            configs.append(art.configuration(row, tmp_path))
    assert all(c == configs[0] for c in configs)


@pytest.mark.parametrize('dataset,count', [('fpp', 313), ('unit', 488)])
def test_launchers_select_dataset_and_reject_cross_dataset_run(tmp_path, dataset, count):
    run = tmp_path / dataset
    env = {**os.environ, 'I2R_DATASET': 'unit', 'PYTHONPATH': str(art.ROOT / 'src')}
    command = [str(art.ARTIFACT / ('run-' + dataset)), '--run', str(run), 'report']
    done = subprocess.run(command, env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)['selected_roots'] == count
    before = (run / 'report.json').read_bytes()
    other = 'unit' if dataset == 'fpp' else 'fpp'
    command[0] = str(art.ARTIFACT / ('run-' + other))
    rejected = subprocess.run(command, env=env, capture_output=True, text=True)
    assert rejected.returncode != 0
    assert 'dataset_selection_mismatch' in rejected.stderr
    assert (run / 'report.json').read_bytes() == before


def test_child_cli_inherits_unit_selection(tmp_path):
    env = {**os.environ, 'I2R_DATASET': 'unit', 'PYTHONPATH': str(art.ROOT / 'src')}
    done = subprocess.run([sys.executable, '-m', 'i2r_agent.experiment_runner', '--run',
                           str(tmp_path / 'child'), 'report'], env=env,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)['selected_roots'] == 488


@pytest.mark.parametrize('dataset', ['unit', 'fpp', 'performance'])
@pytest.mark.parametrize('wrong_root', [False, True])
def test_admission_uses_canonical_roots_and_rejects_changed_exports(monkeypatch, tmp_path, dataset, wrong_root):
    from i2r_agent import source_input
    from i2r_agent.common import Failure
    monkeypatch.setenv('I2R_DATASET', dataset)
    rows = art.manifest()['cases']
    row = (next(r for r in rows if len(r.get('roots', [])) > 1)
           if dataset == 'performance' else rows[0])
    expected = row['roots'] if dataset == 'performance' else [row['root']]
    bundle = {'source_model': {'entries': ['constant:Wrong.export'] if wrong_root else expected,
                               'entities': {name: {} for name in row['closure']}}}
    monkeypatch.setattr(art, 'configuration', lambda *args: {})
    monkeypatch.setattr(art, 'project', lambda *args: tmp_path / 'project')
    calls = []

    class WrapperReached(Exception):
        pass

    def extract(*args):
        calls.append(args[0])
        if len(calls) == 1:
            return bundle
        raise WrapperReached()

    monkeypatch.setattr(source_input, 'preprocess', extract)
    if wrong_root:
        with pytest.raises(Failure) as error:
            art.prepare(row, tmp_path)
        assert error.value.code == 'root_changed'
        assert len(calls) == 1
    else:
        with pytest.raises(WrapperReached):
            art.prepare(row, tmp_path)
        assert len(calls) == 2
