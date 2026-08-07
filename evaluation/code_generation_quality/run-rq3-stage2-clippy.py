#!/usr/bin/env python3
"""Freeze the tracked Stage-2 Clippy corpus and its residual diagnostics."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from datetime import datetime


REPO = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent / "rq3-stage2-clippy-final"
SHARED_LOCK = REPO / "scripts" / "isabelle-exported.Cargo.lock"
LOCK_HELPER = REPO / "scripts" / "ensure-cargo-lock.py"
EXPORT_CODE = re.compile(r"^\s*export_code(?:\s|$)", re.MULTILINE)
NATURAL_PART = re.compile(r"(\d+)")
EXPECTED_SUITES = {"HOL": 1, "Unit": 55, "FPP": 36}


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


def natural_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part
        for part in NATURAL_PART.split(str(path).lower())
    ]


def tracked_theories() -> list[tuple[str, Path]]:
    result = run(["git", "ls-files"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    tracked = [REPO / line for line in result.stdout.splitlines()]

    selected: list[tuple[str, Path]] = []
    hol = REPO / "test" / "HOL_Codegenerator" / "Generate.thy"
    if hol not in tracked:
        raise RuntimeError(f"tracked HOL theory not found: {hol}")
    selected.append(("HOL", hol))

    for suite, prefix in (("Unit", "test/unit/"), ("FPP", "test/fpp/")):
        theories = sorted(
            (
                path
                for path in tracked
                if path.relative_to(REPO).as_posix().startswith(prefix)
                and path.name.endswith("_Test.thy")
                and EXPORT_CODE.search(path.read_text(encoding="utf-8"))
            ),
            key=natural_key,
        )
        selected.extend((suite, theory) for theory in theories)
    return selected


def latest_manifest(theory: Path) -> Path:
    root = theory.parent / "stage2" / theory.stem
    manifests = [
        path
        for path in root.rglob("Cargo.toml")
        if "target" not in path.relative_to(root).parts
    ]
    if not manifests:
        raise RuntimeError(f"missing Stage-2 crate for {theory.relative_to(REPO)}")
    return sorted(manifests, key=lambda path: natural_key(path.relative_to(root)))[-1]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def crate_files(manifest: Path) -> list[Path]:
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
    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def crate_tree_hash(manifest: Path) -> tuple[str, int]:
    root = manifest.parent
    digest = hashlib.sha256()
    files = crate_files(manifest)
    for path in files:
        relative = path.relative_to(root).as_posix().encode()
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest(), len(files)


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


def audit_one(suite: str, theory: Path, manifest: Path) -> dict[str, object]:
    environment = os.environ.copy()
    environment["RUSTC_BOOTSTRAP"] = "1"
    locked = run(
        [sys.executable, str(LOCK_HELPER), str(manifest), str(SHARED_LOCK)],
        env=environment,
    )
    if locked.returncode != 0:
        return {
            "suite": suite,
            "theory": theory,
            "manifest": manifest,
            "exit_status": locked.returncode,
            "error": locked.stderr.strip() or locked.stdout.strip(),
            "diagnostics": [],
        }

    command = [
        "cargo",
        "+stable",
        "clippy",
        "--quiet",
        "--locked",
        "--color",
        "never",
        "--jobs",
        "1",
        "--manifest-path",
        str(manifest),
        "--message-format=json",
        "--",
        "-W",
        "clippy::all",
    ]
    result = run(command, env=environment)
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
    tree_hash, source_files = crate_tree_hash(manifest)
    return {
        "suite": suite,
        "theory": theory,
        "manifest": manifest,
        "tree_hash": tree_hash,
        "source_files": source_files,
        "exit_status": result.returncode,
        "error": result.stderr.strip(),
        "diagnostics": diagnostics,
        "command": shlex.join(command),
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    theories = tracked_theories()
    suite_counts = Counter(suite for suite, _ in theories)
    if dict(suite_counts) != EXPECTED_SUITES:
        raise RuntimeError(f"unexpected tracked corpus: {dict(suite_counts)}")

    jobs = [(suite, theory, latest_manifest(theory)) for suite, theory in theories]
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        pending = {
            executor.submit(audit_one, suite, theory, manifest): (suite, theory)
            for suite, theory, manifest in jobs
        }
        for future in as_completed(pending):
            results.append(future.result())
    results.sort(key=lambda item: (list(EXPECTED_SUITES).index(item["suite"]), natural_key(item["theory"])))

    OUTPUT.mkdir(parents=True, exist_ok=True)
    corpus_rows = []
    diagnostic_rows = []
    commands = []
    for item in results:
        manifest = item["manifest"]
        theory = item["theory"]
        diagnostics = item["diagnostics"]
        corpus_rows.append(
            {
                "suite": item["suite"],
                "theory": theory.relative_to(REPO).as_posix(),
                "manifest": manifest.relative_to(REPO).as_posix(),
                "crate_tree_sha256": item.get("tree_hash", ""),
                "hashed_files": item.get("source_files", ""),
                "clippy_exit_status": item["exit_status"],
                "diagnostic_count": len(diagnostics),
            }
        )
        if item.get("command"):
            commands.append(item["command"])
        for diagnostic in diagnostics:
            diagnostic_rows.append(
                {
                    "suite": item["suite"],
                    "theory": theory.relative_to(REPO).as_posix(),
                    "manifest": manifest.relative_to(REPO).as_posix(),
                    **diagnostic,
                }
            )

    failures = [item for item in results if item["exit_status"] != 0]
    warning_counts = Counter(row["lint"] for row in diagnostic_rows)
    summary_rows = [
        {"kind": "corpus", "name": f"{suite} crates", "count": suite_counts[suite]}
        for suite in EXPECTED_SUITES
    ]
    summary_rows.extend(
        [
            {"kind": "corpus", "name": "Stage-2 crates", "count": len(results)},
            {"kind": "run", "name": "failed crates", "count": len(failures)},
        ]
    )
    summary_rows.extend(
        {"kind": "diagnostic", "name": name, "count": count}
        for name, count in sorted(warning_counts.items())
    )
    summary_rows.append(
        {"kind": "diagnostic", "name": "Total", "count": sum(warning_counts.values())}
    )

    corpus_path = OUTPUT / "rq3-stage2-clippy-corpus.csv"
    write_csv(
        corpus_path,
        [
            "suite",
            "theory",
            "manifest",
            "crate_tree_sha256",
            "hashed_files",
            "clippy_exit_status",
            "diagnostic_count",
        ],
        corpus_rows,
    )
    write_csv(
        OUTPUT / "rq3-stage2-clippy-diagnostics.csv",
        ["suite", "theory", "manifest", "lint", "file", "line", "column", "message"],
        diagnostic_rows,
    )
    write_csv(OUTPUT / "rq3-stage2-clippy-summary.csv", ["kind", "name", "count"], summary_rows)
    (OUTPUT / "commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")

    git_commit = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    git_status = run(["git", "status", "--short"]).stdout
    (OUTPUT / "git-status.txt").write_text(git_status, encoding="utf-8")
    metadata = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": git_commit,
        "git_status_sha256": sha256_bytes(git_status.encode()),
        "rustc": run(["rustc", "+stable", "-Vv"]).stdout.strip(),
        "cargo": run(["cargo", "+stable", "-V"]).stdout.strip(),
        "clippy": run(["cargo", "+stable", "clippy", "-V"]).stdout.strip(),
        "selection": "tracked export_code theories only; HOL Generate plus Unit and FPP",
        "excluded_untracked_scope": "test/unit/example",
        "stage1_policy": "not executed; the accepted Stage-1 baseline is reused",
        "corpus_csv_sha256": sha256_file(corpus_path),
        "expected_suite_counts": EXPECTED_SUITES,
    }
    (OUTPUT / "environment.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    record = f"""# Final RQ3 Stage-2 Clippy record

