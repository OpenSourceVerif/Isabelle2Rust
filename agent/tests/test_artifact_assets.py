"""Exercise the delivered entry boundary and sealed runtime reference assets."""
from pathlib import Path
from unittest.mock import Mock
import pytest
from i2r_agent import fpp_runner, knowledge_run, task_context, knowledge, repair_knowledge
from i2r_agent.common import Failure


def test_reference_catalog_is_readable_and_bound_to_release():
    identity = fpp_runner.identity()['files']
    rows = task_context.reference_catalog()
    contents = knowledge.references([row['path'] for row in rows])
    assert contents
    for name, content in contents.items():
        assert content.strip()
        assert 'agent/references/' + name in identity
    assert set(repair_knowledge.manifest()) <= {
        name.removeprefix('agent/') for name in identity
    }


@pytest.mark.parametrize('workflow', [None, 'unsupported-workflow', 'legacy-analysis', 'legacy-generation'])
def test_obsolete_workflow_is_rejected_before_provider_or_output(tmp_path, monkeypatch, workflow):
    provider = Mock(side_effect=AssertionError('Provider must not be constructed'))
    monkeypatch.setattr(knowledge_run, 'Provider', provider)
    output = tmp_path / 'output'
    with pytest.raises(Failure) as caught:
        knowledge_run.build(tmp_path, output, {'generation': {'workflow': workflow}})
    assert caught.value.code == 'unknown_workflow'
    provider.assert_not_called()
    assert not output.exists()
