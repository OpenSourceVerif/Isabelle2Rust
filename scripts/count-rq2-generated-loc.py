#!/usr/bin/env python3
"""Count Stage-1 and Stage-2 generated Rust LOC for the RQ2 workloads."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CRATES = {
    "SBPF-program": {
        "stage1": "tests_sbpf/theory/stage1/bpf_generator_word_checked_interp/interp_test",
        "stage2": "tests_sbpf/theory/stage2/bpf_generator_word_checked_interp/interp_test",
    },
    "SBPF-instruction": {
        "stage1": "tests_sbpf/theory/stage1/bpf_generator_word_checked/step_test",
        "stage2": "tests_sbpf/theory/stage2/bpf_generator_word_checked/step_test",
    },
    "X64-stepper": {
        "stage1": "tests_x64/theory/stage1/x64StepRustPerformanceGenerator/x64_step_test",
        "stage2": "tests_x64/theory/stage2/x64StepRustPerformanceGenerator/x64_step_test",
    },
}


def cloc(root: Path) -> tuple[int, int]:
    if not (root / "Cargo.toml").is_file():
        raise RuntimeError(f"missing generated crate: {root.relative_to(REPO)}")
    result = subprocess.run(
        ["cloc", "--json", "--quiet", "--skip-uniqueness", "--exclude-dir=target", "--include-lang=Rust", str(root)],
        cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    rust = json.loads(result.stdout).get("Rust", {})
    return int(rust.get("nFiles", 0)), int(rust.get("code", 0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path); args = parser.parse_args()
    rows = []
    for workload, stages in CRATES.items():
        for stage, relative in stages.items():
            files, loc = cloc(REPO / relative)
            rows.append({"workload": workload, "stage": stage, "rust_files": files, "rust_loc": loc})
    target = args.output.open("w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    finally:
        if args.output: target.close()
    return 0


if __name__ == "__main__":
    try: sys.exit(main())
    except RuntimeError as error: print(f"ERROR: {error}", file=sys.stderr); sys.exit(1)
