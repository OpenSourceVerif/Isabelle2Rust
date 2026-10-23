#!/usr/bin/env python3
"""Local ablation; frozen pilot sources are never modified. No model/API calls."""
import hashlib
import json
import platform
import random
import shutil
import statistics
from pathlib import Path
import run_list_index as common

EXP = common.EXP
BASE = common.REPO / 'test/afp/list-index'
FIXTURE = EXP / 'harness/list-index-diagnostic'
ROOT = EXP / 'runs/20261023-list-index-diagnostic'
RESULT = EXP / 'results/20261023-list-index-diagnostic.json'

def environment():
    return dict(platform=platform.platform(), machine=platform.machine(),
                rustc=common.require(['rustc', '+1.94.0', '-Vv'], ROOT / 'rustc-version.json')['stdout'].strip(),
                ocaml=common.require([common.OPAM / 'bin/ocamlopt', '-version'], ROOT / 'ocaml-version.json')['stdout'].strip())

def main():
    crate = ROOT / 'rust'
    (crate / 'src').mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURE / 'main.rs', crate / 'src/main.rs')
    candidate = BASE / 'llm/EXP-0002/run-001/attempt-01.rs'
    shutil.copy2(candidate, crate / 'src/candidate.rs')
    shutil.copytree(BASE / 'stage2', ROOT / 'optimized', ignore=shutil.ignore_patterns('target'), dirs_exist_ok=True)
    (crate / 'Cargo.toml').write_text('''[package]
name = "list_index_diagnostic"
version = "0.1.0"
edition = "2024"
[features]
alloc = []
[dependencies]
num-bigint = "=0.4.6"
exported = { package = "isabelle_exported", path = "../optimized" }
''')
    for kind, features in [('timing', []), ('allocation', ['--features', 'alloc'])]:
        common.require(common.CARGO + ['build', '--offline', '--release', '--manifest-path', crate / 'Cargo.toml'] + features, ROOT / f'build-{kind}.json')
        shutil.copy2(crate / 'target/release/list_index_diagnostic', ROOT / kind)
    ocaml = ROOT / 'ocaml'
    ocaml.mkdir(exist_ok=True)
    shutil.copy2(BASE / 'ocaml/reference.ml', ocaml / 'exported_reference.ml')
    shutil.copy2(FIXTURE / 'main.ml', ocaml / 'main.ml')
    common.require([common.OPAM / 'bin/ocamlfind', 'ocamlopt', '-package', 'zarith,unix', '-linkpkg', 'exported_reference.ml', 'main.ml', '-o', 'runner'], ROOT / 'build-ocaml.json', cwd=ocaml)
    ops = ['clone_drop', 'candidate_e2e', 'candidate_kernel', 'prepare_list', 'stage2_e2e', 'stage2_kernel', 'stage2_shared_kernel', 'list_clone_drop', 'reverse_clone', 'length', 'ocaml_e2e', 'ocaml_kernel', 'ocaml_prepare_list']
    rows = []
    rng = random.Random(20261023)
    for n, values in [(128, 'small'), (512, 'small'), (512, 'large')]:
        for mode in ['first', 'last', 'absent']:
            cases = {}
            for op in ops:
                binary = ocaml / 'runner' if op.startswith('ocaml') else ROOT / 'timing'
                args = [binary, op, n, mode, values]
                prefix = ROOT / 'logs' / f'{n}-{values}-{mode}-{op}'
                cal = common.require(args + [200], Path(str(prefix) + '-cal.json'))['stdout'].split()
                iterations = max(200, min(2000000, int(30_000_000 / max(float(cal[0])/200, 1))))
                row = dict(n=n, values=values, mode=mode, operation=op, iterations=iterations, ns_per_call=[])
                if not op.startswith('ocaml'):
                    count = common.require([ROOT / 'allocation', op, n, mode, values, 1], Path(str(prefix) + '-allocation.json'))['stdout'].split()
                    row.update(alloc_calls=int(count[0]), allocated_bytes=int(count[1]))
                cases[op] = (args, prefix, row)
            for repeat in range(5):
                order = ops.copy(); rng.shuffle(order)
                for op in order:
                    args, prefix, row = cases[op]
                    out = common.require(args + [row['iterations']], Path(str(prefix) + f'-{repeat}.json'))['stdout'].split()
                    row['ns_per_call'].append(float(out[0])/int(out[1]))
                    if op.startswith('ocaml'):
                        row['ocaml_allocated_bytes_per_call'] = float(out[2])
            for _, _, row in cases.values():
                row['median_ns'] = statistics.median(row['ns_per_call'])
                rows.append(row)
            print(f'finished n={n} values={values} mode={mode}', flush=True)
    sources = [candidate, FIXTURE / 'main.rs', FIXTURE / 'main.ml', Path(__file__), BASE / 'stage2/src/Reference.rs', BASE / 'ocaml/reference.ml']
    result = dict(created=common.now(), environment=environment(), protocol='5 shuffled repeats; calibrated ~30 ms; prebuilt inputs; output drop included; separate allocator-instrumented binary; OCaml normal GC after initial full_major; large values = 2^130 + i; stage2_kernel includes query clone required by owned argument; shared variant changes only element representation to Rc<BigInt>, setup excluded', source_sha256={str(p.relative_to(common.REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, rows=rows)
    common.save(RESULT, result)
    print(RESULT)

if __name__ == '__main__':
    main()
