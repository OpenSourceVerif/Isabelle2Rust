#!/usr/bin/env python3
"""Count explicit .clone() call sites in the 95-pair RQ3 Clippy corpus."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
EXPORT_CODE = re.compile(r"^\s*export_code(?:\s|$)", re.MULTILINE)
CLONE = re.compile(r"\.clone\s*\(\s*\)")
NATURAL = re.compile(r"(\d+)")
CASE_STUDIES = {
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


def natural_key(path: Path) -> list[object]:
    return [int(p) if p.isdigit() else p for p in NATURAL.split(str(path).lower())]


def theories(suite: str) -> list[Path]:
    result = subprocess.run(["git", "ls-files", "--", f"test/{suite}"], cwd=REPO, text=True, stdout=subprocess.PIPE, check=True)
    answer = []
    for relative in result.stdout.splitlines():
        if relative.startswith("test/unit/example/"): continue
        path = REPO / relative
        if path.is_file() and path.name.endswith("_Test.thy") and EXPORT_CODE.search(path.read_text()): answer.append(path)
    return sorted(answer)


def crate(theory: Path, stage: str) -> Path:
    root = theory.parent / stage / theory.stem
    manifests = [p for p in root.rglob("Cargo.toml") if "target" not in p.relative_to(root).parts]
    if not manifests: raise RuntimeError(f"missing {stage} crate for {theory.relative_to(REPO)}")
    return sorted(manifests, key=lambda p: natural_key(p.relative_to(root)))[-1].parent


def count(roots: list[Path]) -> tuple[int, int]:
    files = sorted({p for root in roots for p in root.rglob("*.rs") if "target" not in p.relative_to(root).parts})
    return len(files), sum(len(CLONE.findall(path.read_text(encoding="utf-8", errors="replace"))) for path in files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path); args = parser.parse_args()
    groups = {
        "HCT-standard": [REPO / "test/HOL_Codegenerator/Generate.thy"],
        "Unit": theories("unit"), "FPP": theories("fpp")
    }
    rows = []
    for group, selected in groups.items():
        for stage in ("stage1", "stage2"):
            files, clones = count([crate(theory, stage) for theory in selected])
            rows.append({"scope": group, "stage": stage, "crates": len(selected), "rust_files": files, "clone_sites": clones})
    for group, stages in CASE_STUDIES.items():
        for stage, relative in stages.items():
            files, clones = count([REPO / relative])
            rows.append({"scope": group, "stage": stage, "crates": 1, "rust_files": files, "clone_sites": clones})
    for stage in ("stage1", "stage2"):
        stage_rows = [row for row in rows if row["stage"] == stage]
        rows.append({"scope": "Total", "stage": stage, "crates": sum(int(r["crates"]) for r in stage_rows), "rust_files": sum(int(r["rust_files"]) for r in stage_rows), "clone_sites": sum(int(r["clone_sites"]) for r in stage_rows)})
    target = args.output.open("w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    finally:
        if args.output: target.close()
    return 0


if __name__ == "__main__":
    try: sys.exit(main())
    except RuntimeError as error: print(f"ERROR: {error}", file=sys.stderr); sys.exit(1)
