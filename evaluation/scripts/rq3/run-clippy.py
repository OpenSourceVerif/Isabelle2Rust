#!/usr/bin/env python3
"""Record the RQ3 Clippy comparison for generated Stage-1/Stage-2 crates."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


REPO = Path(__file__).resolve().parents[3]
WORK = REPO / "evaluation" / ".work" / "rq3" / "code-quality"
SHARED_LOCK = REPO / "scripts" / "isabelle-exported.Cargo.lock"
LOCK_HELPER = REPO / "scripts" / "ensure-cargo-lock.py"
EXPORT_CODE = re.compile(r"^\s*export_code(?:\s|$)", re.MULTILINE)
NATURAL_PART = re.compile(r"(\d+)")
STAGES = ("stage1", "stage2")
EXPECTED_TEST_SUITES = {"HOL": 1, "Unit": 53, "FPP": 36}
CASE_STUDIES = {
    "SBPF-program": {
        "stage1": "test/sbpf/theory/stage1/bpf_generator_checked128/interp_test/Cargo.toml",
        "stage2": "test/sbpf/theory/stage2/bpf_generator_checked128/interp_test/Cargo.toml",
    },
    "SBPF-instruction": {
        "stage1": "test/sbpf/theory/stage1/bpf_generator_checked128/step_test/Cargo.toml",
        "stage2": "test/sbpf/theory/stage2/bpf_generator_checked128/step_test/Cargo.toml",
    },
    "X64-stepper": {
        "stage1": "test/x64/theory/stage1/x64_generator_checked128/x64_step_test/Cargo.toml",
        "stage2": "test/x64/theory/stage2/x64_generator_checked128/x64_step_test/Cargo.toml",
    },
}
EXPECTED_ALL_DIAGNOSTICS = {
    "clippy::clone_on_copy": (3960, 0),
    "clippy::collapsible_match": (122, 0),
    "clippy::double_parens": (413, 0),
    "clippy::match_single_binding": (219, 0),
    "clippy::needless_bool": (2, 0),
    "clippy::nonminimal_bool": (19, 0),
    "clippy::overly_complex_bool_expr": (1, 1),
    "clippy::too_many_arguments": (13, 13),
    "clippy::type_complexity": (1142, 4),
    "unconditional_recursion": (9, 9),
}


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        **kwargs,
    )


def natural_key(value: str | Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part
        for part in NATURAL_PART.split(str(value).lower())
    ]


def tracked_theories() -> list[tuple[str, Path]]:
    tracked = run(["git", "ls-files", "--", "test/HOL_Codegenerator", "test/unit", "test/fpp"])
    if tracked.returncode != 0:
        raise RuntimeError(tracked.stderr.strip())

    paths = [REPO / relative for relative in tracked.stdout.splitlines()]
    selected: list[tuple[str, Path]] = []
    hol = REPO / "test" / "HOL_Codegenerator" / "Generate.thy"
    if hol not in paths:
        raise RuntimeError(f"tracked HOL theory not found: {hol}")
    selected.append(("HOL", hol))

    for suite, prefix in (("Unit", "test/unit/"), ("FPP", "test/fpp/")):
        theories = sorted(
            (
                path
                for path in paths
                if path.relative_to(REPO).as_posix().startswith(prefix)
                and path.name.endswith("_Test.thy")
                and EXPORT_CODE.search(path.read_text(encoding="utf-8"))
            ),
            key=natural_key,
        )
        selected.extend((suite, theory) for theory in theories)

    counts = Counter(suite for suite, _ in selected)
    if dict(counts) != EXPECTED_TEST_SUITES:
        raise RuntimeError(
            f"unexpected tracked test corpus: expected {EXPECTED_TEST_SUITES}, found {dict(counts)}"
        )
    return selected


def latest_manifest(theory: Path, stage: str) -> Path:
    root = theory.parent / stage / theory.stem
    manifests = [
        path
        for path in root.rglob("Cargo.toml")
        if "target" not in path.relative_to(root).parts
    ]
    if not manifests:
        raise RuntimeError(f"missing {stage} crate for {theory.relative_to(REPO)}")
    return sorted(manifests, key=lambda path: natural_key(path.relative_to(root)))[-1]


def selected_jobs(scope: str) -> list[tuple[str, str, str, Path]]:
    jobs: list[tuple[str, str, str, Path]] = []
    if scope in ("test-suites", "all"):
        for suite, theory in tracked_theories():
            source = theory.relative_to(REPO).as_posix()
            for stage in STAGES:
                jobs.append((suite, source, stage, latest_manifest(theory, stage)))
    if scope in ("case-studies", "all"):
        for workload, stages in CASE_STUDIES.items():
            for stage in STAGES:
                manifest = REPO / stages[stage]
                if not manifest.is_file():
                    raise RuntimeError(f"missing {stage} crate for {workload}: {manifest}")
                jobs.append((workload, workload, stage, manifest))
    return jobs


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def crate_tree_hash(manifest: Path) -> tuple[str, int]:
    root = manifest.parent
    files = [manifest]
    lock = root / "Cargo.lock"
    if lock.is_file():
        files.append(lock)
    files.extend(
        path
        for path in root.rglob("*.rs")
        if "target" not in path.relative_to(root).parts
    )
    digest = hashlib.sha256()
    unique_files = sorted(set(files), key=lambda path: path.relative_to(root).as_posix())
    for path in unique_files:
        relative = path.relative_to(root).as_posix().encode()
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest(), len(unique_files)


def normalize_span_path(name: str, manifest: Path) -> str:
    path = Path(name)
    candidates = [path] if path.is_absolute() else [REPO / path, manifest.parent / path]
    for candidate in candidates:
        if candidate.exists():
            try:
                return candidate.resolve().relative_to(REPO).as_posix()
            except ValueError:
                return candidate.resolve().as_posix()
    return name


def audit_one(
    group: str, source: str, stage: str, manifest: Path, cargo_jobs: int
) -> dict[str, object]:
    environment = os.environ.copy()
    environment.pop("RUSTC_BOOTSTRAP", None)
    locked = run(
        [sys.executable, str(LOCK_HELPER), str(manifest), str(SHARED_LOCK)],
        env=environment,
    )
    if locked.returncode != 0:
        return {
            "group": group,
            "source": source,
            "stage": stage,
            "manifest": manifest,
            "exit_status": locked.returncode,
            "error": locked.stderr.strip() or locked.stdout.strip(),
            "diagnostics": [],
        }

    result = run(
        [
            "cargo", "+stable", "clippy", "--quiet", "--locked", "--color", "never",
            "--jobs", str(cargo_jobs), "--manifest-path", str(manifest), "--message-format=json",
            "--", "-W", "clippy::all",
        ],
        env=environment,
    )
    diagnostics = []
    for line in result.stdout.splitlines():
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("reason") != "compiler-message":
            continue
        diagnostic = message.get("message", {})
        if diagnostic.get("level") != "warning":
            continue
        code = diagnostic.get("code") or {}
        spans = diagnostic.get("spans") or []
        span = next((item for item in spans if item.get("is_primary")), spans[0] if spans else {})
        diagnostics.append(
            {
                "lint": code.get("code", "uncoded warning"),
                "file": normalize_span_path(span.get("file_name", ""), manifest),
                "line": span.get("line_start", ""),
                "column": span.get("column_start", ""),
                "message": diagnostic.get("message", ""),
            }
        )
    tree_hash, hashed_files = crate_tree_hash(manifest)
    return {
        "group": group,
        "source": source,
        "stage": stage,
        "manifest": manifest,
        "tree_hash": tree_hash,
        "hashed_files": hashed_files,
        "exit_status": result.returncode,
        "error": result.stderr.strip(),
        "diagnostics": diagnostics,
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope", choices=("test-suites", "case-studies", "all"), default="all"
    )
    parser.add_argument("--processes", type=positive_int, default=4)
    parser.add_argument("--cargo-jobs", type=positive_int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = (args.output or (WORK / args.scope)).resolve()

    try:
        jobs = selected_jobs(args.scope)
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    results = []
    with ThreadPoolExecutor(max_workers=args.processes) as executor:
        pending = {
            executor.submit(audit_one, *job, args.cargo_jobs): job for job in jobs
        }
        for completed, future in enumerate(as_completed(pending), start=1):
            results.append(future.result())
            if completed % 10 == 0 or completed == len(jobs):
                print(f"  checked {completed}/{len(jobs)}", flush=True)

    group_order = [*EXPECTED_TEST_SUITES, *CASE_STUDIES]
    results.sort(
        key=lambda item: (
            STAGES.index(str(item["stage"])),
            group_order.index(str(item["group"])),
            natural_key(str(item["source"])),
        )
    )
    corpus_rows = []
    diagnostic_rows = []
    for item in results:
        manifest = item["manifest"]
        diagnostics = item["diagnostics"]
        corpus_rows.append(
            {
                "stage": item["stage"],
                "group": item["group"],
                "source": item["source"],
                "manifest": manifest.relative_to(REPO).as_posix(),
                "crate_tree_sha256": item.get("tree_hash", ""),
                "hashed_files": item.get("hashed_files", ""),
                "clippy_exit_status": item["exit_status"],
                "diagnostic_count": len(diagnostics),
            }
        )
        for diagnostic in diagnostics:
            diagnostic_rows.append(
                {
                    "stage": item["stage"],
                    "group": item["group"],
                    "source": item["source"],
                    "manifest": manifest.relative_to(REPO).as_posix(),
                    **diagnostic,
                }
            )

    failures = [item for item in results if item["exit_status"] != 0]
    warning_counts = {
        stage: Counter(
            row["lint"] for row in diagnostic_rows if row["stage"] == stage
        )
        for stage in STAGES
    }
    warning_types = sorted(set(warning_counts["stage1"]) | set(warning_counts["stage2"]))
    summary_rows = []
    for lint in warning_types:
        stage1 = warning_counts["stage1"][lint]
        stage2 = warning_counts["stage2"][lint]
        reduction = "" if stage1 == 0 else f"{(stage1 - stage2) / stage1 * 100:.1f}"
        summary_rows.append(
            {"lint": lint, "stage1": stage1, "stage2": stage2, "reduction_percent": reduction}
        )
    totals = (sum(warning_counts["stage1"].values()), sum(warning_counts["stage2"].values()))
    summary_rows.append(
        {
            "lint": "Total",
            "stage1": totals[0],
            "stage2": totals[1],
            "reduction_percent": f"{(totals[0] - totals[1]) / totals[0] * 100:.1f}",
        }
    )

    by_scope_rows = []
    for group in group_order:
        group_items = [item for item in results if item["group"] == group]
        if not group_items:
            continue
        for stage in STAGES:
            stage_items = [item for item in group_items if item["stage"] == stage]
            by_scope_rows.append(
                {
                    "group": group,
                    "stage": stage,
                    "crates": len(stage_items),
                    "failed_crates": sum(item["exit_status"] != 0 for item in stage_items),
                    "diagnostics": sum(len(item["diagnostics"]) for item in stage_items),
                }
            )

    corpus_path = output / "corpus.csv"
    write_csv(
        corpus_path,
        ["stage", "group", "source", "manifest", "crate_tree_sha256", "hashed_files", "clippy_exit_status", "diagnostic_count"],
        corpus_rows,
    )
    write_csv(
        output / "diagnostics.csv",
        ["stage", "group", "source", "manifest", "lint", "file", "line", "column", "message"],
        diagnostic_rows,
    )
    write_csv(output / "summary.csv", ["lint", "stage1", "stage2", "reduction_percent"], summary_rows)
    write_csv(output / "by-scope.csv", ["group", "stage", "crates", "failed_crates", "diagnostics"], by_scope_rows)

    git_status = run(["git", "status", "--short"]).stdout
    metadata = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": run(["git", "rev-parse", "HEAD"]).stdout.strip(),
        "git_clean": not bool(git_status),
        "git_status_sha256": sha256_bytes(git_status.encode()),
        "rustc": run(["rustc", "+stable", "-Vv"]).stdout.strip(),
        "cargo": run(["cargo", "+stable", "-V"]).stdout.strip(),
        "clippy": run(["cargo", "+stable", "clippy", "-V"]).stdout.strip(),
        "scope": args.scope,
        "stages": list(STAGES),
        "crate_counts": {stage: sum(row["stage"] == stage for row in corpus_rows) for stage in STAGES},
        "corpus_csv_sha256": sha256_file(corpus_path),
    }
    (output / "environment.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if failures:
        for item in failures:
            print(f"FAILED {item['manifest']}: {item['error']}", file=sys.stderr)
        return 1
    if args.scope == "all":
        observed = {
            lint: (warning_counts["stage1"][lint], warning_counts["stage2"][lint])
            for lint in warning_types
        }
        if observed != EXPECTED_ALL_DIAGNOSTICS:
            print(f"unexpected diagnostics: {observed}", file=sys.stderr)
            return 1
    print(
        f"Recorded {len(results) // 2} crate pairs and {totals[0]} -> {totals[1]} diagnostics in {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
