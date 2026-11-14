"""Opt-in command ownership and bounded cleanup, independent of process groups.

A random inherited marker supplements observed parentage when a subprocess
setsid/double-forks before the next scan. Birth identities prevent stale PID
reuse from authorizing a signal. No names, working directories, or blanket
process-group membership are ownership evidence. Environment bytes stay in
memory and are never logged. Not a sandbox against a deliberately evading child.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
import time

from .common import ROOT, Failure, digest, now, save

MARKER = 'I2R_OWNED_COMMAND'
CLEANUP_SECONDS = 3.0
POLL_SECONDS = .15


class ProcessTable:
    """Kernel birth identity, parent and marker access without external packages."""
    def __init__(self):
        self.uid = os.getuid()
        if sys.platform == 'darwin':
            # Layout: apple-oss-distributions/xnu/bsd/sys/proc_info.h proc_bsdinfo.
            u32 = ctypes.c_uint32
            class BSDInfo(ctypes.Structure):
                _fields_ = [(n, u32) for n in ('flags', 'status', 'xstatus', 'pid', 'ppid',
                    'uid', 'gid', 'ruid', 'rgid', 'svuid', 'svgid', 'reserved')] + [
                    ('comm', ctypes.c_char*16), ('name', ctypes.c_char*32)] + [
                    (n, u32) for n in ('nfiles', 'pgid', 'jobc', 'tdev', 'tpgid')] + [
                    ('nice', ctypes.c_int32), ('start_sec', ctypes.c_uint64), ('start_usec', ctypes.c_uint64)]
            self.BSDInfo = BSDInfo
            self.libproc = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
            self.libproc.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
            self.libproc.proc_pidinfo.restype = ctypes.c_int
            self.libproc.proc_listpids.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int]
            self.libproc.proc_listpids.restype = ctypes.c_int
            self.libc = ctypes.CDLL(None, use_errno=True)
            self.libc.sysctl.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_uint, ctypes.c_void_p,
                                        ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
            self.libc.sysctl.restype = ctypes.c_int
            argmax_mib = (ctypes.c_int*2)(1, 8)  # CTL_KERN, KERN_ARGMAX
            argmax = ctypes.c_int(); size = ctypes.c_size_t(ctypes.sizeof(argmax))
            if self.libc.sysctl(argmax_mib, 2, ctypes.byref(argmax), ctypes.byref(size), None, 0) or argmax.value <= 0:
                raise Failure('process_ownership_unavailable', 'Cannot read kernel process-argument capacity')
            self.arg_max = argmax.value
        elif sys.platform != 'linux':
            raise Failure('process_ownership_unavailable', 'Owned cleanup supports Darwin and Linux only')

    def info(self, pid):
        if sys.platform == 'darwin':
            row = self.BSDInfo()
            if self.libproc.proc_pidinfo(pid, 3, 0, ctypes.byref(row), ctypes.sizeof(row)) != ctypes.sizeof(row):
                return None
            if row.pid != pid: return None
            return {'pid': pid, 'ppid': row.ppid, 'pgid': row.pgid, 'uid': row.uid,
                    'birth': [row.start_sec, row.start_usec], 'alive': row.status != 5}
        try:
            entry = Path('/proc')/str(pid)
            text = (entry/'stat').read_text(); fields = text[text.rfind(')')+2:].split()
            return {'pid': pid, 'ppid': int(fields[1]), 'pgid': int(fields[2]), 'uid': entry.stat().st_uid,
                    'birth': [int(fields[19])], 'alive': fields[0] != 'Z'}
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            return None

    def snapshot(self, deadline=None):
        if sys.platform == 'darwin':
            needed = self.libproc.proc_listpids(4, self.uid, None, 0)
            if needed <= 0: raise RuntimeError('Cannot enumerate owned-user processes')
            buffer = (ctypes.c_int*(needed//ctypes.sizeof(ctypes.c_int)+64))()
            count = self.libproc.proc_listpids(4, self.uid, buffer, ctypes.sizeof(buffer))
            if count < 0: raise RuntimeError('Cannot enumerate owned-user processes')
            pids = buffer[:count//ctypes.sizeof(ctypes.c_int)]
        else:
            pids = [int(p.name) for p in Path('/proc').iterdir() if p.name.isdigit()]
        result = {}
        for pid in pids:
            if deadline is not None and time.monotonic() >= deadline: raise TimeoutError('process_scan_deadline')
            if pid <= 0: continue
            info = self.info(pid)
            if info and info['uid'] == self.uid and info['alive']: result[pid] = info
        return result

    def marked(self, pid, token):
        target = (MARKER+'='+token).encode()
        if sys.platform == 'darwin':
            # KERN_PROCARGS2 contains NUL-delimited argv/environment. An exact
            # unpredictable marker matches only this command's inherited env.
            mib = (ctypes.c_int*3)(1, 49, pid)
            storage = ctypes.create_string_buffer(self.arg_max); size = ctypes.c_size_t(len(storage))
            if self.libc.sysctl(mib, 3, storage, ctypes.byref(size), None, 0): return None
            data = storage.raw[:size.value]
        else:
            try: data = (Path('/proc')/str(pid)/'environ').read_bytes()
            except (FileNotFoundError, ProcessLookupError, PermissionError): return None
        return target in data.split(b'\0')


def same_process(current, recorded):
    return bool(current and recorded and current['pid'] == recorded['pid'] and current['uid'] == recorded['uid']
                and current['birth'] == recorded['birth'])


def process_exists(pid):
    """Existence alone never authorizes a signal; it prevents false 'gone'."""
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False
    except PermissionError: return True


class Ownership:
    def __init__(self, table, process, token):
        self.table = table; self.process = process; self.token = token
        self.root = table.info(process.pid)
        if not self.root or not self.root['alive']:
            raise Failure('process_ownership_unavailable', 'Cannot bind gated command process identity')
        self.owned = {process.pid: {**self.root, 'ownership': 'gated_root'}}
        self.errors = []; self.warnings = []; self.unverified = []; self.lock = threading.RLock(); self.stop = threading.Event()
        self.thread = threading.Thread(target=self.monitor, name='i2r-command-ownership', daemon=True)

    def scan(self, deadline=None):
        remaining = -1 if deadline is None else max(0, deadline-time.monotonic())
        if not self.lock.acquire(timeout=remaining): raise TimeoutError('process_scan_lock_deadline')
        try:
            snapshot = self.table.snapshot(deadline=deadline)
            # Parentage is usable only while the parent's birth identity still
            # matches; a reused parent PID cannot confer ownership.
            progress = True
            while progress:
                progress = False
                for pid, info in snapshot.items():
                    if deadline is not None and time.monotonic() >= deadline: raise TimeoutError('process_scan_deadline')
                    if same_process(info, self.owned.get(pid)): continue
                    parent = self.owned.get(info['ppid'])
                    if parent and same_process(snapshot.get(info['ppid']), parent):
                        self.owned[pid] = {**info, 'ownership': 'observed_parent', 'owned_parent': info['ppid']}
                        progress = True
            unverified = []
            for pid, info in snapshot.items():
                if deadline is not None and time.monotonic() >= deadline: raise TimeoutError('process_scan_deadline')
                if same_process(info, self.owned.get(pid)): continue
                if info['birth'] < self.root['birth']: continue
                # Never permanently cache a negative environment read: early
                # exec/reparent races or transient access failures can hide a
                # marker on the first observation.
                marked = self.table.marked(pid, self.token)
                current = self.table.info(pid)
                if same_process(current, info) and current['alive']:
                    if marked:
                        self.owned[pid] = {**info, 'ownership': 'inherited_marker'}
                    elif marked is None:
                        unverified.append({'pid': pid, 'birth': info['birth'], 'reason': 'marker_read_unavailable'})
            live = []
            root_exited = self.process.poll() is not None
            for pid, row in self.owned.items():
                if deadline is not None and time.monotonic() >= deadline: raise TimeoutError('process_scan_deadline')
                if pid == self.root['pid'] and root_exited: continue
                current = snapshot.get(pid) or self.table.info(pid)
                if same_process(current, row):
                    if current['alive']: live.append(row)
                elif current is None and process_exists(pid):
                    unverified.append({'pid': pid, 'birth': row['birth'], 'reason': 'owned_identity_unavailable'})
                elif current and current['birth'] == row['birth'] and current['uid'] != row['uid']:
                    unverified.append({'pid': pid, 'birth': row['birth'], 'reason': 'owned_identity_uid_changed'})
            self.unverified = unverified
            return live
        finally:
            self.lock.release()

    def monitor(self):
        while not self.stop.is_set():
            try: self.scan(deadline=time.monotonic()+.25)
            except Exception as error:
                with self.lock: self.warnings.append(type(error).__name__)
            self.stop.wait(POLL_SECONDS)

    def cleanup(self, deadline, reason):
        started = time.monotonic(); signals = []; mismatches = []
        self.stop.set()
        if self.thread.ident is not None:
            self.thread.join(timeout=max(0, min(.3, deadline-time.monotonic())))
        def signal_owned(rows, sig):
            for row in rows:
                if time.monotonic() >= deadline: break
                current = self.table.info(row['pid'])
                if not same_process(current, row):
                    mismatches.append({'pid': row['pid'], 'expected_birth': row['birth']}); continue
                if not current['alive']: continue
                try:
                    os.kill(row['pid'], sig)
                    signals.append({'pid': row['pid'], 'birth': row['birth'], 'signal': sig.name,
                                    'ownership': row['ownership']})
                except ProcessLookupError: pass
                except PermissionError: self.errors.append('signal_permission_denied')
        # No killpg: every signaled process has individually revalidated ownership.
        rows = []; quiet_scans = 0
        try:
            rows = self.scan(deadline=deadline); signal_owned(rows, signal.SIGTERM)
            term_until = min(deadline, time.monotonic()+min(.5, max(0, deadline-time.monotonic())/3))
            while (rows or self.unverified) and time.monotonic() < term_until:
                self.process.poll(); time.sleep(min(.03, max(0, term_until-time.monotonic())))
                rows = self.scan(deadline=deadline)
            while (rows or self.unverified) and time.monotonic() < deadline:
                signal_owned(rows, signal.SIGKILL); self.process.poll()
                time.sleep(min(.03, max(0, deadline-time.monotonic())))
                rows = self.scan(deadline=deadline)
            # Two complete quiet scans after the direct child is reaped catch
            # a last short-lived fork/reparent during the initial PID snapshot.
            while quiet_scans < 2 and time.monotonic() < deadline:
                rows = self.scan(deadline=deadline)
                if not rows and not self.unverified and self.process.poll() is not None:
                    quiet_scans += 1
                else:
                    quiet_scans = 0; signal_owned(rows, signal.SIGKILL)
                if quiet_scans < 2: time.sleep(min(.03, max(0, deadline-time.monotonic())))
        except Exception as error:
            self.errors.append(type(error).__name__)
        root_returncode = self.process.poll()
        return {'complete': quiet_scans == 2 and root_returncode is not None and not rows and not self.unverified and not self.errors,
                'reason': reason, 'root_returncode': root_returncode, 'quiet_scans': quiet_scans,
                'root': self.root, 'owner_marker_sha256': hashlib.sha256(self.token.encode()).hexdigest(),
                'tracked': list(self.owned.values()), 'signals': signals, 'identity_mismatches_not_signaled': mismatches,
                'remaining': rows, 'unverified_new_processes': self.unverified,
                'discovery_errors': self.errors, 'observation_warnings': self.warnings, 'seconds': time.monotonic()-started,
                'bound_seconds': CLEANUP_SECONDS,
                'ownership_policy': 'Gated root, observed parent with matching birth, or inherited per-command marker; PID/uid/birth rechecked before each individual signal.',
                'limitation': 'Not containment of adversarial descendants that erase the marker and orphan before any observed ancestry. No cwd/name-based fallback is permitted.'}


def assert_timing_ready():
    hold = ROOT/'cache/timing-v2.cleanup-hold.json'
    if hold.exists():
        raise Failure('performance_cleanup_hold', 'A failed owned-process cleanup requires explicit, evidence-backed release before further performance work', {'hold': str(hold)})


def publish_cleanup_hold(cleanup_path, cleanup):
    """A persistent hold is never auto-cleared or replaced by a later worker."""
    hold = ROOT/'cache/timing-v2.cleanup-hold.json'; hold.parent.mkdir(parents=True, exist_ok=True)
    data = {'created_at': now(), 'cleanup_record': str(cleanup_path), 'cleanup_record_sha256': digest(cleanup_path),
            'root_identity': cleanup.get('root'), 'requires_explicit_release': True}
    try: fd = os.open(hold, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError: return
    # Existence already blocks readers, even before this small record is written.
    with os.fdopen(fd, 'w') as output:
        output.write(json.dumps(data, indent=2)+'\n'); output.flush(); os.fsync(output.fileno())


_GATE = '''import os,sys
fd=int(sys.argv[1]); permit=os.read(fd,1); os.close(fd)
if permit != b'G': sys.exit(125)
os.execvpe(sys.argv[2],sys.argv[2:],os.environ)
'''


def run_owned(record, stem, process_env, cwd, stdin, timeout, check):
    """Run one command with cleanup time reserved inside its supplied timeout."""
    assert_timing_ready()
    started = time.monotonic(); deadline = started+timeout; table = ProcessTable()
    if timeout <= .1:
        raise Failure('tool_timeout', 'Not enough command allowance for controlled startup and cleanup', record)
    reserve = min(CLEANUP_SECONDS, timeout/2)
    process_env = dict(process_env); token = secrets.token_hex(24); process_env[MARKER] = token
    read_fd, write_fd = os.pipe(); process = None; ownership = None; interrupted = False
    record['status'] = 'execution_error'
    try:
        with stem.with_suffix('.stdout').open('w') as out, stem.with_suffix('.stderr').open('w') as err:
            process = subprocess.Popen([sys.executable, '-c', _GATE, str(read_fd), *record['command']], cwd=cwd,
                env=process_env, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                stdout=out, stderr=err, start_new_session=True, text=True, pass_fds=(read_fd,))
            os.close(read_fd); read_fd = None
            ownership = Ownership(table, process, token); ownership.thread.start()
            os.write(write_fd, b'G'); os.close(write_fd); write_fd = None
            try:
                process.communicate(stdin, timeout=max(.001, deadline-reserve-time.monotonic()))
                record.update(status='passed' if process.returncode == 0 else 'failed', returncode=process.returncode)
            except subprocess.TimeoutExpired:
                record.update(status='timeout', returncode=process.returncode)
    except KeyboardInterrupt:
        interrupted = True; record['status'] = 'interrupted'
    finally:
        # This covers setup/gate release failures as well as communicate: every
        # registered command is cleaned even if interrupted between those steps.
        for fd in [read_fd, write_fd]:
            if fd is not None: os.close(fd)
        if ownership is not None:
            cleanup_path = stem.parent/'cleanup'/(stem.name+'.json')
            try:
                cleanup = ownership.cleanup(min(deadline, time.monotonic()+reserve), record['status'])
            except Exception as error:
                cleanup = {'complete': False, 'reason': record['status'], 'error': type(error).__name__}
            save(cleanup_path, cleanup)
            record.update(returncode=process.poll(), cleanup=str(cleanup_path), cleanup_complete=cleanup['complete'])
            if not cleanup['complete']:
                publish_cleanup_hold(cleanup_path, cleanup)
                record['command_status'] = record['status']; record['status'] = 'cleanup_incomplete'
        elif process is not None:
            # The gated wrapper has not been permitted to exec the command.
            try: process.wait(timeout=max(.001, min(.5, deadline-time.monotonic())))
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=.5)
        record.update(seconds=time.monotonic()-started, stdout=str(stem.with_suffix('.stdout')),
                      stderr=str(stem.with_suffix('.stderr')))
        save(stem.with_suffix('.json'), record)
    if interrupted: raise KeyboardInterrupt
    if record['status'] == 'cleanup_incomplete':
        raise Failure('tool_cleanup_incomplete', 'Owned subprocesses were not conclusively cleaned; do not start timing', record)
    if check and record['status'] != 'passed':
        tail = (Path(record['stdout']).read_text()+Path(record['stderr']).read_text())[-18000:]
        raise Failure('tool_'+record['status'], tail, record)
    return record
