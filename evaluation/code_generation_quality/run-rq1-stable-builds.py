#!/usr/bin/env python3
"""Build the frozen RQ1 Stage-1/Stage-2 corpus with stable Rust only."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import re
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
LOCK_HELPER = REPO / "scripts" / "ensure-cargo-lock.py"
SHARED_LOCK = REPO / "scripts" / "isabelle-exported.Cargo.lock"
EXPECTED_RUSTC_RELEASE = os.environ.get("EXPECTED_RUSTC_RELEASE", "1.94.0")
EXPECTED_SUITES = {"HCT": 2, "Unit": 55, "FPP": 36}
EXPORT_CODE = re.compile(r"^\s*export_code(?:\s|$)", re.MULTILINE)
FEATURE_GATE = re.compile(r"#!\s*\[\s*feature\s*\(")
NATURAL_PART = re.compile(r"(\d+)")


def natural_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part
        for part in NATURAL_PART.split(str(path).lower())
    ]


def stable_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("RUSTC_BOOTSTRAP", None)
    environment["CARGO"] = "cargo +stable"
    environment["RUSTFLAGS"] = "-Awarnings"
    return environment


def run(command: list[str], *, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def verify_toolchain(environment: dict[str, str]) -> tuple[str, str]:
    rustc = run(["rustc", "+stable", "-Vv"], environment=environment)
    cargo = run(["cargo", "+stable", "-V"], environment=environment)
    if rustc.returncode != 0 or cargo.returncode != 0:
        raise RuntimeError(rustc.stderr.strip() or cargo.stderr.strip())
    release = next(
        (line.removeprefix("release: ") for line in rustc.stdout.splitlines() if line.startswith("release: ")),
        "",
    )
    if release != EXPECTED_RUSTC_RELEASE or any(
        marker in release for marker in ("nightly", "beta", "dev")
    ):
        raise RuntimeError(
            f"expected stable rustc {EXPECTED_RUSTC_RELEASE}, but rustc +stable reports {release or 'unknown'}"
        )
    return rustc.stdout.splitlines()[0], cargo.stdout.strip()


def tracked_theories() -> list[tuple[str, Path]]:
    tracked = run(
        ["git", "ls-files", "--", "test/unit", "test/fpp"],
        environment=stable_environment(),
    )
    if tracked.returncode != 0:
        raise RuntimeError(tracked.stderr.strip())

    selected: list[tuple[str, Path]] = [
        ("HCT", REPO / "test" / "HOL_Codegenerator" / "Generate.thy"),
        ("HCT", REPO / "test" / "HOL_Codegenerator" / "Generate_Binary_Nat.thy"),
    ]
    for relative in tracked.stdout.splitlines():
        # Development examples are tracked for convenience but are not part of
        # the frozen RQ1 Unit corpus documented in this directory's README.
        if relative.startswith("test/unit/example/"):
            continue
        theory = REPO / relative
        if theory.name.endswith("_Test.thy") and EXPORT_CODE.search(
            theory.read_text(encoding="utf-8")
        ):
            suite = "Unit" if relative.startswith("test/unit/") else "FPP"
            selected.append((suite, theory))

    counts = {
        suite: sum(selected_suite == suite for selected_suite, _ in selected)
        for suite in EXPECTED_SUITES
    }
    if counts != EXPECTED_SUITES:
        raise RuntimeError(f"RQ1 corpus mismatch: expected {EXPECTED_SUITES}, found {counts}")
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


def reject_unstable_crate(manifest: Path) -> None:
    root = manifest.parent
    for source in root.rglob("*.rs"):
        if "target" in source.relative_to(root).parts:
            continue
        if FEATURE_GATE.search(source.read_text(encoding="utf-8", errors="replace")):
            raise RuntimeError(f"unstable feature gate in {source.relative_to(REPO)}")
    for toolchain in (*root.glob("rust-toolchain"), *root.glob("rust-toolchain.toml")):
        text = toolchain.read_text(encoding="utf-8", errors="replace").lower()
        if "nightly" in text or "beta" in text:
            raise RuntimeError(f"non-stable toolchain file {toolchain.relative_to(REPO)}")


def build_one(
    suite: str,
    theory: Path,
    stage: str,
    manifest: Path,
    environment: dict[str, str],
) -> tuple[str, str, str, Path, str]:
    reject_unstable_crate(manifest)
    locked = run(
        [sys.executable, str(LOCK_HELPER), str(manifest), str(SHARED_LOCK)],
        environment=environment,
    )
    if locked.returncode != 0:
        return suite, theory.stem, stage, manifest, locked.stderr.strip() or locked.stdout.strip()
    built = run(
        ["cargo", "+stable", "build", "--quiet", "--locked", "--manifest-path", str(manifest)],
        environment=environment,
    )
    return suite, theory.stem, stage, manifest, "" if built.returncode == 0 else built.stderr.strip()


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processes", type=positive_int, default=4)
    args = parser.parse_args()

    environment = stable_environment()
    try:
        rustc, cargo = verify_toolchain(environment)
        theories = tracked_theories()
        jobs = [
            (suite, theory, stage, latest_manifest(theory, stage))
            for suite, theory in theories
            for stage in ("stage1", "stage2")
        ]
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Toolchain: {rustc}; {cargo}; RUSTC_BOOTSTRAP unset", flush=True)
    print("Corpus: HCT=2, Unit=55, FPP=36; pairs=93; crates=186", flush=True)
    failures: list[tuple[str, str, str, Path, str]] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=args.processes) as executor:
        futures = {
            executor.submit(build_one, *job, environment): job
            for job in jobs
        }
        for future in as_completed(futures):
            result = future.result()
            if result[-1]:
                failures.append(result)
            completed += 1
            if completed % 10 == 0 or completed == len(jobs):
                print(f"  built {completed}/{len(jobs)} crates", flush=True)

    if failures:
        print("Stable build failures:", file=sys.stderr)
        for suite, theory, stage, manifest, error in failures:
            print(
                f"  - {suite} {theory} {stage}: {manifest.relative_to(REPO)}",
                file=sys.stderr,
            )
            if error:
                print(f"    {error.splitlines()[-1]}", file=sys.stderr)
        return 1

    print("RQ1 stable compiler acceptance: PASS (93/93 pairs; 186/186 crates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
