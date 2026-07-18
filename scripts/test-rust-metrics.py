#!/usr/bin/env python3

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
SUITE_ROOTS = {
    "hol": REPO_ROOT / "test" / "HOL_Codegenerator",
    "unit": REPO_ROOT / "test" / "unit",
    "fpp": REPO_ROOT / "test" / "fpp",
}
HOL_KLOC_THEORIES = ("Generate", "Generate_Binary_Nat")
HOL_CLIPPY_THEORIES = ("Generate",)
EXPORT_CODE = re.compile(r"^\s*export_code(?:\s|$)", re.MULTILINE)
NATURAL_PART = re.compile(r"(\d+)")


def natural_key(path: Path):
    return [
        int(part) if part.isdigit() else part
        for part in NATURAL_PART.split(str(path).lower())
    ]


def current_theories(suite: str):
    theories = []
    for theory in sorted(SUITE_ROOTS[suite].rglob("*_Test.thy")):
        if EXPORT_CODE.search(theory.read_text(encoding="utf-8")):
            theories.append(theory)
    return theories


def artifact_root(theory: Path, stage: str):
    return theory.parent / stage / theory.stem


def latest_manifest(root: Path):
    manifests = [
        path
        for path in root.rglob("Cargo.toml")
        if "target" not in path.parts
    ]
    if not manifests:
        return None
    return sorted(manifests, key=lambda path: natural_key(path.relative_to(root)))[-1]


def manifests_for(suite: str, stage: str, command: str):
    manifests = []
    missing = []

    if suite == "hol":
        theory_names = HOL_KLOC_THEORIES if command == "kloc" else HOL_CLIPPY_THEORIES
        roots = [SUITE_ROOTS[suite] / stage / name for name in theory_names]
    else:
        roots = [artifact_root(theory, stage) for theory in current_theories(suite)]

    for root in roots:
        manifest = latest_manifest(root) if root.is_dir() else None
        if manifest is None:
            missing.append(root.relative_to(REPO_ROOT))
        else:
            manifests.append(manifest)

    if missing:
        lines = "\n".join(f"  - {path}" for path in missing)
        raise RuntimeError(
            f"Missing generated {stage} Cargo crates for {suite}:\n{lines}\n"
            "Run the corresponding generation/optimization targets first."
        )

    return manifests


def rust_files(manifest: Path):
    crate_root = manifest.parent
    return [
        path
        for path in crate_root.rglob("*.rs")
        if "target" not in path.relative_to(crate_root).parts
    ]


def physical_lines(path: Path):
    data = path.read_bytes()
    return data.count(b"\n") + int(bool(data) and not data.endswith(b"\n"))


def format_table(headers, rows, right_aligned_columns):
    rendered = [[str(cell) for cell in headers]] + [
        [str(cell) for cell in row] for row in rows
    ]
    widths = [max(len(row[index]) for row in rendered) for index in range(len(headers))]

    def divider():
        return "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def render(row):
        cells = []
        for index, cell in enumerate(row):
            if index in right_aligned_columns:
                cells.append(f" {cell:>{widths[index]}} ")
            else:
                cells.append(f" {cell:<{widths[index]}} ")
        return "|" + "|".join(cells) + "|"

    lines = [divider(), render(rendered[0]), divider()]
    lines.extend(render(row) for row in rendered[1:])
    lines.append(divider())
    return "\n".join(lines)


def run_kloc():
    counts = {}
    crate_counts = {}
    for stage in ("stage1", "stage2"):
        for suite in ("hol", "unit", "fpp"):
            manifests = manifests_for(suite, stage, "kloc")
            files = {
                path.resolve()
                for manifest in manifests
                for path in rust_files(manifest)
            }
            counts[(stage, suite)] = sum(physical_lines(path) for path in files)
            crate_counts[(stage, suite)] = len(manifests)

    rows = []
    for stage in ("stage1", "stage2"):
        rows.append(
            [stage, *(f"{counts[(stage, suite)]:,}" for suite in ("hol", "unit", "fpp"))]
        )

    print("Generated Rust LOC (physical lines; latest Cargo export per theory)")
    print(format_table(["Stage", "HOL", "Unit", "FPP"], rows, {1, 2, 3}))
    print(
        "Crates counted per stage: "
        + ", ".join(
            f"{suite.upper() if suite in ('hol', 'fpp') else suite.title()}="
            f"{crate_counts[('stage1', suite)]}"
            for suite in ("hol", "unit", "fpp")
        )
    )


