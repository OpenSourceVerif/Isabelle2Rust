#!/usr/bin/env python3
"""Run the Rust SBPF instruction-level micro test from Isabelle-generated code."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(os.environ.get("SBPF_ROOT", Path(__file__).resolve().parents[5]))
EXEC_DIR = Path(os.environ.get("SBPF_EXEC_DIR", ROOT / "test" / "sbpf" / "tests" / "exec_semantics"))
DATA_DIR = Path(os.environ.get("SBPF_DATA_DIR", ROOT / "test" / "sbpf" / "tests" / "data"))
EXPORT_DIR = Path(
    os.environ.get(
        "SBPF_EXPORT_DIR",
        ROOT / "test" / "sbpf" / "theory" / "stage1" / "bpf_generator_bigint",
    )
)
STEP_JSON = Path(os.environ.get("SBPF_STEP_JSON", DATA_DIR / "ocaml_in.json"))
RUST_DIR = EXEC_DIR / "sbpf_rust"

RUST_TOOLCHAIN = os.environ.get("RUST_TOOLCHAIN", "stable")
GLUE_VERSION = "step-micro-rust-stable-v1"


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


def ensure_dependency(text: str, name: str, spec: str) -> str:
    pattern = rf"(?m)^{re.escape(name)}\s*=.*$"
    if re.search(pattern, text):
        return re.sub(pattern, f"{name} = {spec}", text)
    if "[lints.rust]" in text:
        return text.replace("[lints.rust]", f"{name} = {spec}\n\n[lints.rust]", 1)
    return text.rstrip() + f"\n{name} = {spec}\n"


def prepare_rust_cargo(toml: Path) -> None:
    text = toml.read_text(encoding="utf-8")
    text = ensure_dependency(text, "serde", '{ version = "1.0", features = ["derive"] }')
    text = ensure_dependency(text, "serde_json", '"1.0"')
    toml.write_text(text, encoding="utf-8")

    lock_src = ROOT / "scripts" / "isabelle-exported.Cargo.lock"
    lock_dst = toml.parent / "Cargo.lock"
    if lock_src.exists() and not lock_dst.exists():
        shutil.copy2(lock_src, lock_dst)


def lock_has_step_deps(lock: Path) -> bool:
    if not lock.exists():
        return False
    text = lock.read_text(encoding="utf-8")
    return 'name = "serde"' in text and 'name = "serde_json"' in text


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
        "export_rs_sha256": file_sha256(export_rs),
        "glue_rs_sha256": file_sha256(glue_rs),
    }


def cache_is_valid(pkg_dir: Path, key: dict[str, str]) -> bool:
    stamp = pkg_dir / ".rust_micro_cache.json"
    binary = pkg_dir / "target" / "release" / "isabelle_exported"
    if os.environ.get("REBUILD") == "1":
        return False
    if not stamp.exists() or not binary.exists():
        return False
    try:
        return json.loads(stamp.read_text(encoding="utf-8")) == key
    except json.JSONDecodeError:
        return False


def main() -> int:
    toml = EXPORT_DIR / "step_test" / "Cargo.toml"
    if not toml.exists():
        print(f"ERROR: missing Isabelle Rust export: {rel(toml)}")
        return 2
    if not STEP_JSON.exists():
        print(f"ERROR: missing step JSON: {rel(STEP_JSON)}")
        return 2

    cargo = cargo_command()
    if not check_rust_environment(cargo):
        return 2

    pkg_dir = toml.parent
    export_rs = pkg_dir / "src" / "Step_test.rs"
    main_rs = RUST_DIR / "step_main.rs"

    if not export_rs.exists():
        print(f"ERROR: missing Isabelle Rust export: {rel(export_rs)}")
        return 2

    key = cache_key(export_rs, main_rs)

    env = os.environ.copy()
    env.pop("RUSTC_BOOTSTRAP", None)
    env["CROSS_JSON"] = str(STEP_JSON)
    env["RUSTFLAGS"] = "-Awarnings"
    if os.environ.get("SBPF_STAGE") == "2":
        env["RUSTFLAGS"] += " --cfg sbpf_stage2"
    if os.environ.get("SBPF_NO_BIGINT") == "1":
        env["RUSTFLAGS"] += " --cfg sbpf_no_bigint"

    if os.environ.get("SBPF_BENCH_REPEATS") is not None:
        announce("glue", f"installing {rel(main_rs)} into {rel(pkg_dir / 'src' / 'main.rs')}")
        shutil.copy2(main_rs, pkg_dir / "src" / "main.rs")
        prepare_rust_cargo(toml)
        lock = toml.parent / "Cargo.lock"
        if not lock_has_step_deps(lock):
            lock_cmd = cargo + ["generate-lockfile", "--manifest-path", str(toml)]
            announce("lockfile", shlex.join(lock_cmd))
            rc, _ = run_command(lock_cmd, cwd=ROOT, env=env)
            if rc != 0:
                return rc
        build_cmd = cargo + ["build", "--release", "--locked", "-q", "--manifest-path", str(toml)]
        announce("build", shlex.join(build_cmd))
        rc, _ = run_command(build_cmd, cwd=ROOT, env=env)
        if rc != 0:
            return rc
        binary = pkg_dir / "target" / "release" / "isabelle_exported"
        announce("benchmark", f"timing {rel(STEP_JSON)}")
        rc, _ = run_command([str(binary)], cwd=ROOT, env=env)
        return rc

    if cache_is_valid(pkg_dir, key):
        announce("cache", "reusing compiled Rust micro binary (no source changes)")
    else:
        announce("glue", f"installing {rel(main_rs)} into {rel(pkg_dir / 'src' / 'main.rs')}")
        shutil.copy2(main_rs, pkg_dir / "src" / "main.rs")
        prepare_rust_cargo(toml)

        lock = toml.parent / "Cargo.lock"
        if not lock_has_step_deps(lock):
            lock_cmd = cargo + ["generate-lockfile", "--manifest-path", str(toml)]
            announce("lockfile", shlex.join(lock_cmd))
            rc, _ = run_command(lock_cmd, cwd=ROOT, env=env)
            if rc != 0:
                return rc

        build_cmd = cargo + ["build", "--release", "--locked", "-q", "--manifest-path", str(toml)]
        announce("build", shlex.join(build_cmd))
        rc, _ = run_command(build_cmd, cwd=ROOT, env=env)
        if rc != 0:
            return rc

        stamp = pkg_dir / ".rust_micro_cache.json"
        stamp.write_text(json.dumps(key, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        announce("cache", f"wrote stamp {rel(stamp)}")

    binary = pkg_dir / "target" / "release" / "isabelle_exported"
    announce("run", f"{rel(binary)} over {rel(STEP_JSON)}")
    rc, _ = run_command([str(binary)], cwd=ROOT, env=env)
    return rc


if __name__ == "__main__":
    sys.exit(main())
