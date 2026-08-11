#!/usr/bin/env python3
"""Run the Rust SBPF interpreter macro test from Isabelle-generated code."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(os.environ.get("SBPF_ROOT", Path(__file__).resolve().parents[4]))
EXEC_DIR = Path(os.environ.get("SBPF_EXEC_DIR", ROOT / "tests_sbpf" / "tests" / "exec_semantics"))
DATA_DIR = Path(os.environ.get("SBPF_DATA_DIR", ROOT / "tests_sbpf" / "tests" / "data"))
EXPORT_DIR = Path(os.environ.get("SBPF_EXPORT_DIR", ROOT / "tests_sbpf" / "theory" / "stage1" / "bpf_generator"))
RUST_DIR = EXEC_DIR / "sbpf_rust"

RUST_TOOLCHAIN = os.environ.get("RUST_TOOLCHAIN", "stable")
GLUE_VERSION = "interp-macro-rust-stable-v1"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def announce(title: str, detail: str) -> None:
    print(f">>> [sbpf_rust] {title}: {detail}", flush=True)


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


def run_captured(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float | None,
) -> tuple[int | None, str]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return completed.returncode, completed.stdout
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        return None, output


def cargo_command() -> list[str]:
    raw = os.environ.get("CARGO", "cargo")
    cmd = shlex.split(raw)
    if cmd == ["cargo"] and RUST_TOOLCHAIN:
        return ["cargo", f"+{RUST_TOOLCHAIN}"]
    return cmd


def check_rust_environment(cargo: list[str]) -> bool:
    rc, output = run_command(cargo + ["--version"], cwd=ROOT)
    if rc != 0:
        return False
    announce("Rust toolchain", output.strip())
    if RUST_TOOLCHAIN and f"+{RUST_TOOLCHAIN}" not in " ".join(cargo):
        announce("Rust toolchain", f"using explicit CARGO={shlex.join(cargo)}")
    return True


def rust_case_timeout() -> float | None:
    raw = os.environ.get("RUST_CASE_TIMEOUT", "").strip()
    if not raw:
        return None
    timeout = float(raw)
    if timeout <= 0:
        return None
    return timeout


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_key(export_rs: Path, glue_rs: Path) -> dict[str, str]:
    return {
        "rust_toolchain": RUST_TOOLCHAIN,
        "glue_version": GLUE_VERSION,
        "sbpf_stage": os.environ.get("SBPF_STAGE", "1"),
        "sbpf_no_bigint": os.environ.get("SBPF_NO_BIGINT", "0"),
        "sbpf_native_int": os.environ.get("SBPF_NATIVE_INT", "0"),
        "export_rs_sha256": file_sha256(export_rs),
        "glue_rs_sha256": file_sha256(glue_rs),
    }


def cache_is_valid(pkg_dir: Path, key: dict[str, str]) -> bool:
    stamp = pkg_dir / ".rust_macro_cache.json"
    binary = pkg_dir / "target" / "release" / "isabelle_exported"
    if os.environ.get("REBUILD") == "1":
        return False
    if not stamp.exists() or not binary.exists():
        return False
    try:
        return json.loads(stamp.read_text(encoding="utf-8")) == key
    except json.JSONDecodeError:
        return False


def prepare_rust_cargo(toml: Path) -> None:
    text = toml.read_text(encoding="utf-8")
    cleaned = re.sub(r"(?m)^serde(_json)?\s*=.*\n?", "", text)
    if cleaned != text:
        toml.write_text(cleaned, encoding="utf-8")

    lock_src = ROOT / "scripts" / "isabelle-exported.Cargo.lock"
    lock_dst = toml.parent / "Cargo.lock"
    if lock_src.exists():
        shutil.copy2(lock_src, lock_dst)


def main() -> int:
    if os.environ.get("SBPF_NO_BIGINT") == "1" and os.environ.get("SBPF_NATIVE_INT") == "1":
        print("ERROR: SBPF_NO_BIGINT=1 and SBPF_NATIVE_INT=1 are mutually exclusive")
        return 2

    toml = EXPORT_DIR / "interp_test" / "Cargo.toml"
    if not toml.exists():
        print(f"ERROR: missing Isabelle Rust export: {rel(toml)}")
        return 2

    cargo = cargo_command()
    if not check_rust_environment(cargo):
        return 2

    pkg_dir = toml.parent
    export_rs = pkg_dir / "src" / "Interp_test.rs"
    main_rs = RUST_DIR / "interp_main.rs"

    if not export_rs.exists():
        print(f"ERROR: missing Isabelle Rust export: {rel(export_rs)}")
        return 2

    key = cache_key(export_rs, main_rs)

    env = os.environ.copy()
    env.pop("RUSTC_BOOTSTRAP", None)
    env["CROSS_JSON"] = str(DATA_DIR / "interp_in.json")
    env["RUSTFLAGS"] = "-Awarnings"
    if os.environ.get("SBPF_STAGE") == "2":
        env["RUSTFLAGS"] += " --cfg sbpf_stage2"
    if os.environ.get("SBPF_NO_BIGINT") == "1":
        env["RUSTFLAGS"] += " --cfg sbpf_no_bigint"
    if os.environ.get("SBPF_NATIVE_INT") == "1":
        env["RUSTFLAGS"] += " --cfg sbpf_native_int"

    if os.environ.get("SBPF_BENCH") == "1":
        announce("glue", f"installing {rel(main_rs)} into {rel(pkg_dir / 'src' / 'main.rs')}")
        shutil.copy2(main_rs, pkg_dir / "src" / "main.rs")
        prepare_rust_cargo(toml)
        build_cmd = cargo + ["build", "--release", "--locked", "-q", "--manifest-path", str(toml)]
        announce("build", shlex.join(build_cmd))
        rc, _ = run_command(build_cmd, cwd=ROOT, env=env)
        if rc != 0:
            return rc
        binary = pkg_dir / "target" / "release" / "isabelle_exported"
        announce("benchmark", f"one timed traversal of {len(json.loads((DATA_DIR / 'interp_in.json').read_text()))} cases")
        rc, _ = run_command([str(binary)], cwd=ROOT, env=env)
        return rc

    if cache_is_valid(pkg_dir, key):
        announce("cache", "reusing compiled Rust macro binary (no source changes)")
    else:
        announce("glue", f"installing {rel(main_rs)} into {rel(pkg_dir / 'src' / 'main.rs')}")
        shutil.copy2(main_rs, pkg_dir / "src" / "main.rs")
        prepare_rust_cargo(toml)

        build_cmd = cargo + ["build", "--release", "--locked", "-q", "--manifest-path", str(toml)]
        announce("build", shlex.join(build_cmd))
        rc, _ = run_command(build_cmd, cwd=ROOT, env=env)
        if rc != 0:
            return rc

        stamp = pkg_dir / ".rust_macro_cache.json"
        stamp.write_text(json.dumps(key, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        announce("cache", f"wrote stamp {rel(stamp)}")

    binary = pkg_dir / "target" / "release" / "isabelle_exported"
    with open(DATA_DIR / "interp_in.json", "r", encoding="utf-8") as f:
        cases = json.load(f)

    timeout = rust_case_timeout()
    timeout_detail = "no per-case timeout" if timeout is None else f"timeout {timeout:g}s each"
    announce("run", f"{len(cases)} cases via {rel(binary)} ({timeout_detail})")

    passed = 0
    failed = 0
    timed_out = 0
    case_timings: list[tuple[float, int, str]] = []
    red = "\x1b[31m"
    reset = "\x1b[0m"
    for index, case in enumerate(cases):
        case_env = env.copy()
        case_env["CROSS_CASE_INDEX"] = str(index)
        case_start = time.monotonic()
        print(f">>> [sbpf_rust] case {index + 1}/{len(cases)} {case['dis']}", flush=True)
        case_rc, case_output = run_captured(
            [str(binary)],
            cwd=ROOT,
            env=case_env,
            timeout=timeout,
        )
        elapsed = time.monotonic() - case_start
        case_timings.append((elapsed, index + 1, case["dis"]))
        if case_output:
            print(case_output, end="" if case_output.endswith("\n") else "\n")
        if case_rc is None:
            timed_out += 1
            failed += 1
            print(
                f"{red}{index + 1} {case['dis']:<40} result: "
                f"{red}false (timeout after {timeout:g}s){reset}"
            )
            print(f">>> [sbpf_rust] case {index + 1} elapsed {elapsed:.3f}s", flush=True)
        elif case_rc == 0:
            passed += 1
            print(f">>> [sbpf_rust] case {index + 1} elapsed {elapsed:.3f}s", flush=True)
        else:
            failed += 1
            print(f">>> [sbpf_rust] case {index + 1} elapsed {elapsed:.3f}s", flush=True)

    print("\nSummary (interp macro test, Rust export):")
    print(f"Passed: {passed}")
    print(f"Failed: {failed} (of which {timed_out} timed out)")
    if case_timings:
        print("Slowest cases:")
        for elapsed, case_no, dis in sorted(case_timings, reverse=True)[:5]:
            print(f"  {case_no:>3} {dis:<40} {elapsed:.3f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
