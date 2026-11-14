"""Actual bounded process trees; no compiler, proof, model, or benchmark runs."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import pytest


@pytest.fixture
def modules(monkeypatch, tmp_path):
    from i2r_agent import common, owned_process as owned
    monkeypatch.setattr(owned, "ROOT", tmp_path/"isolated-root")
    return common, owned


def tree_command(tmp_path, parent_action='sleep', detach_immediately=False):
    record = tmp_path/'fixture-pids.json'
    leaf = 'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(40)'
    middle = ('import os,sys,json,subprocess,signal,time;'
              'signal.signal(signal.SIGTERM,signal.SIG_IGN);'
              f'p=subprocess.Popen([sys.executable,"-c",{leaf!r}],start_new_session=True);'
              f'open({str(record)!r},"w").write(json.dumps([os.getpid(),p.pid]));'
              + ('os._exit(0)' if detach_immediately else 'time.sleep(40)'))
    parent = ('import sys,subprocess,time;'
              f'p=subprocess.Popen([sys.executable,"-c",{middle!r}],start_new_session=True);'
              + ('time.sleep(.25);sys.exit(7)' if parent_action == 'fail' else
                 'time.sleep(.25);sys.exit(0)' if parent_action == 'success' else 'time.sleep(40)'))
    return [sys.executable, '-c', parent], record


def cleanup_fixture(table, record):
    # Only fixture-created, identity-checked PIDs, never unrelated processes.
    if not record.exists(): return
    rows = [table.info(pid) for pid in json.loads(record.read_text())]
    for row in rows:
        if not row or not row['alive']: continue
        current = table.info(row['pid'])
        if current and current['birth'] == row['birth']:
            try: os.kill(row['pid'], signal.SIGKILL)
            except ProcessLookupError: pass


@pytest.mark.parametrize('parent_action,detach', [('sleep', False), ('success', True), ('fail', True)])
def test_detached_children_cleaned_on_timeout_success_and_parent_failure(modules, tmp_path, parent_action, detach):
    common, owned = modules; table = owned.ProcessTable()
    command, record = tree_command(tmp_path, parent_action, detach)
    sentinel = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(40)'], start_new_session=True, cwd=tmp_path)
    before = table.info(sentinel.pid); started = time.monotonic()
    try:
        result = common.Executor(tmp_path/'commands', cleanup_descendants=True).run(command, cwd=tmp_path, timeout=5, check=False)
        assert result['status'] == {'sleep': 'timeout', 'success': 'passed', 'fail': 'failed'}[parent_action]
        assert record.exists()
        rows = [table.info(pid) for pid in json.loads(record.read_text())]
        assert not any(row and row['alive'] for row in rows)
        cleanup = common.read(result['cleanup'])
        assert cleanup['complete'] and not cleanup['remaining']
        assert cleanup['seconds'] <= owned.CLEANUP_SECONDS+.3
        assert time.monotonic()-started <= 5.5
        assert sentinel.poll() is None and owned.same_process(table.info(sentinel.pid), before)
        assert sentinel.pid not in {s['pid'] for s in cleanup['signals']}
        assert any(s['signal'] == 'SIGKILL' for s in cleanup['signals'])
        if detach: assert any(r['ownership'] == 'inherited_marker' for r in cleanup['tracked'])
    finally:
        cleanup_fixture(table, record)
        sentinel.terminate(); sentinel.wait(timeout=2)


def test_legacy_default_keeps_existing_detached_process_behavior(modules, tmp_path):
    common, owned = modules; table = owned.ProcessTable()
    command, record = tree_command(tmp_path, 'success', True)
    try:
        executor = common.Executor(tmp_path/'legacy')
        assert executor.cleanup_descendants is False
        result = executor.run(command, timeout=4)
        assert result['status'] == 'passed' and 'cleanup' not in result
        assert not (tmp_path/'legacy/cleanup').exists()
        assert any((row := table.info(pid)) and row['alive'] for pid in json.loads(record.read_text()))
    finally:
        cleanup_fixture(table, record)


def test_owned_command_stdin_exit_and_cleanup_record_sequence(modules, tmp_path):
    common, owned = modules; executor = common.Executor(tmp_path/'commands', cleanup_descendants=True)
    for number in [1, 2]:
        result = executor.run([sys.executable, '-c', 'import sys; print(sys.stdin.read())'], stdin='hello', timeout=5)
        assert Path(result['stdout']).read_text() == 'hello\n'
        assert Path(result['cleanup']).name == f'{number:04d}.json'
        assert common.read(result['cleanup'])['complete']
    resumed = common.Executor(tmp_path/'commands', cleanup_descendants=True)
    assert resumed.sequence == 2  # Separate cleanup records do not corrupt numbering.


def test_interrupt_cleans_owned_tree_before_propagating(modules, tmp_path, monkeypatch):
    common, owned = modules; table = owned.ProcessTable()
    command, record = tree_command(tmp_path)
    original = subprocess.Popen.communicate
    def interrupted(process, *args, **kwargs):
        until = time.monotonic()+2
        while not record.exists() and time.monotonic() < until: time.sleep(.02)
        raise KeyboardInterrupt
    monkeypatch.setattr(subprocess.Popen, 'communicate', interrupted)
    try:
        with pytest.raises(KeyboardInterrupt):
            common.Executor(tmp_path/'commands', cleanup_descendants=True).run(command, timeout=5)
        cleanup = common.read(tmp_path/'commands/cleanup/0001.json')
        assert cleanup['complete'] and cleanup['reason'] == 'interrupted'
        assert not any((row := table.info(pid)) and row['alive'] for pid in json.loads(record.read_text()))
    finally:
        monkeypatch.setattr(subprocess.Popen, 'communicate', original)
        cleanup_fixture(table, record)


def test_pid_reuse_is_not_ownership(modules, monkeypatch):
    _, owned = modules
    root = {'pid': 700, 'uid': os.getuid(), 'ppid': 1, 'pgid': 700, 'birth': [1, 1], 'alive': True}
    reused = {**root, 'birth': [2, 2]}
    class Table:
        def info(self, pid): return root
        def snapshot(self, deadline=None): return {700: reused}
        def marked(self, pid, token): return False
    class Process:
        pid = 700
        def poll(self): return 0
    tracker = owned.Ownership(Table(), Process(), 'only-my-token')
    assert tracker.scan() == []
    assert not owned.same_process(reused, root)


def test_unsupported_platform_fails_before_spawn(modules, monkeypatch, tmp_path):
    common, owned = modules
    monkeypatch.setattr(owned.sys, 'platform', 'unsupported')
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Do not launch without cleanup support'))
    with pytest.raises(common.Failure) as exc:
        common.Executor(tmp_path/'commands', cleanup_descendants=True).run(['unused'], timeout=5)
    assert exc.value.code == 'process_ownership_unavailable'


def test_transient_marker_read_is_retried(modules):
    _, owned = modules
    root = {'pid': 700, 'uid': os.getuid(), 'ppid': 1, 'pgid': 700, 'birth': [1, 1], 'alive': True}
    orphan = {**root, 'pid': 701, 'pgid': 701, 'birth': [2, 2]}
    class Table:
        reads = 0
        def info(self, pid): return root if pid == 700 else orphan
        def snapshot(self, deadline=None): return {701: orphan}
        def marked(self, pid, token):
            self.reads += 1; return self.reads > 1
    class Process:
        pid = 700
        def poll(self): return 0
    tracker = owned.Ownership(Table(), Process(), 'only-my-token')
    assert tracker.scan() == []
    rows = tracker.scan()
    assert len(rows) == 1 and rows[0]['ownership'] == 'inherited_marker'


def test_gate_release_interrupt_cannot_bypass_cleanup(modules, tmp_path, monkeypatch):
    common, owned = modules; table = owned.ProcessTable(); command, record = tree_command(tmp_path)
    real_write = os.write
    def release_then_interrupt(fd, value):
        result = real_write(fd, value)
        if value == b'G':
            until = time.monotonic()+2
            while not record.exists() and time.monotonic() < until: time.sleep(.02)
            raise KeyboardInterrupt
        return result
    monkeypatch.setattr(os, 'write', release_then_interrupt)
    try:
        with pytest.raises(KeyboardInterrupt):
            common.Executor(tmp_path/'commands', cleanup_descendants=True).run(command, timeout=5)
        assert common.read(tmp_path/'commands/cleanup/0001.json')['complete']
        assert record.exists()
        assert not any((r := table.info(pid)) and r['alive'] for pid in json.loads(record.read_text()))
    finally:
        monkeypatch.setattr(os, 'write', real_write)
        cleanup_fixture(table, record)


def test_concurrent_owned_commands_do_not_kill_each_other(modules, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    common, owned = modules; table = owned.ProcessTable()
    short, record = tree_command(tmp_path)
    long = [sys.executable, '-c', 'import time;time.sleep(2.5);print("independent token survived")']
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(common.Executor(tmp_path/'short', cleanup_descendants=True).run,
                            short, timeout=3, check=False)
            b = pool.submit(common.Executor(tmp_path/'long', cleanup_descendants=True).run,
                            long, timeout=7)
            short_result = a.result(); long_result = b.result()
        assert short_result['status'] == 'timeout' and long_result['status'] == 'passed'
        assert 'survived' in Path(long_result['stdout']).read_text()
        ca = common.read(short_result['cleanup']); cb = common.read(long_result['cleanup'])
        assert ca['owner_marker_sha256'] != cb['owner_marker_sha256']
        assert cb['root']['pid'] not in {r['pid'] for r in ca['signals']}
    finally:
        cleanup_fixture(table, record)


def test_actual_isabelle_bash_process_detached_group_is_cleaned(modules, tmp_path):
    import shlex
    executable = Path('/Applications/Isabelle2025.app/contrib/bash_process-20240326/arm64-darwin/bash_process')
    if sys.platform != 'darwin' or not executable.exists(): pytest.skip('Installed Isabelle2025 macOS wrapper required')
    common, owned = modules; table = owned.ProcessTable(); record = tmp_path/'wrapper-pid.json'
    leaf = ('import os,json,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);'
            f'open({str(record)!r},"w").write(json.dumps([os.getpid()]));time.sleep(40)')
    command = [str(executable), str(tmp_path/'isabelle-timing'), 'bash', '-c',
               'exec '+shlex.quote(sys.executable)+' -c '+shlex.quote(leaf)]
    try:
        result = common.Executor(tmp_path/'commands', cleanup_descendants=True).run(command, timeout=5, check=False)
        cleanup = common.read(result['cleanup'])
        assert result['status'] == 'timeout' and cleanup['complete']
        assert any(r['pgid'] != cleanup['root']['pgid'] for r in cleanup['tracked'])
        assert not any((r := table.info(pid)) and r['alive'] for pid in json.loads(record.read_text()))
    finally:
        cleanup_fixture(table, record)


def test_signal_rechecks_birth_after_snapshot_before_kill(modules, monkeypatch):
    _, owned = modules
    root = {'pid': 700, 'uid': os.getuid(), 'ppid': 1, 'pgid': 700, 'birth': [1, 1], 'alive': True}
    child = {**root, 'pid': 701, 'birth': [1, 2]}
    reused = {**child, 'birth': [2, 2]}
    class Table:
        def info(self, pid): return root if pid == 700 else reused
        def snapshot(self, deadline=None): return {701: child}
        def marked(self, pid, token): return False
    class Process:
        pid = 700
        def poll(self): return 0
    tracker = owned.Ownership(Table(), Process(), 'only-my-token')
    tracker.owned[701] = {**child, 'ownership': 'observed_parent'}
    sent = []; monkeypatch.setattr(os, 'kill', lambda *args: sent.append(args))
    report = tracker.cleanup(time.monotonic()+.1, 'test_pid_reuse')
    assert sent == []
    assert report['identity_mismatches_not_signaled']
    assert not report['complete']  # Contradictory final snapshot is not silently trusted.


def test_recovered_observation_warning_does_not_override_final_clean_scan(modules):
    _, owned = modules
    root = {'pid': 700, 'uid': os.getuid(), 'ppid': 1, 'pgid': 700, 'birth': [1, 1], 'alive': True}
    class Table:
        def info(self, pid): return root
        def snapshot(self, deadline=None): return {}
    class Process:
        pid = 700
        def poll(self): return 0
    tracker = owned.Ownership(Table(), Process(), 'only-my-token'); tracker.warnings.append('TimeoutError')
    report = tracker.cleanup(time.monotonic()+.2, 'recovered_monitor_timeout')
    assert report['complete'] and report['observation_warnings'] == ['TimeoutError']
    assert report['discovery_errors'] == [] and report['unverified_new_processes'] == []


def test_final_unverifiable_marker_fails_closed_without_signaling_stranger(modules, monkeypatch):
    _, owned = modules
    root = {'pid': 700, 'uid': os.getuid(), 'ppid': 1, 'pgid': 700, 'birth': [1, 1], 'alive': True}
    unknown = {**root, 'pid': 701, 'pgid': 701, 'birth': [2, 2]}
    class Table:
        def info(self, pid): return root if pid == 700 else unknown
        def snapshot(self, deadline=None): return {701: unknown}
        def marked(self, pid, token): return None
    class Process:
        pid = 700
        def poll(self): return 0
    tracker = owned.Ownership(Table(), Process(), 'only-my-token')
    sent = []; monkeypatch.setattr(os, 'kill', lambda *args: sent.append(args))
    report = tracker.cleanup(time.monotonic()+.1, 'unverifiable')
    assert not report['complete'] and sent == []
    assert report['unverified_new_processes'][0]['pid'] == 701


def test_cleanup_failure_publishes_persistent_hold_without_affecting_legacy(modules, monkeypatch, tmp_path):
    common, owned = modules
    def failed_cleanup(owner, *args):
        owner.stop.set(); owner.thread.join(timeout=1)
        return {'complete': False, 'root': owner.root, 'remaining': []}
    monkeypatch.setattr(owned.Ownership, 'cleanup', failed_cleanup)
    # The command already exits before the simulated audit failure, so this test
    # creates no real orphan. The isolated ROOT prevents touching an active run.
    with pytest.raises(common.Failure) as exc:
        common.Executor(tmp_path/'managed', cleanup_descendants=True).run([sys.executable, '-c', 'pass'], timeout=5)
    assert exc.value.code == 'tool_cleanup_incomplete'
    hold = owned.ROOT/'cache/timing-v2.cleanup-hold.json'
    assert hold.exists() and common.read(hold)['requires_explicit_release']
    with pytest.raises(common.Failure) as exc: owned.assert_timing_ready()
    assert exc.value.code == 'performance_cleanup_hold'
    # Default-off behavior does not read or erase the performance-only hold.
    assert common.Executor(tmp_path/'legacy').run([sys.executable, '-c', 'pass'])['status'] == 'passed'
    assert hold.exists()


def test_unreadable_tracked_descendant_and_live_root_cannot_be_declared_clean(modules, monkeypatch):
    _, owned = modules
    root = {'pid': 700, 'uid': os.getuid(), 'ppid': 1, 'pgid': 700, 'birth': [1, 1], 'alive': True}
    child = {**root, 'pid': 701, 'birth': [1, 2]}
    class Table:
        first = True
        def info(self, pid):
            if self.first: self.first = False; return root
            return None
        def snapshot(self, deadline=None): return {}
    class Process:
        pid = 700
        def poll(self): return None
    tracker = owned.Ownership(Table(), Process(), 'only-my-token')
    tracker.owned[701] = {**child, 'ownership': 'observed_parent'}
    monkeypatch.setattr(owned, 'process_exists', lambda pid: True)
    sent = []; monkeypatch.setattr(os, 'kill', lambda *args: sent.append(args))
    report = tracker.cleanup(time.monotonic()+.1, 'unreadable_tracked_identity')
    assert not report['complete'] and report['root_returncode'] is None
    assert {r['pid'] for r in report['unverified_new_processes']} == {700, 701}
    assert sent == []


def test_second_quiet_scan_catches_late_orphan(modules, monkeypatch):
    _, owned = modules
    root = {'pid': 700, 'uid': os.getuid(), 'ppid': 1, 'pgid': 700, 'birth': [1, 1], 'alive': True}
    child = {**root, 'pid': 701, 'birth': [1, 2]}
    class Table:
        count = 0
        def info(self, pid): return root if pid == 700 else child
        def snapshot(self, deadline=None):
            self.count += 1
            return {701: child} if self.count == 3 else {}
        def marked(self, pid, token): return True
    class Process:
        pid = 700
        def poll(self): return 0
    table = Table(); tracker = owned.Ownership(table, Process(), 'only-my-token')
    sent = []; monkeypatch.setattr(os, 'kill', lambda pid, sig: sent.append((pid, sig)))
    # After the simulated KILL, the child disappears from info as well.
    original = table.info
    table.info = lambda pid: None if pid == 701 and sent else original(pid)
    monkeypatch.setattr(owned, 'process_exists', lambda pid: False)
    report = tracker.cleanup(time.monotonic()+.3, 'late_orphan')
    assert sent == [(701, signal.SIGKILL)] and report['complete']
    assert report['quiet_scans'] == 2 and table.count >= 5
