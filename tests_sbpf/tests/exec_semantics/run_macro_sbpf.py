#!/usr/bin/env python3
"""Shared SBPF macro-validation orchestration.

This script owns only the language-independent path:
  1. ensure the BigInt profile is exported from Isabelle,
  2. refresh the local macro-test JSON data derived from sbpf_ocaml/test.ml,
  3. run the OCaml and Rust language-specific macro runners,
  4. print one combined statistical summary.
"""

from __future__ import annotations

import os
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StageResult:
    name: str
    passed: int | None
    failed: int | None
    rc: int
    note: str = ""

    @property
    def total(self) -> int | None:
        if self.passed is None or self.failed is None:
            return None
        return self.passed + self.failed


ROOT = Path(__file__).resolve().parents[3]
EXEC_DIR = ROOT / "tests_sbpf" / "tests" / "exec_semantics"
DATA_DIR = ROOT / "tests_sbpf" / "tests" / "data"
THEORY = os.environ.get("SBPF_THEORY") or "bpf_generator_bigint"
EXPORT_DIR = Path(
    os.environ.get("SBPF_EXPORT_DIR")
    or ROOT / "tests_sbpf" / "theory" / "stage1" / THEORY
)
if not EXPORT_DIR.is_absolute():
    EXPORT_DIR = ROOT / EXPORT_DIR
OCAML_EXPORT_DIR = ROOT / "tests_sbpf" / "theory" / "stage1" / "bpf_generator_bigint"
TEST_ML = EXEC_DIR / "sbpf_ocaml" / "test.ml"
INTERP_JSON = DATA_DIR / "interp_in.json"
SHARED_BUILD_DIR = EXEC_DIR / "_build"
INTERP_JSON_STAMP = SHARED_BUILD_DIR / "interp_in_cache.json"
DATA_GENERATOR_VERSION = "interp-json-v1"

OCAML_RUNNER = EXEC_DIR / "sbpf_ocaml" / "run_interp_macro.py"
RUST_RUNNER = EXEC_DIR / "sbpf_rust" / "run_interp_macro.py"

PASSED_RE = re.compile(r"Passed:\s*(\d+)")
FAILED_RE = re.compile(r"Failed:\s*(\d+)")
FAILED_NOTE_RE = re.compile(r"Failed:\s*\d+\s*\(of which ([^)]+)\)")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def announce(title: str, detail: str) -> None:
    print(f">>> [macro_sbpf] {title}: {detail}", flush=True)


