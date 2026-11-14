"""Fatal cleanup holds stop search and all common timing entry points."""
from pathlib import Path
import pytest
from test_optimization_controller import controller, rust
from i2r_agent import optimization as opt, owned_process, kernel_timing
from i2r_agent.common import Failure, read, save


@pytest.mark.parametrize('code', ['tool_cleanup_incomplete', 'performance_cleanup_hold', 'process_ownership_unavailable'])
def test_fatal_cleanup_is_not_a_candidate_failure_or_final_selection(controller, monkeypatch, code):
    c = controller
    def failed(*args, **kwargs): raise Failure(code, 'fatal process environment')
    monkeypatch.setattr(opt, 'build_and_validate', failed)
    with pytest.raises(Failure) as error:
        c['run']([rust('candidate before fatal failure')], mode='rust-only')
    assert error.value.code == code
    assert not (c['directory']/'result.json').exists()
    state = read(c['directory']/'search-state.json')
    assert state['attempts'][-1]['status'] == code and state['no_gain'] == 0
    assert read(c['directory']/'budget.json')['active'] is False


def test_persistent_hold_blocks_preparation_and_final_timing(monkeypatch, tmp_path):
    monkeypatch.setattr(owned_process, 'ROOT', tmp_path/'isolated-root')
    hold = owned_process.ROOT/'cache/timing-v2.cleanup-hold.json'
    save(hold, {'requires_explicit_release': True, 'cleanup_record': 'test-only'})
    budget = opt.Budget(tmp_path/'budget.json', 25, 60)
    try:
        with pytest.raises(Failure) as error:
            with opt.computation(budget): pytest.fail('Held environment entered computation')
        assert error.value.code == 'performance_cleanup_hold'
        with pytest.raises(Failure) as error:
            kernel_timing.measure_group('fixture', [], [], None, {}, tmp_path/'timing')
        assert error.value.code == 'performance_cleanup_hold'
        assert not (tmp_path/'timing').exists()
        assert hold.exists()
    finally: budget.close()


@pytest.mark.parametrize('code', sorted(opt.FATAL_EXECUTION_ERRORS))
def test_optional_profile_cannot_swallow_fatal_cleanup_failure(monkeypatch, tmp_path, code):
    from i2r_agent import performance_search
    def failed(*args):
        raise Failure(code, 'owned execution could not be reconciled', {'owned_command': 'test'})
    monkeypatch.setattr(performance_search, 'instrument', failed)
    with pytest.raises(Failure) as error:
        opt.profile({'files': {}}, {}, {}, {}, tmp_path, None)
    assert error.value.code == code
    record = read(tmp_path/'profile.json')
    assert record['status'] == 'aborted' and record['error'] == code


def test_ordinary_profile_failure_stays_optional(monkeypatch, tmp_path):
    from i2r_agent import performance_search
    def failed(*args): raise Failure('profile_compile_failed', 'instrumented build unsupported')
    monkeypatch.setattr(performance_search, 'instrument', failed)
    result = opt.profile({'files': {}}, {}, {}, {}, tmp_path, None)
    assert result['status'] == 'unavailable'
