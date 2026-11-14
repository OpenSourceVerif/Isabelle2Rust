"""Run compilation/review fixtures up to the real source-acceptance boundary.

These fixtures deliberately have no source-test author or differential project.
The checkpoint remains active: reaching this boundary is not full acceptance.
"""
from pathlib import Path
from unittest.mock import patch
from i2r_agent import translation_workflow as runner
from i2r_agent.common import read


def compile_until_source(*args, **kwargs):
    class SourceBoundary(Exception):
        pass

    transition = runner.go_after_support

    def stop(state, project):
        transition(state, project)
        assert state['phase'] == 'support'
        assert set(state['completed']) == set(state['partition']['units'])
        raise SourceBoundary()

    with patch.object(runner, 'go_after_support', side_effect=stop):
        try:
            runner.search(*args, **kwargs)
        except SourceBoundary:
            state = read(Path(args[4]) / 'segmented-checkpoint.json')
            assert state['status'] == 'active'
            return state['attempts'], [state]
    raise AssertionError('Compilation fixture did not reach source acceptance')
