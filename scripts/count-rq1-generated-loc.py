#!/usr/bin/env python3
"""Count cloc Rust LOC for the generated RQ1 Stage-1/Stage-2 corpus."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
EXPORT_CODE = re.compile(r"^\s*export_code(?:\s|$)", re.MULTILINE)
NATURAL = re.compile(r"(\d+)")


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part for part in NATURAL.split(str(path).lower())]


def tracked_theories(suite: str) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", f"test/{suite}"], cwd=REPO, text=True,
        stdout=subprocess.PIPE, check=True
    )
    selected = []
    for relative in result.stdout.splitlines():
        if relative.startswith("test/unit/example/"):
            continue
        path = REPO / relative
        if path.is_file() and path.name.endswith("_Test.thy") and EXPORT_CODE.search(path.read_text()):
            selected.append(path)
    return sorted(selected)


def latest_crate(theory: Path, stage: str) -> Path:
    root = theory.parent / stage / theory.stem
    manifests = [p for p in root.rglob("Cargo.toml") if "target" not in p.relative_to(root).parts]
    if not manifests:
        raise RuntimeError(f"missing {stage} crate for {theory.relative_to(REPO)}")
    return sorted(manifests, key=lambda p: natural_key(p.relative_to(root)))[-1].parent


def cloc(roots: list[Path]) -> tuple[int, int]:
    command = ["cloc", "--json", "--quiet", "--skip-uniqueness", "--exclude-dir=target", "--include-lang=Rust"]
    command.extend(map(str, roots))
    result = subprocess.run(command, cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    rust = json.loads(result.stdout).get("Rust", {})
    return int(rust.get("nFiles", 0)), int(rust.get("code", 0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    suites = {
        "HCT-standard": [REPO / "test/HOL_Codegenerator/Generate.thy"],
        "HCT-binary-nat": [REPO / "test/HOL_Codegenerator/Generate_Binary_Nat.thy"],
        "Unit": tracked_theories("unit"),
        "FPP": tracked_theories("fpp"),
    }
    rows = []
    for suite, theories in suites.items():
        for stage in ("stage1", "stage2"):
            files, loc = cloc([latest_crate(theory, stage) for theory in theories])
            rows.append({"suite": suite, "stage": stage, "crates": len(theories), "rust_files": files, "rust_loc": loc})
    target = args.output.open("w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    finally:
        if args.output: target.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr); sys.exit(1)
