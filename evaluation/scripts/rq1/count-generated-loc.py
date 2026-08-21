#!/usr/bin/env python3
"""Count generated Rust LOC for the frozen RQ1 Stage-1/Stage-2 corpus.

Only ``src/**/*.rs`` files from Isabelle-exported library crates are counted.
The script rejects binary drivers, Rust tests, benchmarks, examples, and build
scripts so a hand-written harness cannot silently enter the paper's KLOC.
``cloc`` supplies the code count and therefore excludes comments and blank
lines.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXPORT_CODE = re.compile(r"^\s*export_code(?:\s|$)", re.MULTILINE)
NATURAL = re.compile(r"(\d+)")
RUST_TEST = re.compile(
    r"#\s*!?\s*\[\s*(?:test|cfg\s*\(\s*test\s*\))\s*\]",
    re.MULTILINE,
)
EXPECTED_SUITES = {
    "HCT-standard": 1,
    "HCT-binary-nat": 1,
    "Unit": 53,
    "FPP": 36,
}


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


def generated_crate(theory: Path, stage: str) -> Path:
    root = theory.parent / stage / theory.stem
    manifests = [p for p in root.rglob("Cargo.toml") if "target" not in p.relative_to(root).parts]
    if len(manifests) != 1:
        raise RuntimeError(
            f"expected exactly one {stage} crate for {theory.relative_to(REPO)}, "
            f"found {len(manifests)}"
        )
    return manifests[0].parent


def cloc(roots: list[Path]) -> tuple[int, int]:
    sources: list[Path] = []
    forbidden_names = ("build.rs",)
    forbidden_dirs = ("benches", "examples", "test", "tests")
    for root in roots:
        if any((root / name).exists() for name in forbidden_names + forbidden_dirs):
            raise RuntimeError(f"non-generated test/harness path present in {root}")
        if (root / "src" / "main.rs").exists():
            raise RuntimeError(f"binary driver present in generated RQ1 crate: {root / 'src/main.rs'}")
        crate_sources = sorted((root / "src").rglob("*.rs"))
        if not crate_sources:
            raise RuntimeError(f"no generated Rust sources under {root / 'src'}")
        for source in crate_sources:
            if RUST_TEST.search(source.read_text(encoding="utf-8", errors="replace")):
                raise RuntimeError(f"Rust test item present in generated RQ1 source: {source}")
        sources.extend(crate_sources)

    command = [
        "cloc", "--json", "--quiet", "--skip-uniqueness", "--include-lang=Rust",
        *map(str, sources),
    ]
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
    actual = {suite: len(theories) for suite, theories in suites.items()}
    if actual != EXPECTED_SUITES:
        raise RuntimeError(f"RQ1 corpus mismatch: expected {EXPECTED_SUITES}, found {actual}")
    rows = []
    for suite, theories in suites.items():
        for stage in ("stage1", "stage2"):
            files, loc = cloc([generated_crate(theory, stage) for theory in theories])
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