- Scope: tracked generated Stage-2 crates only. Stage-1 was not executed.
- Corpus: {len(results)} crates, comprising {suite_counts['HOL']} HOL, {suite_counts['Unit']} Unit, and {suite_counts['FPP']} FPP crates.
- Toolchain: {metadata['clippy']}.
- Result: {sum(warning_counts.values())} diagnostics and {len(failures)} failed Clippy commands.
- Untracked theories under `test/unit/example` are outside the frozen corpus.
- Each crate hash covers `Cargo.toml`, `Cargo.lock`, and non-target Rust source files using length-delimited relative paths and contents.

## Residual diagnostics

| Diagnostic | Count |
| --- | ---: |
"""
    record += "".join(f"| `{name}` | {count} |\n" for name, count in sorted(warning_counts.items()))
    record += f"| **Total** | **{sum(warning_counts.values())}** |\n"
    (OUTPUT / "experiment-record.md").write_text(record, encoding="utf-8")

    if failures:
        for item in failures:
            print(f"FAILED {item['manifest']}: {item['error']}", file=sys.stderr)
        return 1
    expected_warnings = {
        "clippy::overly_complex_bool_expr": 1,
        "clippy::too_many_arguments": 2,
        "clippy::type_complexity": 4,
        "unconditional_recursion": 9,
    }
    if dict(warning_counts) != expected_warnings:
        print(f"unexpected diagnostics: {dict(warning_counts)}", file=sys.stderr)
        return 1
    print(f"Recorded {len(results)} Stage-2 crates and {sum(warning_counts.values())} diagnostics in {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