def parse_warning_counts(output: str):
    counts = Counter()
    for line in output.splitlines():
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("reason") != "compiler-message":
            continue
        diagnostic = message.get("message", {})
        if diagnostic.get("level") != "warning":
            continue
        code = diagnostic.get("code")
        warning_type = code.get("code") if code else "uncoded warning"
        counts[warning_type] += 1
    return counts


def clippy_one(manifest: Path, cargo_command, cargo_jobs: int):
    command = [
        *cargo_command,
        "clippy",
        "--quiet",
        "--locked",
        "--color",
        "never",
        "--jobs",
        str(cargo_jobs),
        "--manifest-path",
        str(manifest),
        "--message-format=json",
        "--",
        "-W",
        "clippy::all",
    ]
    environment = os.environ.copy()
    environment["RUSTC_BOOTSTRAP"] = "1"
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return parse_warning_counts(result.stdout), result.returncode, result.stderr.strip()


def run_clippy(processes: int, cargo_jobs: int):
    cargo_command = shlex.split(os.environ.get("CARGO", "cargo"))
    suite_manifests = {
        (stage, suite): manifests_for(suite, stage, "clippy")
        for stage in ("stage1", "stage2")
        for suite in ("hol", "unit", "fpp")
    }
    stage_manifests = {
        stage: [
            manifest
            for suite in ("hol", "unit", "fpp")
            for manifest in suite_manifests[(stage, suite)]
        ]
        for stage in ("stage1", "stage2")
    }

    stage_counts = {"stage1": Counter(), "stage2": Counter()}
    failures = []
    jobs = [
        (stage, manifest)
        for stage in ("stage1", "stage2")
        for manifest in stage_manifests[stage]
    ]
    total = len(jobs)
    completed = 0

    print(
        f"Running cargo clippy on {total} generated crates "
        "(HOL excludes Generate_Binary_Nat)...",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=processes) as executor:
        future_jobs = {
            executor.submit(clippy_one, manifest, cargo_command, cargo_jobs): (stage, manifest)
            for stage, manifest in jobs
        }
        for future in as_completed(future_jobs):
            stage, manifest = future_jobs[future]
            counts, returncode, error = future.result()
            stage_counts[stage].update(counts)
            if returncode != 0:
                failures.append((stage, manifest, error))
            completed += 1
            if completed % 10 == 0 or completed == total:
                print(f"  checked {completed}/{total}", flush=True)

    warning_types = sorted(set(stage_counts["stage1"]) | set(stage_counts["stage2"]))
    rows = [
        [warning_type, stage_counts["stage1"][warning_type], stage_counts["stage2"][warning_type]]
        for warning_type in warning_types
    ]
    if not rows:
        rows.append(["(none)", 0, 0])
    rows.append(["Total", sum(stage_counts["stage1"].values()), sum(stage_counts["stage2"].values())])

    print("\nWarnings reported by cargo clippy (-W clippy::all; all suites combined)")
    print(format_table(["Warning type", "Stage 1", "Stage 2"], rows, {1, 2}))
    print(
        "Crates checked per stage: "
        + ", ".join(
            f"{suite.upper() if suite in ('hol', 'fpp') else suite.title()}="
            f"{len(suite_manifests[('stage1', suite)])}"
            for suite in ("hol", "unit", "fpp")
        )
        + f" ({len(stage_manifests['stage1'])} total)"
    )

    if failures:
        print("\nClippy failed for:", file=sys.stderr)
        for stage, manifest, error in failures:
            relative = manifest.relative_to(REPO_ROOT)
            print(f"  - {stage}: {relative}", file=sys.stderr)
            if error:
                print(f"    {error.splitlines()[-1]}", file=sys.stderr)
        return 1
    return 0


def positive_int(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def main():
    parser = argparse.ArgumentParser(description="Summarize generated Rust test artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("kloc", help="count generated Rust physical lines")
    clippy_parser = subparsers.add_parser("clippy", help="aggregate cargo clippy warnings")
    clippy_parser.add_argument(
        "--processes",
        type=positive_int,
        default=4,
        help="number of Cargo processes to run concurrently (default: 4)",
    )
    clippy_parser.add_argument(
        "--cargo-jobs",
        type=positive_int,
        default=1,
        help="jobs used inside each Cargo process (default: 1)",
    )
    args = parser.parse_args()

    try:
        if args.command == "kloc":
            run_kloc()
            return 0
        return run_clippy(args.processes, args.cargo_jobs)
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
