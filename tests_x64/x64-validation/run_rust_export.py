#!/usr/bin/env python3
"""Export and compile the unmodified Rust x64 validation baselines.

This preflight is intentionally separate from the correctness harness.  It
builds the two Rust-only generator theories, verifies their expected artifacts,
and compiles the generated Cargo projects before any test glue is copied into a
working tree.  A successful result therefore establishes that the raw
``x64_encode`` and ``x64_step_test`` exports compile on their own.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
THEORY_DIR = ROOT / "tests_x64" / "theory"
LOCK_SOURCE = ROOT / "scripts" / "isabelle-exported.Cargo.lock"
RUST_TOOLCHAIN = os.environ.get("RUST_TOOLCHAIN", "nightly-2025-12-01")
ISABELLE_THREADS = os.environ.get("X64_ISABELLE_THREADS", "1")
ISABELLE_TIMEOUT = os.environ.get("X64_ISABELLE_TIMEOUT", "1200")
ISABELLE_MAX_HEAP = os.environ.get("X64_ISABELLE_MAX_HEAP", "3200")
ISABELLE_JAVA_HEAP = os.environ.get("X64_ISABELLE_JAVA_HEAP", "768")
ISABELLE_LAUNCHER = ROOT / "tests_x64" / "x64-validation" / "_build" / "isabelle-bounded"


@dataclass(frozen=True)
class ExportSpec:
    """Expected artifacts for one raw x64 Rust code export."""

    theory: str
    crate: str
    module: str

    @property
    def export_root(self) -> Path:
        return THEORY_DIR / "stage1" / self.theory

    @property
    def crate_dir(self) -> Path:
        return self.export_root / self.crate


EXPORTS = (
    ExportSpec("x64EncodeRustGenerator", "x64_encode", "X64_encode.rs"),
    ExportSpec("x64StepRustGenerator", "x64_step_test", "X64_step_test.rs"),
)


def rel(path: Path) -> str:
    """Render repository paths without hiding external override locations."""

    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def announce(title: str, detail: str) -> None:
    print(f">>> [x64-rust-export] {title}: {detail}", flush=True)


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> int:
    """Run one preflight command with output streamed in execution order."""

    announce("command", shlex.join(cmd))
    return subprocess.run(cmd, cwd=cwd, env=env).returncode


def cargo_command() -> list[str]:
    """Honor CARGO overrides while selecting the fixed nightly by default."""

    command = shlex.split(os.environ.get("CARGO", "cargo"))
    if command == ["cargo"] and RUST_TOOLCHAIN:
        return ["cargo", f"+{RUST_TOOLCHAIN}"]
    return command


def expected_files(spec: ExportSpec) -> tuple[Path, Path]:
    return spec.crate_dir / "Cargo.toml", spec.crate_dir / "src" / spec.module


def isabelle_environment() -> dict[str, str]:
    """Create a bounded launcher after loading the normal Isabelle settings.

    The x64 definitions retain a large code-generator graph.  Isabelle's
    bundled Poly/ML configuration sets only a minimum heap size, so a process
    can otherwise consume all memory assigned to WSL before the operating
    system can terminate it cleanly.  The launcher retains the developer's AFP
    roots and session database, then overrides only the process memory values
    after settings have been loaded.  The second Isabelle invocation sees the
    settings marker and therefore cannot overwrite those bounded values.
    """

    isabelle = shutil.which("isabelle")
    if isabelle is None:
        raise RuntimeError("isabelle executable not found in PATH")
    isabelle_home = Path(isabelle).resolve().parents[1]
    ISABELLE_LAUNCHER.parent.mkdir(parents=True, exist_ok=True)
    ISABELLE_LAUNCHER.write_text(
        "#!/usr/bin/env bash\n"
        "# Generated x64 export launcher; removed by make clean.\n"
        # Isabelle's settings scripts intentionally probe unset variables, so
        # nounset cannot be enabled around the component-loading phase.
        "set -e\n"
        f'export ISABELLE_HOME={shlex.quote(str(isabelle_home))}\n'
        'source "$ISABELLE_HOME/lib/scripts/getsettings"\n'
        f'export ML_OPTIONS="--minheap 500 --maxheap {ISABELLE_MAX_HEAP} '
        '--gcthreads 1 --gcpercent 25"\n'
        'export ISABELLE_TOOL_JAVA_OPTIONS="-Djava.awt.headless=true -Xms256m '
        f'-Xmx{ISABELLE_JAVA_HEAP}m -Xss16m"\n'
        'exec "$ISABELLE_HOME/bin/isabelle" "$@"\n',
        encoding="utf-8",
    )
    ISABELLE_LAUNCHER.chmod(0o755)
    env = os.environ.copy()
    # The launcher must perform the first settings load itself.
    env.pop("ISABELLE_SETTINGS_PRESENT", None)
    return env


def check_isabelle_environment(env: dict[str, str]) -> bool:
    """Reject the export unless Isabelle reports the intended hard limits."""

    cmd = [str(ISABELLE_LAUNCHER), "getenv", "ML_OPTIONS", "ISABELLE_TOOL_JAVA_OPTIONS"]
    announce("command", shlex.join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    required = (
        f"--maxheap {ISABELLE_MAX_HEAP}",
        "--gcthreads 1",
        f"-Xmx{ISABELLE_JAVA_HEAP}m",
    )
    missing = [value for value in required if value not in completed.stdout]
    if completed.returncode != 0 or missing:
        if missing:
            print(
                "ERROR: Isabelle did not load the bounded export settings: "
                + ", ".join(missing)
            )
        return False
    return True


def ensure_export(
    spec: ExportSpec, *, rebuild: bool, isabelle_env: dict[str, str]
) -> bool:
    """Generate a Rust export only when absent or explicitly requested."""

    missing = [path for path in expected_files(spec) if not path.exists()]
    if not rebuild and not missing:
        announce("Isabelle export", f"reusing {rel(spec.crate_dir)}")
        return True

    reason = "REBUILD=1" if rebuild else "missing " + ", ".join(rel(p) for p in missing)
    announce("Isabelle export", f"building {spec.theory} ({reason})")
    # A new export must not inherit an old main.rs, lockfile, target tree, or
    # previously injected test fragment.  The directory contains only
    # reproducible Isabelle export artifacts for this one generator theory.
    if spec.export_root.exists():
        shutil.rmtree(spec.export_root)
    # x64 code generation retains a large HOL/code-generator graph.  Pass the
    # worker limit as an explicit make-variable override: Isabelle settings
    # intentionally replace a same-named process environment variable, while
    # ``-o threads=...`` on the actual build command is authoritative.
    isabelle_build = (
        f"{shlex.quote(str(ISABELLE_LAUNCHER))} build -v -e "
        f"-o threads={ISABELLE_THREADS} -d test-root Rust"
    )
    rc = run(
        [
            "make",
            "build",
            "TEST_DIR=tests_x64/theory",
            f"TEST_THEORY={spec.theory}",
            f"TEST_TIMEOUT={ISABELLE_TIMEOUT}",
            f"ISABELLE_TEST_VERBOSE={isabelle_build}",
        ],
        cwd=ROOT,
        env=isabelle_env,
    )
    if rc != 0:
        return False

    missing_after = [path for path in expected_files(spec) if not path.exists()]
    for path in missing_after:
        print(f"ERROR: expected Rust export not found: {rel(path)}")
    return not missing_after


def install_lockfile(spec: ExportSpec) -> bool:
    """Install only reproducibility metadata; generated Rust sources stay raw."""

    if not LOCK_SOURCE.exists():
        print(f"ERROR: shared generated-crate lockfile is missing: {rel(LOCK_SOURCE)}")
        return False
    destination = spec.crate_dir / "Cargo.lock"
    shutil.copy2(LOCK_SOURCE, destination)
    return True


def compile_export(spec: ExportSpec, cargo: list[str]) -> bool:
    """Compile the untouched generated crate before correctness glue exists."""

    if not install_lockfile(spec):
        return False
    env = os.environ.copy()
    env["RUSTC_BOOTSTRAP"] = "1"
    env["RUSTFLAGS"] = "-Awarnings"
    manifest = spec.crate_dir / "Cargo.toml"
    announce("raw Cargo build", rel(manifest))
    return (
        run(
            cargo + ["build", "--locked", "--manifest-path", str(manifest)],
            cwd=ROOT,
            env=env,
        )
        == 0
    )


def main() -> int:
    rebuild = os.environ.get("REBUILD") == "1"
    cargo = cargo_command()
    if run(cargo + ["--version"], cwd=ROOT) != 0:
        return 2

    isabelle_env = isabelle_environment()
    announce(
        "Isabelle memory limits",
        f"Poly/ML={ISABELLE_MAX_HEAP} MiB, Java={ISABELLE_JAVA_HEAP} MiB",
    )
    # Print the effective values before the expensive build.  This turns an
    # incorrectly loaded user component into an immediate gate failure instead
    # of risking another unbounded Poly/ML process.
    if not check_isabelle_environment(isabelle_env):
        return 2
    passed = 0
    for spec in EXPORTS:
        if not ensure_export(spec, rebuild=rebuild, isabelle_env=isabelle_env):
            print(f"ERROR: Rust export failed for {spec.theory}")
            break
        if not compile_export(spec, cargo):
            print(f"ERROR: raw Rust export did not compile for {spec.theory}")
            break
        passed += 1

    failed = len(EXPORTS) - passed
    print("\n========================================")
    print("x64 raw Rust export summary")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print("  Overall: PASS" if failed == 0 else "  Overall: FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
