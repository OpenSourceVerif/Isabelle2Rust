#!/usr/bin/env python3
"""Supplementary Queue/Sieve diagnostics over a completed, immutable RQ2 matrix.

No model calls, selected-code edits, or feedback into search. Kernel, lifetime,
and loop-carried measurements have distinct boundaries and must not replace or
be pooled with the main matrix protocol. Requires Python 3.11+ and Cargo.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import statistics
import subprocess
import time
import tomllib


CASES = {'queue': 'fpp-deq-list', 'sieve': 'hol-eratosthenes'}
MODES = ('off', 'rust-only', 'full')
BACKENDS = ('arbitrary', 'checked')
ROUNDS = 3
SAMPLES = 7


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def copy_if_distinct(source, destination):
    if Path(source).resolve() != Path(destination).resolve(): shutil.copy2(source, destination)


def source_seal(path):
    """Hash every source/config/lock file, without traversing build products."""
    path = Path(path); result = {}
    for base, directories, files in os.walk(path):
        directories[:] = sorted(d for d in directories if d not in {'target', '.git'})
        for name in sorted(files):
            entry = Path(base)/name
            result[str(entry.relative_to(path))] = sha(entry)
    return result


def verify_hashes(expected, label):
    for name, expected_sha in expected.items():
        if not Path(name).is_file() or sha(name) != expected_sha:
            raise RuntimeError(f'{label} changed: {name}')


def find_repository(matrix):
    # A copied script remains usable from its output directory.
    for base in (Path(__file__).resolve(), Path(matrix).resolve()):
        for parent in base.parents:
            if (parent/'agent/src/i2r_agent/optimization.py').is_file():
                return parent
    raise RuntimeError('Cannot locate repository from script or matrix path')


def ensure_search_idle():
    listing = subprocess.run(['ps', '-axo', 'pid=,command='], check=True, capture_output=True, text=True).stdout
    active = []
    for line in listing.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2 or int(fields[0]) == os.getpid(): continue
        command = fields[1]
        if (re.search(r'\bi2r_agent\.experiment_runner\b.*\boptimize\b', command) or
                re.search(r'(?:^|\s)-m\s+i2r_agent\.optimization(?:\s|$)', command)):
            active.append({'pid': int(fields[0]), 'command': command})
    if active:
        raise RuntimeError('Optimization search is still running; defer this audit: ' + json.dumps(active))


@contextmanager
def resource_lock(repository, exclusive, waits):
    """Same global preparation slots and timing lock as the search controller."""
    started = time.monotonic(); cache = repository/'agent/cache'; cache.mkdir(parents=True, exist_ok=True)
    slot = None; entered = False
    def require_clean():
        hold = repository/'agent/cache/timing-v2.cleanup-hold.json'
        if hold.exists():
            raise RuntimeError('Unresolved process cleanup blocks supplementary measurements: '+str(hold))
    try:
        require_clean()
        if not exclusive:
            while slot is None:
                require_clean()
                ensure_search_idle()
                for number in range(2):
                    candidate = (cache/f'optimization-preparation-{number}.lock').open('a+')
                    try:
                        fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB); slot = candidate; break
                    except BlockingIOError:
                        candidate.close()
                if slot is None: time.sleep(.1)
        with (cache/'timing-v2.lock').open('a+') as lock:
            while True:
                require_clean()
                ensure_search_idle()
                try:
                    fcntl.flock(lock, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB); break
                except BlockingIOError:
                    time.sleep(.2)
            require_clean()
            waited = time.monotonic()-started; entered = True
            waits.append({'kind': 'exclusive_timing' if exclusive else 'shared_preparation', 'seconds': waited, 'at': now()})
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
    finally:
        if not entered:
            waits.append({'kind': 'aborted_wait', 'seconds': time.monotonic()-started, 'at': now()})
        if slot is not None:
            fcntl.flock(slot, fcntl.LOCK_UN); slot.close()


def resolve_jobs(matrix, case_names):
    report_path = matrix/'matrix.json'; report = read(report_path)
    if report.get('complete') is not True:
        raise RuntimeError('The main matrix must be complete before supplementary diagnostics')
    inputs = {str(report_path): sha(report_path)}; jobs = []; logical_aliases = {}; source_hashes = {}
    for short in case_names:
        case = CASES[short]; directory = matrix/case; result_path = directory/'result.json'
        result = read(result_path); validation_path = directory/'validation.json'; validation = read(validation_path)
        sealpath = directory/'matrix-seal.json'
        if result.get('status') != 'measured' or result['matrix_seal_sha256'] != sha(sealpath):
            raise RuntimeError(f'Invalid or changed final matrix case: {case}')
        matching = [row for row in report['results'] if row['case'] == case]
        if matching != [result]: raise RuntimeError(f'Matrix report and case result differ: {case}')
        aliases = result.get('executable_aliases')
        expected_keys = {f'{m}-{b}' for m in MODES for b in BACKENDS}
        if not isinstance(aliases, dict) or set(aliases) != expected_keys or aliases != validation.get('executable_aliases'):
            raise RuntimeError(f'Missing or inconsistent executable_aliases: {case}')
        for mode, selected in result.get('selections', {}).items():
            statepath = Path(selected['selected_state']); budget_path = statepath.parent/'budget.json'
            if read(budget_path).get('active'):
                raise RuntimeError(f'{case}/{mode} search budget is still active')
            if sha(statepath) != selected['selected_state_sha256']:
                raise RuntimeError(f'Selected state changed: {statepath}')
            inputs[str(statepath)] = sha(statepath)
        for name in [result_path, validation_path, sealpath]: inputs[str(name)] = sha(name)
        for logical, canonical in aliases.items():
            if canonical not in expected_keys or aliases.get(canonical) != canonical or logical.rsplit('-', 1)[1] != canonical.rsplit('-', 1)[1]:
                raise RuntimeError(f'Invalid canonical executable alias: {logical} -> {canonical}')
            logical_aliases[case+'-'+logical] = case+'-'+canonical
        for canonical in sorted(set(aliases.values())):
            timing = directory/'builds'/canonical/'timing'; build_path = timing/'build-v2.json'; build = read(build_path)
            crate = timing/'crate'
            if not crate.is_dir(): raise RuntimeError(f'Missing canonical timing crate: {crate}')
            for field in ['source_hashes', 'artifact_hashes']:
                if not build.get(field): raise RuntimeError(f'Missing build integrity record: {build_path}/{field}')
                verify_hashes(build[field], field); inputs.update(build[field])
            inputs[str(build_path)] = sha(build_path)
            for relative in ['src/lib.rs', 'Cargo.toml', 'harness/Cargo.lock', 'numeric-runtime/src/lib.rs']:
                if str(crate/relative) not in build['artifact_hashes']:
                    raise RuntimeError(f'Unsealed canonical source: {crate/relative}')
            source_hashes[str(crate)] = source_seal(crate)
            jobs.append({'id': case+'-'+canonical, 'case': case, 'short': short,
                         'backend': canonical.rsplit('-', 1)[1], 'canonical': canonical,
                         'aliases': sorted(k for k, v in logical_aliases.items() if v == case+'-'+canonical),
                         'crate': str(crate), 'build_record': str(build_path)})
    return jobs, logical_aliases, inputs, source_hashes


def execute(command, directory, stem, timeout):
    started = time.monotonic(); directory.mkdir(parents=True, exist_ok=True)
    with (directory/(stem+'.stdout')).open('w') as stdout, (directory/(stem+'.stderr')).open('w') as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, text=True, start_new_session=True)
        status = 'passed'
        try:
            process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            status = 'timeout' if isinstance(error, subprocess.TimeoutExpired) else 'interrupted'
            try: os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait()
        if status == 'passed' and process.returncode: status = 'failed'
    record = {'command': command, 'status': status, 'returncode': process.returncode, 'seconds': time.monotonic()-started,
              'stdout': str(directory/(stem+'.stdout')), 'stderr': str(directory/(stem+'.stderr'))}
    record['stdout_sha256'] = sha(record['stdout']); record['stderr_sha256'] = sha(record['stderr'])
    save(directory/(stem+'.json'), record)
    if status != 'passed': raise RuntimeError(f'{stem} {status}; see {directory/(stem+".stderr")}')
    return record


def verify_dependency_lock(frozen, diagnostic):
    def external(path):
        return {(p['name'], p['version'], p.get('source'), p.get('checksum'))
                for p in tomllib.loads(Path(path).read_text()).get('package', []) if p.get('source')}
    # The independent harness may omit observer-only dependencies, but every
    # retained registry dependency must be exactly pinned as in the matrix.
    if not external(diagnostic) <= external(frozen):
        raise RuntimeError('Independent harness changed a registry dependency from the canonical lock')


def parse_timings(text, job, round_number):
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 7 or fields[0] != 'TIME': raise RuntimeError(f'Malformed timing output: {line!r}')
        _, boundary, n, acc, sample, repetitions, elapsed = fields
        n, acc, sample, repetitions, elapsed = map(int, [n, acc, sample, repetitions, elapsed])
        if boundary not in {'kernel', 'lifetime', 'chained'} or repetitions <= 0 or elapsed <= 0:
            raise RuntimeError('Invalid supplementary timing sample')
        rows.append({'implementation': job['id'], 'aliases': job['aliases'], 'round': round_number,
                     'scope': boundary, 'n': n, 'acc': acc, 'sample': sample, 'iterations': repetitions,
                     'batch_ns': elapsed, 'ns': elapsed/repetitions,
                     'role': 'loop_carried_identity_diagnostic' if boundary == 'chained' else 'supplementary_'+boundary})
    expected = ({('kernel', 1024, m) for m in (0, 64, 1024)} |
                {('lifetime', 1024, m) for m in (0, 64, 1024)} | {('chained', 1024, 0)}
                if job['short'] == 'queue' else {('kernel', 4096, 0), ('kernel', 4097, 0)})
    groups = {(r['scope'], r['n'], r['acc']) for r in rows}
    if groups != expected: raise RuntimeError('Missing or unexpected diagnostic workloads')
    for group in groups:
        samples = [r['sample'] for r in rows if (r['scope'], r['n'], r['acc']) == group]
        if sorted(samples) != list(range(SAMPLES)): raise RuntimeError('Require exactly seven distinct samples per workload')
    return rows


def summarize(raw, aliases):
    timings = []; canonical = {}
    keys = sorted({(x['implementation'], x['scope'], x['n'], x['acc']) for x in raw})
    for implementation, boundary, n, acc in keys:
        rows = [x for x in raw if (x['implementation'], x['scope'], x['n'], x['acc']) == (implementation, boundary, n, acc)]
        if len(rows) != ROUNDS*SAMPLES or {x['round'] for x in rows} != set(range(ROUNDS)):
            raise RuntimeError('Final summary requires three complete independent process rounds')
        medians = [statistics.median(x['ns'] for x in rows if x['round'] == r) for r in range(ROUNDS)]
        value = {'implementation': implementation, 'scope': boundary, 'n': n, 'acc': acc,
                 'median_ns': statistics.median(medians), 'process_medians_ns': medians,
                 'minimum_batch_ns': min(x['batch_ns'] for x in rows), 'role': rows[0]['role']}
        timings.append(value); canonical[(implementation, boundary, n, acc)] = value
    comparisons = []
    for logical, target in sorted(aliases.items()):
        case = next(c for c in CASES.values() if logical.startswith(c+'-'))
        backend = logical.rsplit('-', 1)[1]; off = aliases[case+'-off-'+backend]
        for (implementation, boundary, n, acc), value in canonical.items():
            if implementation != target: continue
            reference = canonical[(off, boundary, n, acc)]
            comparisons.append({'logical_implementation': logical, 'canonical_implementation': target,
                                'scope': boundary, 'n': n, 'acc': acc, 'median_ns': value['median_ns'],
                                'off_same_backend_speedup': reference['median_ns']/value['median_ns'],
                                'role': value['role'], 'identical_executable_to_off': target == off})
    return timings, comparisons


def run(matrix, output, case_names):
    matrix, output = matrix.resolve(), output.resolve(); repository = find_repository(matrix)
    if output == matrix or matrix in output.parents or output in matrix.parents:
        raise RuntimeError('Audit output must be separate from the immutable matrix')
    ensure_search_idle()
    jobs, aliases, inputs, before = resolve_jobs(matrix, case_names)
    identity = {'schema': 1, 'script_sha256': sha(__file__), 'matrix': str(matrix), 'cases': case_names,
                'rounds': ROUNDS, 'samples_per_round': SAMPLES, 'input_hashes': inputs,
                'executable_aliases': aliases, 'source_hashes_before': before,
                'harness_hashes': {k: hashlib.sha256(v.encode()).hexdigest() for k, v in HARNESSES.items()},
                'jobs': jobs}
    output.mkdir(parents=True, exist_ok=True)
    with (output/'audit.lock').open('a+') as own_lock:
        fcntl.flock(own_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        intent_path = output/'intent.json'
        if intent_path.exists():
            if read(intent_path)['identity'] != identity: raise RuntimeError('Audit inputs changed; use a new output directory')
        else:
            save(intent_path, {'identity': identity, 'created_at': now(), 'diagnostic_only': True,
                'no_model_calls': True, 'no_selected_code_edits': True,
                'scope_note': 'Supplementary diagnostics only; never pool these samples with the main matrix.',
                'queue_boundaries': {'kernel': 'Independent prepared owned inputs -> opaque noinline invocation -> retained complete outputs; equality outside clock',
                    'lifetime': 'Numeric container copies -> call -> full output comparison -> destruction; all inside clock, excludes text I/O',
                    'chained': 'Empty-accumulator identity with loop-carried owned output; diagnostic only, final equality outside clock'},
                'sieve': 'Literal source-helper oracle plus independent trial division, including arbitrary counters above 128 bits; complete outputs checked'})
        copied = output/Path(__file__).name
        copy_if_distinct(__file__, copied)
        if (output/'summary.json').exists() and read(output/'summary.json').get('complete'):
            verify_hashes(inputs, 'matrix input')
            if {p: source_seal(p) for p in before} != before: raise RuntimeError('Canonical source changed')
            completed = read(output/'summary.json')
            for name, key in [('raw.json', 'raw_sha256'), ('checks.json', 'checks_sha256'), ('source-hashes.json', 'source_hashes_sha256')]:
                if sha(output/name) != completed[key]: raise RuntimeError(f'Completed audit artifact changed: {name}')
            for key, checked in completed['checks'].items():
                if sha(output/'binaries'/key) != checked['binary_sha256']: raise RuntimeError(f'Completed audit executable changed: {key}')
            print('AUDIT_ALREADY_COMPLETE', output, flush=True); return
        waits = []; checks = {}; raw = []; binaries = {}; rounds = []
        cargo = shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo')
        try:
            for job in jobs:
                ensure_search_idle(); work = output/'harnesses'/job['id']; crate = Path(job['crate'])
                with resource_lock(repository, False, waits):
                    (work/'src').mkdir(parents=True, exist_ok=True)
                    code = HARNESSES[job['short']].replace('__BACKEND__', job['backend'])
                    (work/'src/main.rs').write_text(code)
                    shutil.copy2(crate/'harness/Cargo.lock', work/'Cargo.lock')
                    (work/'Cargo.toml').write_text('[package]\nname = "i2r_integrity_audit"\nversion = "0.1.0"\nedition = "2024"\n[dependencies]\n'
                        + 'i2r_candidate = { path = '+json.dumps(str(crate))+', default-features = false, features = ["i2r-'+job['backend']+'"] }\n'
                        + 'i2r-numeric = { path = '+json.dumps(str(crate/'numeric-runtime'))+', default-features = false, features = ["'+job['backend']+'"] }\n')
                    toolchain = tomllib.loads((crate/'rust-toolchain.toml').read_text())['toolchain']['channel']
                    print('AUDIT_BUILD', job['id'], flush=True)
                    build = execute([cargo, '+'+toolchain, 'build', '--offline', '--release', '--manifest-path', str(work/'Cargo.toml'),
                                     '--target-dir', str(output/'target')], work, 'build', 300)
                    verify_dependency_lock(crate/'harness/Cargo.lock', work/'Cargo.lock')
                    binary = output/'binaries'/job['id']; binary.parent.mkdir(exist_ok=True)
                    shutil.copy2(output/'target/release/i2r_integrity_audit', binary); binaries[job['id']] = binary
                    checked = execute([str(binary), 'check'], work, 'check', 300)
                    text = Path(checked['stdout']).read_text().strip()
                    if not text.startswith('CHECK '): raise RuntimeError('Semantic checks produced no explicit completion record')
                    checks[job['id']] = {'status': 'passed', 'output': text, 'execution': checked, 'build': build,
                        'binary_sha256': sha(binary), 'harness_sha256': sha(work/'src/main.rs'), 'aliases': job['aliases'],
                        'supplementary_lock_sha256': sha(work/'Cargo.lock'), 'canonical_lock_sha256': sha(crate/'harness/Cargo.lock')}
                    save(output/'checks.json', checks)
            with resource_lock(repository, True, waits):
                for number in range(ROUNDS):
                    order = jobs[number:]+jobs[:number]  # Fixed order, never chosen from observed gains.
                    for position, job in enumerate(order):
                        ensure_search_idle(); binary = binaries[job['id']]; work = output/'harnesses'/job['id']
                        if sha(binary) != checks[job['id']]['binary_sha256']: raise RuntimeError('Audit executable changed')
                        print('AUDIT_TIME', number, job['id'], flush=True)
                        timed = execute([str(binary), 'timing'], work, f'timing-{number}', 300)
                        raw.extend(parse_timings(Path(timed['stdout']).read_text(), job, number))
                        rounds.append({'round': number, 'position': position, 'implementation': job['id'], 'execution': timed})
                        save(output/'raw.json', raw); save(output/'rounds.json', rounds)
            verify_hashes(inputs, 'matrix input')
            after = {p: source_seal(p) for p in before}
            save(output/'source-hashes.json', {'before': before, 'after': after, 'unchanged': before == after, 'aliases': aliases})
            if before != after: raise RuntimeError('A canonical source changed during supplementary audit')
            timings, comparisons = summarize(raw, aliases)
            save(output/'summary.json', {'complete': True, 'finished_at': now(), 'checks': checks,
                'timings': timings, 'logical_comparisons': comparisons, 'executable_aliases': aliases,
                'unique_executables': len(jobs), 'original_sources_unchanged': True,
                'role': 'Supplementary diagnostics; chained identity results are not main-protocol kernel results',
                'rounds': ROUNDS, 'samples_per_round': SAMPLES, 'timing_order': rounds,
                'raw_sha256': sha(output/'raw.json'), 'checks_sha256': sha(output/'checks.json'),
                'source_hashes_sha256': sha(output/'source-hashes.json')})
            print('AUDIT_COMPLETE', output, flush=True)
        except Exception as error:
            after = {p: source_seal(p) for p in before}
            save(output/'source-hashes.json', {'before': before, 'after': after, 'unchanged': before == after, 'aliases': aliases})
            save(output/'failure.json', {'at': now(), 'type': type(error).__name__, 'message': str(error)})
            raise
        finally:
            save(output/'scheduling.json', {'waits': waits, 'preparation': 'shared timing-v2 lock and one of two global preparation slots',
                                          'timing': 'exclusive timing-v2 lock, never nested inside shared lock'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', type=Path, required=True, help='Completed final matrix directory')
    parser.add_argument('--output', type=Path, required=True, help='Separate directory for diagnostic artifacts')
    parser.add_argument('--cases', nargs='+', choices=sorted(CASES), default=['queue', 'sieve'])
    args = parser.parse_args()
    if len(set(args.cases)) != len(args.cases): parser.error('--cases must not contain duplicates')
    run(args.matrix, args.output, args.cases)


QUEUE_HARNESS = r'''#![forbid(unsafe_code)]
use i2r_candidate::{List, deq2list};
use i2r_numeric::Nat;
use std::hint::black_box;
use std::time::Instant;

#[derive(Debug, PartialEq, Eq)]
struct Payload { n: u128, text: String }

fn semantic_checks() {
    let mut cases = 0usize;
    let mut wrapped = 0usize;
    for n in [0,1,2,3,7,16,63,64,65,256,1024] {
        for m in [0,1,2,3,7,16,63,64,65,256] {
            for shift in [0,1,5] {
                let make = |len: usize, offset: u128| -> List<Payload> {
                    let mut v: List<_> = (0..len).map(|i| Payload {
                        n: u128::MAX - (i as u128 + offset),
                        text: format!("payload-{}-{}", offset, i),
                    }).collect();
                    for _ in 0..shift { if let Some(x) = v.pop_front() { v.push_back(x); } }
                    v
                };
                let q = make(n, 0); let a = make(m, 10000);
                wrapped += usize::from(!q.as_slices().1.is_empty() || !a.as_slices().1.is_empty());
                let expected: Vec<_> = q.iter().chain(a.iter()).map(|x|(x.n,x.text.clone())).collect();
                let actual: Vec<_> = deq2list(q,a).into_iter().map(|x|(x.n,x.text)).collect();
                assert_eq!(actual,expected, "n={n} m={m} shift={shift}"); cases += 1;
            }
        }
    }
    println!("CHECK queue_nonclone_payload {cases} wrapped {wrapped}");
}

#[inline(never)]
fn invoke(q: List<Nat>, a: List<Nat>) -> List<Nat> {
    deq2list(black_box(q),black_box(a))
}

fn numeric_inputs(n: usize, m: usize) -> (List<Nat>,List<Nat>,Vec<Nat>) {
    let q:List<_>=(0..n).rev().map(|x|Nat::from(x+1)).collect();
    let a:List<_>=(0..m).map(|x|Nat::from(x+10000)).collect();
    let expected=q.iter().chain(a.iter()).cloned().collect();
    (q,a,expected)
}

fn kernel_batch(n:usize,m:usize,reps:usize) -> u128 {
    let (q,a,expected)=numeric_inputs(n,m);
    let inputs:Vec<_>=(0..reps).map(|_|black_box((q.clone(),a.clone()))).collect();
    let mut out=Vec::with_capacity(reps);
    let start=Instant::now();
    for (q,a) in inputs {out.push(black_box(invoke(q,a)));}
    let elapsed=start.elapsed().as_nanos();
    for x in out {assert!(x.iter().eq(expected.iter()));}
    elapsed
}

// Independent lifetime measurement: cloning ready numeric inputs, executing,
// inspecting every result value, and destruction are all included. No text I/O.
fn lifetime_batch(n:usize,m:usize,reps:usize) -> u128 {
    let (q,a,expected)=numeric_inputs(n,m);
    let start=Instant::now();
    for _ in 0..reps {
        let out=black_box(invoke(black_box(&q).clone(),black_box(&a).clone()));
        assert!(out.iter().eq(black_box(&expected).iter()));
        drop(out);
    }
    start.elapsed().as_nanos()
}

// Identity-operation timing with a loop-carried owned buffer. This permits a
// long timer window without retaining millions of 1024-element allocations.
// Only an empty accumulator is valid for this diagnostic; outputs are checked.
fn chained_batch(n:usize,reps:usize) -> u128 {
    let (mut q,_,expected)=numeric_inputs(n,0);
    let start=Instant::now();
    for _ in 0..reps {q=black_box(invoke(q,black_box(List::new())));}
    let elapsed=start.elapsed().as_nanos();
    assert!(q.iter().eq(expected.iter()));
    elapsed
}

fn timing() {
    for (n,m) in [(1024,0),(1024,64),(1024,1024)] {
        let size=std::mem::size_of::<Nat>()*(n+m).max(1)+128;
        let reps=(64*1024*1024/size).clamp(1,8192);
        kernel_batch(n,m,16);
        for sample in 0..7 {let ns=kernel_batch(n,m,reps);println!("TIME kernel {n} {m} {sample} {reps} {ns}");}
        let probe=lifetime_batch(n,m,16).max(1);
        let reps=((20_000_000u128*16/probe) as usize).clamp(1,65536);
        lifetime_batch(n,m,reps);
        for sample in 0..7 {let ns=lifetime_batch(n,m,reps);println!("TIME lifetime {n} {m} {sample} {reps} {ns}");}
    }
    let probe=chained_batch(1024,1024).max(1);
    let reps=((50_000_000u128*1024/probe) as usize).clamp(1,30_000_000);
    chained_batch(1024,reps);
    for sample in 0..7 {let ns=chained_batch(1024,reps);println!("TIME chained 1024 0 {sample} {reps} {ns}");}
}

fn main() {
    let check=std::env::args().any(|x|x=="check");
    if check {semantic_checks();} else {timing();}
}
'''

SIEVE_HARNESS = r'''#![forbid(unsafe_code)]
use i2r_candidate::{Nat, mark_out, mark_out_aux, sieve, primes_upto};
use std::hint::black_box;
use std::time::Instant;
const BACKEND: &str = "__BACKEND__";

// Literal source transition oracle; deliberately no strided-index rewrite.
fn literal_mark(n:&Nat,mut m:Nat,bs:&[bool])->Vec<bool> {
    bs.iter().map(|b|if m.is_zero(){m=n.clone();false}else{m=m.sub_trunc(&Nat::one());*b}).collect()
}
fn literal_sieve(n:&Nat,bs:&[bool])->Vec<bool> {
    let mut result=bs.to_vec(); let mut k=n.clone();
    for i in 0..result.len() {
        if result[i] {
            let tail=literal_mark(&k,k.clone(),&result[i+1..]);
            result[i+1..].copy_from_slice(&tail);
        }
        k+=Nat::one();
    }
    result
}
fn trial_division(n:usize)->Vec<Nat> {
    (2..=n).filter(|x| {
        let mut d=2usize;
        while d<=x/d {if x%d==0{return false;} d+=1;}
        true
    }).map(Nat::from).collect()
}

fn semantic_checks() {
    let mut marked=0usize;let mut sieved=0usize;let mut roots=0usize;
    for len in 0..=8 {
        for bits in 0..(1usize<<len) {
            let bs:Vec<_>=(0..len).map(|i|bits&(1<<i)!=0).collect();
            for n in 0..=10usize {
                let nn=Nat::from(n);
                assert_eq!(sieve(&nn,bs.clone()),literal_sieve(&nn,&bs));sieved+=1;
                assert_eq!(mark_out(&nn,bs.clone()),literal_mark(&nn,nn.clone(),&bs));marked+=1;
                for m in 0..=10usize {
                    assert_eq!(mark_out_aux(&nn,Nat::from(m),bs.clone()),literal_mark(&nn,Nat::from(m),&bs));marked+=1;
                }
            }
        }
    }
    let texts=["0","1","16","18446744073709551615","18446744073709551616",
        "340282366920938463463374607431768211327","340282366920938463463374607431768211473"];
    let large:Vec<Nat>=texts.iter().filter_map(|s|s.parse().ok()).collect();
    // An arbitrary parser silently dropping the >128-bit case is a failure.
    assert_eq!(large.len(), if BACKEND == "arbitrary" {7} else {6});
    println!("CHECK sieve_bigcounter parsed {} excluded {} backend {}",large.len(),texts.len()-large.len(),BACKEND);
    for n in &large {for m in &large {for len in [0,1,2,7,31] {
        let bs:Vec<_>=(0..len).map(|x|x%3!=1).collect();
        assert_eq!(mark_out_aux(n,m.clone(),bs.clone()),literal_mark(n,m.clone(),&bs));marked+=1;
        assert_eq!(sieve(n,bs.clone()),literal_sieve(n,&bs));sieved+=1;
    }}}
    // All small bounds plus new seeded bounds, squares, and original-size neighbors.
    let mut ns:Vec<usize>=(0..=256).collect();
    ns.extend([257,289,361,511,512,513,1023,1024,1025,4095,4096,4097,8191,8192]);
    let mut seed=0xa318de7bu64;
    for _ in 0..24 {seed=seed.wrapping_mul(6364136223846793005).wrapping_add(1);ns.push(257+(seed as usize)%5744);}
    ns.sort();ns.dedup();
    for n in ns {assert_eq!(primes_upto(&Nat::from(n)),trial_division(n),"n={n}");roots+=1;}
    println!("CHECK sieve_helpers mark {marked} sieve {sieved} prime_roots {roots}");
}

#[inline(never)]
fn invoke(n:&Nat)->Vec<Nat>{primes_upto(black_box(n))}

fn batch(n:usize,reps:usize)->u128 {
    let nn=Nat::from(n);let expected=trial_division(n);
    let mut results=Vec::with_capacity(reps);
    let start=Instant::now();
    for _ in 0..reps {results.push(black_box(invoke(black_box(&nn))));}
    let elapsed=start.elapsed().as_nanos();
    for x in results {assert_eq!(x,expected);}
    elapsed
}
fn main(){
    if std::env::args().any(|x|x=="check"){semantic_checks();return;}
    for n in [4096,4097] {
        let probe=batch(n,1).max(1);
        let reps=(20_000_000u128/probe).clamp(1,2048) as usize;
        batch(n,reps);
        for sample in 0..7 {let ns=batch(n,reps);println!("TIME kernel {n} 0 {sample} {reps} {ns}");}
    }
}
'''

HARNESSES = {'queue': QUEUE_HARNESS, 'sieve': SIEVE_HARNESS}

if __name__ == '__main__':
    main()
