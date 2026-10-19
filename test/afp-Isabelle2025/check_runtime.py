#!/usr/bin/env python3
"""Independent List-Index semantic harness for --runtime-command.

Build a separate harness crate so the generated Rust files remain untouched.
The Stage-2 signature adapters are in runtime/list_index.rs; both stages use
the same finite-list oracle. Passing this harness covers only these inputs.
"""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

from afp_common import HERE, PROJECT, command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry", choices=["List-Index"])
    parser.add_argument("stage1", type=Path)
    parser.add_argument("stage2", type=Path)
    args = parser.parse_args()
    # Reuse the runner's bound and stable toolchain; its outer timeout also
    # bounds the entire harness, while these limits bound each Cargo invocation.
    args.timeout = 180
    args.min_available_mb = 512
    env = os.environ.copy()
    env.pop("RUSTC_BOOTSTRAP", None)
    # Standalone invocation observes the same Cargo job bound as run.py.
    env["CARGO_BUILD_JOBS"] = "1"
    cargo = shlex.split(env.get("CARGO", "cargo +1.94.0"))
    for stage, root in (("stage1", args.stage1), ("stage2", args.stage2)):
        manifests = sorted(root.glob("export*/Cargo.toml"))
        if len(manifests) != 1:
            raise ValueError("Expected one generated List-Index crate under " + str(root))
        work = HERE / "_build/runtime" / stage
        work.mkdir(parents=True, exist_ok=True)
        (work / "src").mkdir(exist_ok=True)
        shutil.copyfile(HERE / "runtime/list_index.rs", work / "src/main.rs")
        (work / "Cargo.toml").write_text(
            '[package]\nname = "afp_list_index_runtime"\nversion = "0.1.0"\nedition = "2024"\n'
            '[dependencies]\nnum-bigint = "0.4.6"\nexported = { package = "isabelle_exported", path = '
            + json.dumps(str(manifests[0].parent.resolve())) + " }\n")
        stage_env = dict(env, RUSTFLAGS=env.get("RUSTFLAGS", "") +
                         (" --cfg stage2" if stage == "stage2" else "") + " -Awarnings")
        log = HERE / "logs/List-Index" / (stage + ".runtime.log")
        lock = command([sys.executable, str(PROJECT / "scripts/ensure-cargo-lock.py"),
                        str(work / "Cargo.toml"), str(PROJECT / "scripts/isabelle-exported.Cargo.lock")],
                       log.with_name(stage + ".runtime-lock.log"), args, stage_env)
        if lock["status"] != "passed":
            raise RuntimeError("Runtime harness lockfile failed: " + lock["log"])
        checked = command([*cargo, "run", "--quiet", "--locked", "--manifest-path",
                           str(work / "Cargo.toml")], log, args, stage_env)
        if checked["status"] != "passed":
            raise RuntimeError("Runtime checks failed: " + checked["log"])
        print(log.read_text().splitlines()[-1], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