def run_command(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        output.append(line)
        print(line, end="")
    rc = proc.wait()
    return rc, "".join(output)


def parse_summary(name: str, rc: int, output: str, note: str = "") -> StageResult:
    passed_match = PASSED_RE.findall(output)
    failed_match = FAILED_RE.findall(output)
    if not passed_match or not failed_match:
        return StageResult(name, None, None, rc, note or "no summary found")
    failed_note = FAILED_NOTE_RE.findall(output)
    if failed_note and not note:
        note = failed_note[-1]
    return StageResult(name, int(passed_match[-1]), int(failed_match[-1]), rc, note)


def export_outputs() -> list[Path]:
    return [
        OCAML_EXPORT_DIR / "interp_test.ocaml",
        EXPORT_DIR / "interp_test" / "Cargo.toml",
    ]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def interp_json_cache_key() -> dict[str, str]:
    return {
        "generator_version": DATA_GENERATOR_VERSION,
        "test_ml_sha256": file_sha256(TEST_ML),
    }


def interp_json_cache_is_valid(key: dict[str, str]) -> bool:
    if os.environ.get("REBUILD") == "1" or os.environ.get("DATA_REBUILD") == "1":
        return False
    if not INTERP_JSON.exists() or not INTERP_JSON_STAMP.exists():
        return False
    try:
        return json.loads(INTERP_JSON_STAMP.read_text(encoding="utf-8")) == key
    except json.JSONDecodeError:
        return False


def ensure_isabelle_export() -> bool:
    missing = [path for path in export_outputs() if not path.exists()]
    missing_ocaml = OCAML_EXPORT_DIR / "interp_test.ocaml" in missing
    if missing_ocaml:
        print(
            "ERROR: missing fixed OCaml baseline export: "
            f"{rel(OCAML_EXPORT_DIR / 'interp_test.ocaml')}"
        )
        return False

    force_rebuild = os.environ.get("REBUILD") == "1"
    if not missing and not force_rebuild:
        announce("Isabelle export", f"reusing {rel(EXPORT_DIR)}")
        return True

    reason = "REBUILD=1" if force_rebuild else "missing " + ", ".join(rel(p) for p in missing)
    announce("Isabelle export", f"building {THEORY} ({reason})")
    rc, _ = run_command(
        ["make", "build", "TEST_DIR=tests_sbpf/theory", f"TEST_THEORY={THEORY}"],
        cwd=ROOT,
    )
    if rc != 0:
        return False

    missing_after = [path for path in export_outputs() if not path.exists()]
    if missing_after:
        for path in missing_after:
            print(f"ERROR: expected Isabelle export not found: {rel(path)}")
        return False
    return True


def refresh_interp_json() -> bool:
    key = interp_json_cache_key()
    if interp_json_cache_is_valid(key):
        announce("shared data", f"reusing {rel(INTERP_JSON)} from cached sbpf_ocaml/test.ml")
        return True

    announce("shared data", f"refreshing {rel(INTERP_JSON)} from sbpf_ocaml/test.ml")
    rc, _ = run_command(["python3", str(EXEC_DIR / "gen_interp_json.py")], cwd=ROOT)
    if rc != 0:
        return False
    SHARED_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    INTERP_JSON_STAMP.write_text(json.dumps(key, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def run_stage(name: str, script: Path, export_dir: Path) -> StageResult:
    env = os.environ.copy()
    env.pop("RUSTC_BOOTSTRAP", None)
    env["SBPF_ROOT"] = str(ROOT)
    env["SBPF_EXEC_DIR"] = str(EXEC_DIR)
    env["SBPF_DATA_DIR"] = str(DATA_DIR)
    env["SBPF_EXPORT_DIR"] = str(export_dir)

    announce(name, f"running {rel(script)}")
    rc, output = run_command(["python3", str(script)], cwd=ROOT, env=env)
    return parse_summary(name, rc, output)


def print_final_summary(results: list[StageResult]) -> None:
    print("\n========================================")
    print("macro_sbpf summary")
    for result in results:
        if result.total is None:
            detail = f"no summary (exit {result.rc})"
            if result.note:
                detail += f", {result.note}"
            print(f"  {result.name}: {detail}")
        else:
            detail = (
                f"  {result.name}: Passed {result.passed} / "
                f"Failed {result.failed} / Total {result.total}"
            )
            if result.note:
                detail += f" ({result.note})"
            print(detail)

    failed_cases = sum(result.failed or 0 for result in results)
    infra_failed = any(result.total is None or result.rc not in (0, 1) for result in results)
    print("  Overall: PASS" if failed_cases == 0 and not infra_failed else "  Overall: FAIL")


def main() -> int:
    if not ensure_isabelle_export():
        print_final_summary([StageResult("Isabelle export", None, None, 1, "generation failed")])
        return 1

    if not refresh_interp_json():
        print_final_summary([StageResult("shared data", None, None, 1, "interp JSON failed")])
        return 1

    results = [
        run_stage("OCaml export", OCAML_RUNNER, OCAML_EXPORT_DIR),
        run_stage("Rust export", RUST_RUNNER, EXPORT_DIR),
    ]
    print_final_summary(results)

    for result in results:
        if result.total is None:
            return 1
        if result.failed:
            return 1
        if result.rc not in (0, 1):
            return result.rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
