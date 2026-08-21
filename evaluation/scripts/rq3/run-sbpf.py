#!/usr/bin/env python3
"""Prepare, validate, and measure the RQ3 SBPF performance matrix."""

from __future__ import annotations

import argparse
import csv
import ctypes
import errno
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "evaluation" / "harness" / "rq3"
SBPF_HARNESS = HARNESS / "sbpf"
DATA = ROOT / "test" / "sbpf" / "tests" / "data"
PROGRAM_INPUT = DATA / "interp_in.json"
STEP_INPUT = DATA / "ocaml_in_6000.json"
DEFAULT_EXPORT = (
    ROOT / "test" / "sbpf" / "theory" / "stage1" / "bpf_generator_bigint"
)
ADAPTED_EXPORTS = {
    "interp_test": ROOT
    / "test"
    / "sbpf"
    / "theory"
    / "stage1"
    / "bpf_generator_checked128"
    / "interp_test",
    "step_test": ROOT
    / "test"
    / "sbpf"
    / "theory"
    / "stage1"
    / "bpf_generator_checked128"
    / "step_test",
}
GENERATED_ROOT = ROOT / "test" / "sbpf" / "theory" / "performance"
OPTIMIZER = ROOT / "optimize" / "target" / "release" / "cargo-opt"
RUSTLIGHTAST = ROOT.parent / "RustLightAST"
BASELINE = SBPF_HARNESS / "native"
WORK = ROOT / "evaluation" / ".work" / "rq3" / "sbpf"
BUILD = WORK / "build"
RESULTS = WORK / "runs"
TIME = Path("/usr/bin/time")
CPU = "0"
RUNTIME_TARGET_SECONDS = 5.0
CASE_STUDY_REPETITIONS = {
    "SBPF-program": 20,
    "SBPF-instruction": 1,
}

STAGES = {
    "Stage-1": ("stage1", [], False),
    "Stage-2 minus Borrow": ("stage2-no-borrow", ["--disable-borrow"], False),
    "Stage-2 minus Last-Use": (
        "stage2-no-last-use",
        ["--disable-last-use"],
        True,
    ),
    "Stage-2 minus Closure": (
        "stage2-no-closure",
        ["--disable-closure"],
        True,
    ),
    "Stage-2 Full": ("stage2-full", [], True),
    "Stage-2 minus Copy": ("stage2-no-copy", ["--disable-copy"], True),
    "Stage-2 minus Mut": ("stage2-no-mut", ["--disable-mut"], True),
    "Stage-2 minus PreferOwned": (
        "stage2-no-prefer-owned",
        ["--disable-prefer-owned"],
        True,
    ),
}

STAGE2_IMPLEMENTATIONS = [
    "Stage-2 minus Borrow",
    "Stage-2 minus Last-Use",
    "Stage-2 minus Closure",
    "Stage-2 Full",
]

RUST_IMPLEMENTATIONS = ["Stage-1", *STAGE2_IMPLEMENTATIONS]
DIAGNOSTIC_IMPLEMENTATIONS = [
    "Stage-2 minus Copy",
    "Stage-2 minus Mut",
    "Stage-2 Full",
]
IMPLEMENTATIONS = [
    *RUST_IMPLEMENTATIONS,
    "OCaml baseline",
    "Case-study baseline",
]

ABLATION_GROUPS = {
    "Borrow": "Stage-2 minus Borrow",
    "Last-Use": "Stage-2 minus Last-Use",
    "Closure": "Stage-2 minus Closure",
}

DIAGNOSTIC_ABLATIONS = {
    "Copy": "Stage-2 minus Copy",
    "Mut": "Stage-2 minus Mut",
}

PREFER_OWNED_IMPLEMENTATIONS = ["Stage-2 minus PreferOwned", "Stage-2 Full"]
PREFER_OWNED_ABLATIONS = {"PreferOwned": "Stage-2 minus PreferOwned"}

STRUCTURAL_TRANSFORMATIONS = [
    "binding cleanup",
    "match cleanup",
    "Boolean cleanup",
    "bound cleanup",
    "complex-type cleanup",
]

BENCHMARKS = {
    "SBPF-program": ("interp_test", PROGRAM_INPUT, "generated_program.rs"),
    "SBPF-instruction": ("step_test", STEP_INPUT, "generated_step.rs"),
}

RESULT_RE = re.compile(r"^RESULT\s+(.*)$", re.MULTILINE)
RSS_RE = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")

COMMANDS: list[str] = []
RESULT_DIR: Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_text(command: list[str], env: dict[str, str] | None = None) -> str:
    prefix = ""
    if env:
        visible = {
            key: value
            for key, value in env.items()
            if key
            in {
                "CARGO_TARGET_DIR",
                "CROSS_JSON",
                "RUSTFLAGS",
                "SBPF_MEASURE",
                "SUITE_REPETITIONS",
            }
        }
        prefix = " ".join(f"{key}={shlex.quote(value)}" for key, value in visible.items())
        if prefix:
            prefix += " "
    return prefix + shlex.join(command)


def save_commands() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "commands.txt").write_text("\n".join(COMMANDS) + "\n", encoding="utf-8")


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("RUSTC_BOOTSTRAP", None)
    env.pop("RUSTFLAGS", None)
    if extra:
        env.update(extra)
    return env


def execute(
    command: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    actual_env = clean_env(env)
    rendered = command_text(command, env)
    COMMANDS.append(f"cd {shlex.quote(str(cwd))} && {rendered}")
    save_commands()
    print(f">>> {rendered}", flush=True)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=actual_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.returncode != 0 and completed.stderr:
        print(completed.stderr, file=sys.stderr, end="" if completed.stderr.endswith("\n") else "\n")
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode, command, completed.stdout, completed.stderr
        )
    return completed


def output(command: list[str], cwd: Path = ROOT) -> str:
    return subprocess.check_output(command, cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()


def add_benchmark_dependencies(manifest: Path) -> None:
    text = manifest.read_text(encoding="utf-8")
    if "serde =" not in text:
        text = text.replace(
            "[lints.rust]",
            'serde = { version = "1.0", features = ["derive"] }\nserde_json = "1.0"\n\n[lints.rust]',
            1,
        )
    if "unexpected_cfgs" not in text:
        text = text.rstrip() + (
            "\nunexpected_cfgs = { level = \"allow\", "
            "check-cfg = ['cfg(sbpf_borrowed)', 'cfg(allocation_metrics)'] }\n"
        )
    manifest.write_text(text, encoding="utf-8")


def copy_clean_package(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    (destination / "src").mkdir(parents=True)
    shutil.copy2(source / "Cargo.toml", destination / "Cargo.toml")
    for rust_source in sorted((source / "src").glob("*.rs")):
        shutil.copy2(rust_source, destination / "src" / rust_source.name)
    add_benchmark_dependencies(destination / "Cargo.toml")


def source_shape_metrics(stage_dir: Path) -> dict[str, int]:
    sources = sorted(stage_dir.glob("*/src/*.rs"))
    texts = [source.read_text(encoding="utf-8") for source in sources]
    return {
        "rust_files": len(sources),
        "source_bytes": sum(len(text.encode("utf-8")) for text in texts),
        "clone_calls": sum(text.count(".clone()") for text in texts),
        "let_mut_bindings": sum(len(re.findall(r"\blet\s+mut\b", text)) for text in texts),
        "borrow_optimized_functions": sum(
            text.count("// borrow-optimized by shared parameters") for text in texts
        ),
        "mut_optimized_functions": sum(
            text.count("// mut-optimized by in-place updates") for text in texts
        ),
        "inferred_copy_derives": sum(
            text.count("// copy-optimized by inferred Copy derive") for text in texts
        ),
        "complex_type_aliases": sum(text.count("I2rComplexTypeH") for text in texts),
    }


def write_stage_manifest(
    stage_dir: Path,
    implementation: str,
    optimizer_flags: list[str],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    optimized = implementation != "Stage-1"
    generated_hashes = {}
    for package, _, _ in BENCHMARKS.values():
        for source in sorted((stage_dir / package / "src").glob("*.rs")):
            generated_hashes[f"{package}/{source.name}"] = sha256(source)
    manifest = {
        "implementation": implementation,
        "optimized": optimized,
        "optimizer_flags": optimizer_flags,
        "source_stage1_sha256": source_hashes,
        "generated_source_sha256": generated_hashes,
        "optimizer_sha256": sha256(OPTIMIZER) if optimized else None,
        "stage2_groups": {
            "borrow": optimized and "--disable-borrow" not in optimizer_flags,
            "last_use": optimized and "--disable-last-use" not in optimizer_flags,
            "closure": optimized and "--disable-closure" not in optimizer_flags,
        },
        "stage2_passes": {
            "copy": optimized and "--disable-copy" not in optimizer_flags,
            "borrow": optimized and "--disable-borrow" not in optimizer_flags,
            "mut": optimized and "--disable-mut" not in optimizer_flags,
            "last_use": optimized and "--disable-last-use" not in optimizer_flags,
            "closure": optimized and "--disable-closure" not in optimizer_flags,
        },
        "borrow_policy": {
            "prefer_owned": optimized
            and "--disable-borrow" not in optimizer_flags
            and "--disable-prefer-owned" not in optimizer_flags,
        },
        "structural_transformations": {
            "enabled": optimized,
            "members": STRUCTURAL_TRANSFORMATIONS,
        },
        "stage1_materialization": (
            "original export copied without cargo-opt or RustLightAST parsing/printing"
            if not optimized
            else "cargo-opt applied to an unchanged copy of the original Stage-1 export"
        ),
        "source_shape": source_shape_metrics(stage_dir),
    }
    (stage_dir / "configuration.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def generate_step_input() -> None:
    execute(
        [
            "make",
            "micro_sbpf_gen",
            "X=6000",
            f"SBPF_STEP_JSON={STEP_INPUT.relative_to(ROOT)}",
            "SBPF_STEP_SEED=5984326",
            "RUST_TOOLCHAIN=stable",
        ]
    )
    values = json.loads(STEP_INPUT.read_text(encoding="utf-8"))
    if len(values) != 6000:
        raise RuntimeError(f"generated {len(values)} instruction vectors, expected 6000")


def generate_exports(*, include_baseline: bool = True) -> None:
    theories = ["bpf_generator_checked128"]
    if include_baseline:
        theories.insert(0, "bpf_generator_bigint")
    for theory in theories:
        execute(
            [
                "make",
                "build",
                "TEST_DIR=test/sbpf/theory",
                f"TEST_THEORY={theory}",
            ]
        )
    required = [
        ADAPTED_EXPORTS["interp_test"] / "src" / "Interp_test.rs",
        ADAPTED_EXPORTS["step_test"] / "src" / "Step_test.rs",
    ]
    if include_baseline:
        required.extend(
            [
                DEFAULT_EXPORT / "interp_test.ocaml",
                DEFAULT_EXPORT / "step_test.ocaml",
            ]
        )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing regenerated exports: {missing}")


def prepare_generated(
    configurations: dict[str, Any], implementations: list[str] | None = None
) -> None:
    selected = set(implementations or RUST_IMPLEMENTATIONS)
    if any(implementation != "Stage-1" for implementation in selected):
        execute(["cargo", "+stable", "build", "--release", "--locked"], cwd=ROOT / "optimize")
    source_hashes = {}
    for package, source_package in ADAPTED_EXPORTS.items():
        for source in sorted((source_package / "src").glob("*.rs")):
            source_hashes[f"{package}/{source.name}"] = sha256(source)
    for implementation, (directory, optimizer_flags, borrowed) in STAGES.items():
        if implementation not in selected:
            continue
        stage_dir = GENERATED_ROOT / directory
        if stage_dir.exists():
            shutil.rmtree(stage_dir)
        if implementation == "Stage-1":
            for package, _, _ in BENCHMARKS.values():
                copy_clean_package(ADAPTED_EXPORTS[package], stage_dir / package)
        else:
            scratch = GENERATED_ROOT / ".stage1-source"
            if scratch.exists():
                shutil.rmtree(scratch)
            for package, _, _ in BENCHMARKS.values():
                copy_clean_package(ADAPTED_EXPORTS[package], scratch / package)
                command = [
                    str(OPTIMIZER),
                    str(scratch / package),
                    "--out-dir",
                    str(stage_dir / package),
                    *optimizer_flags,
                ]
                execute(command)
                add_benchmark_dependencies(stage_dir / package / "Cargo.toml")
            shutil.rmtree(scratch)

        for benchmark, (package, _, template) in BENCHMARKS.items():
            shutil.copy2(
                SBPF_HARNESS / "rust" / template,
                stage_dir / package / "src" / "main.rs",
            )
            execute(
                ["cargo", "+stable", "generate-lockfile", "--manifest-path", str(stage_dir / package / "Cargo.toml")]
            )
        configurations[implementation] = write_stage_manifest(
            stage_dir, implementation, optimizer_flags, source_hashes
        )
        configurations[implementation]["borrowed_adapter"] = borrowed
        configurations[implementation]["prefer_owned_ablation_adapter"] = (
            implementation == "Stage-2 minus PreferOwned"
        )


def build_generated(
    configurations: dict[str, Any],
    binaries: dict[str, Any],
    implementations: list[str] | None = None,
) -> None:
    selected = set(implementations or RUST_IMPLEMENTATIONS)
    for implementation, (directory, _, borrowed) in STAGES.items():
        if implementation not in selected:
            continue
        binaries[implementation] = {}
        for benchmark, (package, _, _) in BENCHMARKS.items():
            package_dir = GENERATED_ROOT / directory / package
            binaries[implementation][benchmark] = {}
            for metric, allocation in (("runtime", False), ("allocation", True)):
                flags = []
                if borrowed:
                    flags.append("--cfg sbpf_borrowed")
                if implementation == "Stage-2 minus PreferOwned":
                    flags.append("--cfg sbpf_no_prefer_owned")
                if allocation:
                    flags.append("--cfg allocation_metrics")
                target = package_dir / "target" / metric
                env = {"CARGO_TARGET_DIR": str(target)}
                if flags:
                    env["RUSTFLAGS"] = " ".join(flags)
                execute(
                    ["cargo", "+stable", "build", "--release", "--locked"],
                    cwd=package_dir,
                    env=env,
                )
                binary = target / "release" / "isabelle_exported"
                binaries[implementation][benchmark][metric] = {
                    "path": str(binary),
                    "sha256": sha256(binary),
                    "rustflags": env.get("RUSTFLAGS", ""),
                }
        configurations[implementation]["executables"] = binaries[implementation]


OCAML_STEP_SIGNATURE = """  val step_test :
    int list ->
      int list ->
        int list -> int list -> int -> int -> int -> int -> int -> bool
"""
OCAML_STEP_SIGNATURE_GLUE = OCAML_STEP_SIGNATURE + (
    "  val int_of_standard_int : int64 -> int\n"
    "  val int_list_of_standard_int_list : int64 list -> int list\n"
)
OCAML_PROGRAM_SIGNATURE = """  val bpf_interp_test :
    int list -> int list -> int list -> int -> int -> int -> bool -> bool
"""
OCAML_PROGRAM_SIGNATURE_GLUE = OCAML_PROGRAM_SIGNATURE + (
    "  val int_of_standard_int : int64 -> int\n"
    "  val int_list_of_standard_int_list : int64 list -> int list\n"
)
OCAML_GLUE = """
let int_of_standard_int (n : int64) : int =
  Int_of_integer (Z.of_int64 n);;

let int_list_of_standard_int_list (xs : int64 list) : int list =
  List.map int_of_standard_int xs;;

"""


def glue_ocaml(source: Path, destination: Path, benchmark: str) -> None:
    text = source.read_text(encoding="utf-8")
    if benchmark == "SBPF-program":
        signature, replacement = OCAML_PROGRAM_SIGNATURE, OCAML_PROGRAM_SIGNATURE_GLUE
        ending = "end;; (*struct Interp_test*)"
    else:
        signature, replacement = OCAML_STEP_SIGNATURE, OCAML_STEP_SIGNATURE_GLUE
        ending = "end;; (*struct Step_test*)"
    if signature not in text or ending not in text:
        raise RuntimeError(f"OCaml glue marker missing in {source}")
    text = text.replace(signature, replacement, 1)
    text = text.replace(ending, OCAML_GLUE + ending, 1)
    destination.write_text(text, encoding="utf-8")


def build_ocaml(configurations: dict[str, Any], binaries: dict[str, Any]) -> None:
    binaries["OCaml baseline"] = {}
    compiler = output(["ocamlopt", "-version"])
    if compiler != "4.11.2":
        raise RuntimeError(f"expected ocamlopt 4.11.2, got {compiler}")
    for benchmark in BENCHMARKS:
        short = "program" if benchmark == "SBPF-program" else "instruction"
        module = "interp_test" if benchmark == "SBPF-program" else "step_test"
        build_dir = BUILD / "ocaml" / short
        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True)
        glue_ocaml(DEFAULT_EXPORT / f"{module}.ocaml", build_dir / f"{module}.ml", benchmark)
        shutil.copy2(
            SBPF_HARNESS / "ocaml" / f"{short}.ml",
            build_dir / f"{short}.ml",
        )
        shutil.copy2(
            HARNESS / "common" / "monotonic_stubs.c",
            build_dir / "monotonic_stubs.c",
        )
        packages = "zarith,yojson,unix"
        execute(["ocamlfind", "ocamlopt", "-c", "monotonic_stubs.c"], cwd=build_dir)
        execute(
            ["ocamlfind", "ocamlopt", "-package", packages, "-linkpkg", "-c", f"{module}.ml"],
            cwd=build_dir,
        )
        binary = build_dir / f"sbpf-{short}"
        execute(
            [
                "ocamlfind",
                "ocamlopt",
                "-package",
                packages,
                "-linkpkg",
                "-o",
                binary.name,
                "monotonic_stubs.o",
                f"{module}.cmx",
                f"{short}.ml",
            ],
            cwd=build_dir,
        )
        binaries["OCaml baseline"][benchmark] = {
            "runtime": {"path": str(binary), "sha256": sha256(binary)},
            "allocation": {"path": str(binary), "sha256": sha256(binary)},
        }
    configurations["OCaml baseline"] = {
        "compiler": f"ocamlopt {compiler}",
        "runtime_clock": "clock_gettime(CLOCK_MONOTONIC) through an OCaml C stub",
        "source_export_sha256": {
            "interp_test.ocaml": sha256(DEFAULT_EXPORT / "interp_test.ocaml"),
            "step_test.ocaml": sha256(DEFAULT_EXPORT / "step_test.ocaml"),
        },
        "executables": binaries["OCaml baseline"],
    }


def build_case_study(configurations: dict[str, Any], binaries: dict[str, Any]) -> None:
    binaries["Case-study baseline"] = {}
    for metric, allocation in (("runtime", False), ("allocation", True)):
        target = BASELINE / "target" / metric
        env = {"CARGO_TARGET_DIR": str(target)}
        if allocation:
            env["RUSTFLAGS"] = "--cfg allocation_metrics"
        execute(["cargo", "+stable", "build", "--release", "--locked"], cwd=BASELINE, env=env)
        for benchmark, name in (
            ("SBPF-program", "sbpf-program-baseline"),
            ("SBPF-instruction", "sbpf-instruction-baseline"),
        ):
            binary = target / "release" / name
            binaries["Case-study baseline"].setdefault(benchmark, {})[metric] = {
                "path": str(binary),
                "sha256": sha256(binary),
                "rustflags": env.get("RUSTFLAGS", ""),
            }
    configurations["Case-study baseline"] = {
        "core_functions": {
            "SBPF-program": "execute_program",
            "SBPF-instruction": "execute_step",
        },
        "measurement_boundary": (
            "Executable, input memory, stack, context, memory mapping, and every EbpfVm "
            "are prepared before the timer and allocation counter are reset; each VM is "
            "executed exactly once by execute_program or execute_step"
        ),
        "excluded_front_end": (
            "JSON parsing, SBPF-program bytecode loading, and SBPF-instruction assembly "
            "are outside the measured region"
        ),
        "allocation_scope": (
            "diagnostic counter within prepared interpreter calls only; VM construction "
            "and OS-managed resources are excluded, so cross-implementation allocation "
            "is reported as unavailable"
        ),
        "runtime_suite_repetitions": CASE_STUDY_REPETITIONS,
        "source_sha256": {
            "Cargo.lock": sha256(BASELINE / "Cargo.lock"),
            "Cargo.toml": sha256(BASELINE / "Cargo.toml"),
            "src/instruction.rs": sha256(BASELINE / "src" / "instruction.rs"),
            "src/metrics.rs": sha256(BASELINE / "src" / "metrics.rs"),
            "src/program.rs": sha256(BASELINE / "src" / "program.rs"),
        },
        "executables": binaries["Case-study baseline"],
    }


def perf_event_probe() -> dict[str, Any]:
    class PerfEventAttr(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_uint32),
            ("size", ctypes.c_uint32),
            ("config", ctypes.c_uint64),
            ("sample_period", ctypes.c_uint64),
            ("sample_type", ctypes.c_uint64),
            ("read_format", ctypes.c_uint64),
            ("flags", ctypes.c_uint64),
            ("reserved", ctypes.c_ubyte * 80),
        ]

    attribute = PerfEventAttr()
    attribute.type = 0
    attribute.size = ctypes.sizeof(attribute)
    attribute.config = 1  # PERF_COUNT_HW_INSTRUCTIONS
    attribute.flags = 1  # disabled
    libc = ctypes.CDLL(None, use_errno=True)
    fd = libc.syscall(298, ctypes.byref(attribute), 0, -1, -1, 0)
    error = ctypes.get_errno()
    if fd >= 0:
        os.close(fd)
    return {
        "available": fd >= 0,
        "syscall": "perf_event_open(PERF_COUNT_HW_INSTRUCTIONS, pid=0, cpu=-1)",
        "return_value": fd,
        "errno": error,
        "error": os.strerror(error) if error else None,
        "perf_event_paranoid": Path("/proc/sys/kernel/perf_event_paranoid").read_text().strip()
        if Path("/proc/sys/kernel/perf_event_paranoid").exists()
        else None,
        "perf_executable": shutil.which("perf"),
    }


def record_environment() -> dict[str, Any]:
    affinity = sorted(os.sched_getaffinity(0))
    environment = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "git_commit": output(["git", "rev-parse", "HEAD"]),
        "git_status": output(["git", "status", "--short"]),
        "rustlightast": {
            "path": str(RUSTLIGHTAST),
            "git_commit": output(["git", "-C", str(RUSTLIGHTAST), "rev-parse", "HEAD"]),
            "git_status": output(["git", "-C", str(RUSTLIGHTAST), "status", "--short"]),
        },
        "uname": output(["uname", "-a"]),
        "lscpu": output(["lscpu"]),
        "free_h": output(["free", "-h"]),
        "rustc_stable": output(["rustc", "+stable", "--version", "--verbose"]),
        "cargo_stable": output(["cargo", "+stable", "--version"]),
        "ocamlopt": output(["ocamlopt", "-version"]),
        "cpu_affinity_before": affinity,
        "measurement_cpu": int(CPU),
        "inputs": {
            "SBPF-program": {"path": str(PROGRAM_INPUT), "sha256": sha256(PROGRAM_INPUT)},
            "SBPF-instruction": {"path": str(STEP_INPUT), "sha256": sha256(STEP_INPUT)},
        },
        "host_instructions": perf_event_probe(),
        "rustc_bootstrap_present": "RUSTC_BOOTSTRAP" in os.environ,
    }
    (RESULT_DIR / "environment.json").write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return environment


def parse_result(stdout: str) -> dict[str, str]:
    matches = RESULT_RE.findall(stdout)
    if not matches:
        raise RuntimeError(f"no machine-readable RESULT record in output:\n{stdout}")
    return dict(field.split("=", 1) for field in matches[-1].split())


def run_binary(
    binary: Path,
    benchmark: str,
    metric: str,
    repetitions: int,
    log_stem: Path,
) -> tuple[dict[str, str], int, int, str, str]:
    input_path = BENCHMARKS[benchmark][1]
    log_stem.parent.mkdir(parents=True, exist_ok=True)
    env = {
        "CROSS_JSON": str(input_path),
        "SBPF_MEASURE": metric,
        "SUITE_REPETITIONS": str(repetitions),
    }
    time_log = log_stem.with_suffix(".time")
    command = [str(TIME), "-v", "-o", str(time_log), "taskset", "-c", CPU, str(binary)]
    rendered = command_text(command, env)
    COMMANDS.append(f"cd {shlex.quote(str(ROOT))} && {rendered}")
    save_commands()
    print(f">>> {benchmark} | {metric} | {log_stem.name}", flush=True)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=clean_env(env),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    log_stem.with_suffix(".stdout").write_text(completed.stdout, encoding="utf-8")
    log_stem.with_suffix(".stderr").write_text(completed.stderr, encoding="utf-8")
    time_text = time_log.read_text(encoding="utf-8") if time_log.exists() else ""
    if completed.returncode != 0:
        raise RuntimeError(
            f"measurement failed ({completed.returncode}): {rendered}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    result = parse_result(completed.stdout)
    rss_match = RSS_RE.search(time_text)
    if not rss_match:
        raise RuntimeError(f"maximum RSS missing from {time_log}")
    return result, int(rss_match.group(1)), completed.returncode, completed.stdout, completed.stderr


def validate_all(
    binaries: dict[str, Any],
    implementations: list[str] | None = None,
    benchmarks: list[str] | None = None,
) -> None:
    selected = implementations or IMPLEMENTATIONS
    for benchmark in benchmarks or list(BENCHMARKS):
        expected = 146 if benchmark == "SBPF-program" else 6000
        for implementation in selected:
            binary = Path(binaries[implementation][benchmark]["runtime"]["path"])
            result, _, _, _, _ = run_binary(
                binary,
                benchmark,
                "correctness",
                1,
                RESULT_DIR / "correctness" / f"{benchmark}__{slug(implementation)}",
            )
            if int(result.get("passed", -1)) != expected or int(result.get("failed", -1)) != 0:
                raise RuntimeError(f"correctness failed for {benchmark} / {implementation}: {result}")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


RAW_FIELDS = [
    "benchmark",
    "implementation",
    "metric",
    "run_id",
    "process_id",
    "cpu",
    "input_sha256",
    "binary_sha256",
    "suite_repetitions",
    "logical_units",
    "elapsed_seconds",
    "normalized_seconds",
    "peak_rss_kib",
    "allocated_bytes",
    "host_instructions",
    "measurement_status",
    "exit_status",
]


def write_raw(rows: list[dict[str, Any]]) -> None:
    with (RESULT_DIR / "raw.csv").open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=RAW_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pilot_benchmarks(
    binaries: dict[str, Any],
    implementations: list[str] | None = None,
    benchmarks: list[str] | None = None,
) -> dict[str, dict[str, int]]:
    selected = implementations or IMPLEMENTATIONS
    repetitions: dict[str, dict[str, int]] = {}
    for benchmark in benchmarks or list(BENCHMARKS):
        repetitions[benchmark] = {}
        for implementation in selected:
            binary = Path(binaries[implementation][benchmark]["runtime"]["path"])
            result, _, _, _, _ = run_binary(
                binary,
                benchmark,
                "pilot",
                1,
                RESULT_DIR / "pilot" / f"{slug(benchmark)}__{slug(implementation)}",
            )
            elapsed = float(result["elapsed_seconds"])
            if elapsed <= 0.0:
                raise RuntimeError(
                    f"non-positive pilot time for {benchmark}/{implementation}: {elapsed}"
                )
            if implementation == "Case-study baseline":
                # Preserve the historical single-use-VM configuration. Every
                # repetition is prepared independently before measurement.
                repetitions[benchmark][implementation] = CASE_STUDY_REPETITIONS[
                    benchmark
                ]
                continue
            # Repeat only complete suites, preserving equal input weight while
            # targeting a seconds-scale aggregate.
            repetitions[benchmark][implementation] = max(
                1, math.ceil(RUNTIME_TARGET_SECONDS / elapsed)
            )
        if all(
            implementation in repetitions[benchmark]
            for implementation in ("Stage-2 minus Closure", "Stage-2 Full")
        ):
            paired_repetitions = max(
                repetitions[benchmark]["Stage-2 minus Closure"],
                repetitions[benchmark]["Stage-2 Full"],
            )
            repetitions[benchmark]["Stage-2 minus Closure"] = paired_repetitions
            repetitions[benchmark]["Stage-2 Full"] = paired_repetitions
        if all(
            implementation in repetitions[benchmark]
            for implementation in PREFER_OWNED_IMPLEMENTATIONS
        ):
            paired_repetitions = max(
                repetitions[benchmark][implementation]
                for implementation in PREFER_OWNED_IMPLEMENTATIONS
            )
            for implementation in PREFER_OWNED_IMPLEMENTATIONS:
                repetitions[benchmark][implementation] = paired_repetitions
    (RESULT_DIR / "suite_repetitions.json").write_text(
        json.dumps(repetitions, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return repetitions


def measure_all(
    binaries: dict[str, Any],
    environment: dict[str, Any],
    repetitions: dict[str, dict[str, int]],
    implementations: list[str] | None = None,
    benchmarks: list[str] | None = None,
) -> list[dict[str, Any]]:
    selected = implementations or IMPLEMENTATIONS
    selected_benchmarks = benchmarks or list(BENCHMARKS)
    rows: list[dict[str, Any]] = []
    input_hashes = {
        benchmark: environment["inputs"][benchmark]["sha256"] for benchmark in BENCHMARKS
    }
    if selected == STAGE2_IMPLEMENTATIONS:
        # Full and minus Closure form an adjacent counterbalanced block.
        # Alternating their order limits first/second-position bias, while the
        # within-round ratio limits round-wide frequency and background-load drift.
        round_orders = [
            [selected[3], selected[2], selected[0], selected[1]],
            [selected[0], selected[1], selected[2], selected[3]],
            [selected[1], selected[3], selected[2], selected[0]],
        ]
    elif selected == RUST_IMPLEMENTATIONS:
        round_orders = [
            [selected[4], selected[3], selected[0], selected[1], selected[2]],
            [selected[1], selected[2], selected[3], selected[4], selected[0]],
            [selected[0], selected[2], selected[1], selected[4], selected[3]],
        ]
    elif selected == DIAGNOSTIC_IMPLEMENTATIONS:
        round_orders = [
            [selected[2], selected[0], selected[1]],
            [selected[0], selected[1], selected[2]],
            [selected[1], selected[2], selected[0]],
        ]
    else:
        round_orders = [
            selected[offset:] + selected[:offset]
            for offset in range(3)
        ]
    for run_id in range(1, 4):
        order = round_orders[run_id - 1]
        for benchmark in selected_benchmarks:
            for metric in ("runtime", "allocation"):
                for implementation in order:
                    # Runtime needs a long timed region; allocation is a
                    # deterministic byte counter, so each allocation round uses
                    # one complete suite.
                    reps = (
                        repetitions[benchmark][implementation]
                        if metric == "runtime"
                        else 1
                    )
                    binary_info = binaries[implementation][benchmark][metric]
                    result, rss, exit_status, _, _ = run_binary(
                        Path(binary_info["path"]),
                        benchmark,
                        metric,
                        reps,
                        RESULT_DIR
                        / "runs"
                        / f"run-{run_id}"
                        / f"{benchmark}__{metric}__{slug(implementation)}",
                    )
                    elapsed = float(result["elapsed_seconds"])
                    allocation_unavailable = (
                        metric == "allocation"
                        and implementation == "Case-study baseline"
                    )
                    actual_repetitions = int(
                        result.get("suite_repetitions", "1")
                    )
                    rows.append(
                        {
                            "benchmark": benchmark,
                            "implementation": implementation,
                            "metric": metric,
                            "run_id": run_id,
                            "process_id": result["process_id"],
                            "cpu": CPU,
                            "input_sha256": input_hashes[benchmark],
                            "binary_sha256": binary_info["sha256"],
                            "suite_repetitions": actual_repetitions,
                            "logical_units": int(result["logical_units"]),
                            "elapsed_seconds": f"{elapsed:.9f}",
                            "normalized_seconds": f"{elapsed / actual_repetitions:.9f}",
                            "peak_rss_kib": rss,
                            "allocated_bytes": (
                                ""
                                if allocation_unavailable
                                else int(float(result["allocated_bytes"]))
                            ),
                            "host_instructions": "",
                            "measurement_status": (
                                "unavailable: non-comparable measurement boundary"
                                if allocation_unavailable
                                else "measured"
                            ),
                            "exit_status": exit_status,
                        }
                    )
                    write_raw(rows)
    return rows


def summarize(
    rows: list[dict[str, Any]],
    host_available: bool,
    implementations: list[str] | None = None,
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for benchmark in BENCHMARKS:
        for implementation in implementations or IMPLEMENTATIONS:
            runtime_rows = [
                row
                for row in rows
                if row["benchmark"] == benchmark
                and row["implementation"] == implementation
                and row["metric"] == "runtime"
            ]
            allocation_rows = [
                row
                for row in rows
                if row["benchmark"] == benchmark
                and row["implementation"] == implementation
                and row["metric"] == "allocation"
            ]
            runtime_values = [float(row["normalized_seconds"]) for row in runtime_rows]
            rss_values = [int(row["peak_rss_kib"]) / 1024.0 for row in runtime_rows]
            if implementation == "Case-study baseline":
                allocation_values = None
                allocation_unit = (
                    "MiB/case" if benchmark == "SBPF-program" else "KiB/step"
                )
            elif benchmark == "SBPF-program":
                allocation_values = [
                    int(row["allocated_bytes"]) / int(row["logical_units"]) / (1024.0**2)
                    for row in allocation_rows
                ]
                allocation_unit = "MiB/case"
                instruction_unit = "instructions/case"
            else:
                allocation_values = [
                    int(row["allocated_bytes"]) / int(row["logical_units"]) / 1024.0
                    for row in allocation_rows
                ]
                allocation_unit = "KiB/step"
                instruction_unit = "instructions/step"
            metrics = [
                ("Median runtime", "s", runtime_values),
                ("Peak RSS", "MiB", rss_values),
            ]
            for metric, unit, values in metrics:
                summary.append(
                    {
                        "benchmark": benchmark,
                        "implementation": implementation,
                        "metric": metric,
                        "unit": unit,
                        "run_1": f"{values[0]:.9f}",
                        "run_2": f"{values[1]:.9f}",
                        "run_3": f"{values[2]:.9f}",
                        "median": f"{statistics.median(values):.9f}",
                    }
                )
            summary.append(
                {
                    "benchmark": benchmark,
                    "implementation": implementation,
                    "metric": "Heap allocation",
                    "unit": allocation_unit,
                    "run_1": "unavailable" if allocation_values is None else f"{allocation_values[0]:.9f}",
                    "run_2": "unavailable" if allocation_values is None else f"{allocation_values[1]:.9f}",
                    "run_3": "unavailable" if allocation_values is None else f"{allocation_values[2]:.9f}",
                    "median": (
                        "unavailable"
                        if allocation_values is None
                        else f"{statistics.median(allocation_values):.9f}"
                    ),
                }
            )
            summary.append(
                {
                    "benchmark": benchmark,
                    "implementation": implementation,
                    "metric": "Host instructions",
                    "unit": instruction_unit,
                    "run_1": "TBD",
                    "run_2": "TBD",
                    "run_3": "TBD",
                    "median": "TBD" if not host_available else "TBD",
                }
            )
    fields = ["benchmark", "implementation", "metric", "unit", "run_1", "run_2", "run_3", "median"]
    with (RESULT_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)
    return summary


def write_grouped_ablation_summary(
    rows: list[dict[str, Any]],
    ablation_groups: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    paired = []
    for benchmark in BENCHMARKS:
        full_rows = sorted(
            (
                row
                for row in rows
                if row["benchmark"] == benchmark
                and row["implementation"] == "Stage-2 Full"
                and row["metric"] == "runtime"
            ),
            key=lambda row: int(row["run_id"]),
        )
        if len(full_rows) != 3:
            raise RuntimeError(f"expected three runtime rows for {benchmark}/Stage-2 Full")
        full = [float(row["normalized_seconds"]) for row in full_rows]

        for group, implementation in (ablation_groups or ABLATION_GROUPS).items():
            minus_rows = sorted(
                (
                    row
                    for row in rows
                    if row["benchmark"] == benchmark
                    and row["implementation"] == implementation
                    and row["metric"] == "runtime"
                ),
                key=lambda row: int(row["run_id"]),
            )
            if len(minus_rows) != 3:
                raise RuntimeError(
                    f"expected three runtime rows for {benchmark}/{implementation}"
                )
            minus = [float(row["normalized_seconds"]) for row in minus_rows]
            ratios = [
                minus_value / full_value
                for minus_value, full_value in zip(minus, full)
            ]
            median_ratio = statistics.median(minus) / statistics.median(full)
            full_wins = sum(ratio > 1.0 for ratio in ratios)
            paired.append(
                {
                    "benchmark": benchmark,
                    "ablated_group": group,
                    "implementation": implementation,
                    "run_1_minus_over_full": f"{ratios[0]:.9f}",
                    "run_2_minus_over_full": f"{ratios[1]:.9f}",
                    "run_3_minus_over_full": f"{ratios[2]:.9f}",
                    "median_minus_over_full": f"{median_ratio:.9f}",
                    "minus_cost_percent": f"{(median_ratio - 1.0) * 100.0:.6f}",
                    "full_speedup_percent": f"{(1.0 - 1.0 / median_ratio) * 100.0:.6f}",
                    "full_wins": full_wins,
                    "conclusion": (
                        "Full faster"
                        if median_ratio > 1.0
                        else f"{implementation} faster"
                        if median_ratio < 1.0
                        else "tie"
                    ),
                }
            )
    fields = list(paired[0])
    with (RESULT_DIR / "grouped_ablation.csv").open(
        "w", newline="", encoding="utf-8"
    ) as destination:
        writer = csv.DictWriter(destination, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(paired)
    return paired


def write_experiment_record(
    summary: list[dict[str, Any]],
    grouped_ablation: list[dict[str, Any]],
    environment: dict[str, Any],
    reused_from: Path | None = None,
    instruction_only: bool = False,
    rust_only: bool = False,
    diagnostic: bool = False,
    prefer_owned_ablation: bool = False,
    rust_refresh: bool = False,
    baseline_refresh: bool = False,
    ocaml_refresh: bool = False,
) -> None:
    git_dirty = bool(environment["git_status"].strip())
    paired_ablation = "PreferOwned" if prefer_owned_ablation else "Closure"
    ablation_kind = "policy" if prefer_owned_ablation else "pass"
    lines = [
        "# RQ3 SBPF experiment record",
        "",
        f"- Base Git commit: `{environment['git_commit']}`",
        (
            "- Git worktree: dirty at measurement time; `environment.json` records "
            "the status, and the configuration and binary manifests record exact "
            "optimizer, generated-source, and executable SHA-256 hashes."
            if git_dirty
            else "- Git worktree: clean at measurement time."
        ),
        f"- Measurement CPU: `{environment['measurement_cpu']}`",
        f"- SBPF-program input SHA-256: `{environment['inputs']['SBPF-program']['sha256']}`",
        f"- SBPF-instruction input SHA-256: `{environment['inputs']['SBPF-instruction']['sha256']}`",
        "- Numeric representation: every Rust Stage-1 and Stage-2 configuration uses the "
        "WordU128 layer and Checked128 Int/Nat profile; the OCaml baseline uses the fixed "
        "default export of the same Isabelle/HOL semantics.",
        (
            f"- Correctness: all {len(DIAGNOSTIC_IMPLEMENTATIONS)} diagnostic "
            "generated-Rust configurations passed 146/146 SBPF-program cases "
            "and 6000/6000 SBPF-instruction vectors."
            if diagnostic
            else "- Correctness: both PreferOwned configurations passed "
            "146/146 SBPF-program cases and 6000/6000 SBPF-instruction vectors."
            if prefer_owned_ablation
            else "- Correctness: all five generated-Rust configurations passed "
            "146/146 SBPF-program cases and 6000/6000 SBPF-instruction vectors."
            if rust_only
            else "- Correctness: the five regenerated Rust implementations passed "
            "146/146 SBPF-program cases and 6000/6000 SBPF-instruction vectors; "
            f"the unchanged OCaml and case-study baselines were reused from `{reused_from}`."
            if rust_refresh
            else "- Correctness: the rebuilt case-study baseline passed "
            "146/146 SBPF-program cases and 6000/6000 SBPF-instruction vectors; "
            f"all generated-semantics and OCaml rows were reused from `{reused_from}`."
            if baseline_refresh
            else "- Correctness: the rebuilt OCaml baseline passed "
            "146/146 SBPF-program cases and 6000/6000 SBPF-instruction vectors; "
            f"all generated-semantics and case-study rows were reused from `{reused_from}`."
            if ocaml_refresh
            else "- Correctness: the four newly measured Stage-2 SBPF-instruction implementations "
            "passed 6000/6000 vectors; the unchanged SBPF-program, Stage-1, OCaml, and "
            "case-study rows were reused from "
            f"`{reused_from}`."
            if instruction_only
            else
            "- Correctness: the four regenerated Stage-2 implementations passed "
            "146/146 SBPF-program cases and 6000/6000 SBPF-instruction vectors; "
            f"the unchanged Stage-1, OCaml, and case-study baselines were reused from `{reused_from}`."
            if reused_from
            else "- Correctness: all seven SBPF-program implementations passed 146/146 cases; "
            "all seven SBPF-instruction implementations passed 6000/6000 vectors."
        ),
        f"- Each value below is from an independent pinned process. Generated and OCaml pilots select whole-suite repetition counts targeting approximately {RUNTIME_TARGET_SECONDS:.0f} seconds. The prepared Solana baseline retains its historical configuration of {CASE_STUDY_REPETITIONS['SBPF-program']} SBPF-program suites and {CASE_STUDY_REPETITIONS['SBPF-instruction']} SBPF-instruction suite per process; every VM is independently constructed before measurement and executed once. Full and minus {paired_ablation} use the larger of their two pilot repetition counts and run adjacently with alternating order. Every ablation effect is the ratio of the minus-{ablation_kind} and Full configuration medians. Reused rows retain their recorded protocol. Each allocation round uses one complete suite. Runtime results are normalized per suite.",
        "- OCaml runtime uses `clock_gettime(CLOCK_MONOTONIC)` through a C stub.",
        "",
    ]
    lines.extend(
        [
            "## Diagnostic Stage-2 pass ablations"
            if diagnostic
            else "## PreferOwned ablation"
            if prefer_owned_ablation
            else "## Paper-facing Stage-2 ablations",
            "",
        ]
    )
    for row in grouped_ablation:
        lines.append(
            f"- {row['benchmark']} / {row['ablated_group']}: minus/Full ratios "
            f"{row['run_1_minus_over_full']}, {row['run_2_minus_over_full']}, "
            f"{row['run_3_minus_over_full']}; ratio of medians {row['median_minus_over_full']} "
            f"({row['conclusion']}, Full speedup {row['full_speedup_percent']}%, "
            f"Full wins {row['full_wins']}/3)."
        )
    lines.append("")
    host = environment["host_instructions"]
    if not host["available"]:
        lines.extend(
            [
                "Host instructions are `TBD`. The direct "
                f"`{host['syscall']}` probe failed with errno {host['errno']} "
                f"(`{host['error']}`), `perf_event_paranoid={host['perf_event_paranoid']}`, "
                "and no compatible `perf` executable was installed. No estimate was substituted.",
                "",
            ]
        )
    for benchmark in BENCHMARKS:
        lines.extend([f"## {benchmark}", ""])
        for metric in ("Median runtime", "Peak RSS", "Heap allocation", "Host instructions"):
            values = [
                row
                for row in summary
                if row["benchmark"] == benchmark and row["metric"] == metric
            ]
            unit = values[0]["unit"]
            lines.extend(
                [
                    f"### {metric} ({unit})",
                    "",
                    "| Implementation | Run 1 | Run 2 | Run 3 | Median |",
                    "|---|---:|---:|---:|---:|",
                ]
            )
            for row in values:
                lines.append(
                    f"| {row['implementation']} | {row['run_1']} | {row['run_2']} | "
                    f"{row['run_3']} | {row['median']} |"
                )
            lines.append("")
    lines.extend(
        [
            "## Artifacts",
            "",
            "- `environment.json`: host, toolchains, affinity, inputs, and counter probe.",
            "- `configurations.json`: pass matrix, source hashes, build settings, and executable hashes.",
            "- `raw.csv`: one row per formal measurement process.",
            "- `summary.csv`: the three values and median for every table cell.",
            "- `grouped_ablation.csv`: within-round minus-group/Full ratios and the ratio of the configuration medians.",
            "- `commands.txt`: every actual preparation, build, validation, pilot, and measurement command.",
            "- `correctness/`, `pilot/`, and `runs/`: per-process stdout, stderr, and `/usr/bin/time -v` output.",
            "",
        ]
    )
    (RESULT_DIR / "experiment-record.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--resume", type=Path)
    parser.add_argument(
        "--stage2-only-from",
        type=Path,
        help="reuse unchanged Stage-1/OCaml/case-study rows and rebuild the four paper-facing Stage-2 configurations",
    )
    parser.add_argument(
        "--rust-from",
        type=Path,
        help="regenerate and remeasure all five Rust configurations while reusing only OCaml/case-study baseline rows",
    )
    parser.add_argument(
        "--baseline-only-from",
        type=Path,
        help="rebuild and remeasure only the case-study baseline while reusing all other rows",
    )
    parser.add_argument(
        "--ocaml-only-from",
        type=Path,
        help="rebuild and remeasure only the OCaml baseline while reusing all other rows",
    )
    parser.add_argument(
        "--instruction-only-from",
        type=Path,
        help="reuse baselines and program rows, and remeasure only Stage-2 SBPF-instruction",
    )
    parser.add_argument(
        "--rust-only",
        action="store_true",
        help="measure only the five generated-Rust paper configurations",
    )
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="explicitly run only Stage-2 minus Copy, minus Mut, and Full",
    )
    parser.add_argument(
        "--prefer-owned-ablation",
        action="store_true",
        help="measure only Stage-2 minus PreferOwned and Stage-2 Full",
    )
    parser.add_argument(
        "--reuse-stage1-exports",
        action="store_true",
        help="use the existing raw Stage-1 exports instead of regenerating them",
    )
    args = parser.parse_args()
    global RESULT_DIR
    if not TIME.is_file():
        raise RuntimeError("/usr/bin/time is required")

    exclusive_modes = [
        args.resume,
        args.stage2_only_from,
        args.instruction_only_from,
        args.rust_from,
        args.baseline_only_from,
        args.ocaml_only_from,
    ]
    if sum(mode is not None for mode in exclusive_modes) > 1:
        parser.error(
            "--resume, --stage2-only-from, --instruction-only-from, --rust-from, and "
            "--baseline-only-from, and --ocaml-only-from are mutually exclusive"
        )
    if (args.diagnostic or args.prefer_owned_ablation) and (
        args.resume
        or args.stage2_only_from
        or args.instruction_only_from
        or args.rust_from
        or args.baseline_only_from
        or args.ocaml_only_from
        or args.rust_only
    ):
        parser.error(
            "targeted ablation modes cannot be combined with --resume, reuse modes, or --rust-only"
        )
    if args.diagnostic and args.prefer_owned_ablation:
        parser.error("--diagnostic and --prefer-owned-ablation are mutually exclusive")

    reused_from: Path | None = None
    instruction_only = args.instruction_only_from is not None
    rust_refresh = args.rust_from is not None
    baseline_refresh = args.baseline_only_from is not None
    ocaml_refresh = args.ocaml_only_from is not None
    if args.resume:
        RESULT_DIR = args.resume.resolve()
        environment = json.loads((RESULT_DIR / "environment.json").read_text(encoding="utf-8"))
        binaries = json.loads((RESULT_DIR / "binaries.json").read_text(encoding="utf-8"))
        configurations = json.loads(
            (RESULT_DIR / "configurations.json").read_text(encoding="utf-8")
        )
        if "rust_rerun" in configurations:
            rust_refresh = True
            reused_from = Path(
                configurations["rust_rerun"]["reused_unchanged_implementations_from"]
            )
    else:
        timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S%z")
        RESULT_DIR = RESULTS / timestamp
        RESULT_DIR.mkdir(parents=True)
        reused_from = (
            args.rust_from.resolve()
            if args.rust_from
            else args.baseline_only_from.resolve()
            if args.baseline_only_from
            else args.ocaml_only_from.resolve()
            if args.ocaml_only_from
            else args.stage2_only_from.resolve()
            if args.stage2_only_from
            else args.instruction_only_from.resolve()
            if args.instruction_only_from
            else None
        )
        if reused_from is None:
            if not args.reuse_stage1_exports:
                generate_exports()
            generate_step_input()
        elif rust_refresh and not args.reuse_stage1_exports:
            generate_exports(include_baseline=False)
        environment = record_environment()
        if instruction_only:
            configurations = json.loads(
                (reused_from / "configurations.json").read_text(encoding="utf-8")
            )
            binaries = json.loads((reused_from / "binaries.json").read_text(encoding="utf-8"))
            configurations["instruction_rerun"] = {
                "reused_binaries_and_unchanged_rows_from": str(reused_from),
                "regenerated_implementations": [],
                "remeasured_implementations": STAGE2_IMPLEMENTATIONS,
                "runtime_repetition_rule": (
                    f"whole-suite pilot target of at least {RUNTIME_TARGET_SECONDS:.0f} seconds "
                    "per process"
                ),
            }
        elif baseline_refresh:
            configurations = json.loads(
                (reused_from / "configurations.json").read_text(encoding="utf-8")
            )
            binaries = json.loads((reused_from / "binaries.json").read_text(encoding="utf-8"))
            configurations.pop("Case-study baseline", None)
            binaries.pop("Case-study baseline", None)
            build_case_study(configurations, binaries)
            configurations["numeric_representation"] = (
                "Rust WordU128 layer plus Checked128 Int/Nat profile for Stage-1 and every "
                "Stage-2 configuration; fixed default OCaml export; native Solana rBPF "
                "case-study baseline"
            )
            configurations["case_study_rerun"] = {
                "reused_unchanged_implementations_from": str(reused_from),
                "remeasured_implementation": "Case-study baseline",
                "measurement_boundary": configurations["Case-study baseline"][
                    "measurement_boundary"
                ],
                "runtime_suite_repetitions": configurations["Case-study baseline"][
                    "runtime_suite_repetitions"
                ],
                "allocation_scope": configurations["Case-study baseline"][
                    "allocation_scope"
                ],
            }
        elif ocaml_refresh:
            configurations = json.loads(
                (reused_from / "configurations.json").read_text(encoding="utf-8")
            )
            binaries = json.loads((reused_from / "binaries.json").read_text(encoding="utf-8"))
            configurations.pop("OCaml baseline", None)
            binaries.pop("OCaml baseline", None)
            build_ocaml(configurations, binaries)
            configurations["ocaml_rerun"] = {
                "reused_unchanged_implementations_from": str(reused_from),
                "remeasured_implementation": "OCaml baseline",
                "runtime_repetition_rule": (
                    f"whole-suite pilot target of at least {RUNTIME_TARGET_SECONDS:.0f} seconds "
                    "per process"
                ),
                "allocation_rule": "one complete suite per independent process",
                "clock": "clock_gettime(CLOCK_MONOTONIC) through an OCaml C stub",
            }
        elif reused_from is not None:
            configurations = json.loads(
                (reused_from / "configurations.json").read_text(encoding="utf-8")
            )
            binaries = json.loads((reused_from / "binaries.json").read_text(encoding="utf-8"))
            for key in list(configurations):
                if key.startswith("Stage-") if rust_refresh else key.startswith("Stage-2"):
                    del configurations[key]
            for key in list(binaries):
                if key.startswith("Stage-") if rust_refresh else key.startswith("Stage-2"):
                    del binaries[key]
            configurations["matrix_order"] = IMPLEMENTATIONS
            if rust_refresh:
                configurations["numeric_representation"] = (
                    "Rust WordU128 layer plus Checked128 Int/Nat profile for Stage-1 and every "
                    "Stage-2 configuration; unchanged OCaml/case-study baseline rows reused"
                )
            configurations["rust_rerun" if rust_refresh else "stage2_rerun"] = {
                "reused_unchanged_implementations_from": str(reused_from),
                "regenerated_implementations": (
                    RUST_IMPLEMENTATIONS if rust_refresh else STAGE2_IMPLEMENTATIONS
                ),
            }
            regenerated = RUST_IMPLEMENTATIONS if rust_refresh else STAGE2_IMPLEMENTATIONS
            prepare_generated(configurations, regenerated)
            build_generated(configurations, binaries, regenerated)
        else:
            selected_rust = (
                PREFER_OWNED_IMPLEMENTATIONS
                if args.prefer_owned_ablation
                else DIAGNOSTIC_IMPLEMENTATIONS
                if args.diagnostic
                else RUST_IMPLEMENTATIONS
            )
            configurations = {
                "matrix_order": (
                    PREFER_OWNED_IMPLEMENTATIONS
                    if args.prefer_owned_ablation
                    else DIAGNOSTIC_IMPLEMENTATIONS
                    if args.diagnostic
                    else RUST_IMPLEMENTATIONS
                    if args.rust_only
                    else IMPLEMENTATIONS
                ),
                "available_pass_level_ablations": [
                    "Copy",
                    "Borrow",
                    "Mut",
                    "Last-Use",
                    "Closure",
                ],
                "available_policy_ablations": ["PreferOwned"],
                "paper_facing_ablations": ["Borrow", "Last-Use", "Closure"],
                "diagnostic_mode": args.diagnostic,
                "prefer_owned_ablation": args.prefer_owned_ablation,
                "numeric_representation": (
                    "Rust WordU128 layer plus Checked128 Int/Nat profile for Stage-1 and every "
                    "Stage-2 configuration; fixed default OCaml export for the OCaml baseline"
                ),
                "rust_build": "cargo +stable build --release --locked",
                "allocation_rule": (
                    "Successful alloc and alloc_zeroed add layout.size(); successful realloc adds "
                    "new_size; dealloc subtracts nothing. The counter is reset immediately before "
                    "the measurement region."
                ),
            }
            binaries = {}
            prepare_generated(configurations, selected_rust)
            build_generated(configurations, binaries, selected_rust)
            if not args.rust_only and not args.diagnostic and not args.prefer_owned_ablation:
                build_ocaml(configurations, binaries)
                build_case_study(configurations, binaries)
        (RESULT_DIR / "configurations.json").write_text(
            json.dumps(configurations, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (RESULT_DIR / "binaries.json").write_text(
            json.dumps(binaries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if args.prepare_only:
            print(f"prepared experiment at {RESULT_DIR}")
            return 0

    selected = (
        PREFER_OWNED_IMPLEMENTATIONS
        if args.prefer_owned_ablation
        else DIAGNOSTIC_IMPLEMENTATIONS
        if args.diagnostic
        else RUST_IMPLEMENTATIONS
        if args.rust_only
        else ["Case-study baseline"]
        if baseline_refresh
        else ["OCaml baseline"]
        if ocaml_refresh
        else STAGE2_IMPLEMENTATIONS
        if instruction_only
        else RUST_IMPLEMENTATIONS
        if rust_refresh
        else IMPLEMENTATIONS
        if reused_from is None
        else STAGE2_IMPLEMENTATIONS
    )
    measured_benchmarks = ["SBPF-instruction"] if instruction_only else list(BENCHMARKS)
    validate_all(binaries, selected, measured_benchmarks)
    repetitions = pilot_benchmarks(binaries, selected, measured_benchmarks)
    rows = measure_all(binaries, environment, repetitions, selected, measured_benchmarks)
    if reused_from is not None:
        with (reused_from / "raw.csv").open(newline="", encoding="utf-8") as source:
            reused_rows = list(csv.DictReader(source))
        if instruction_only:
            baseline_rows = [
                row
                for row in reused_rows
                if row["benchmark"] != "SBPF-instruction"
                or not row["implementation"].startswith("Stage-2")
            ]
        elif baseline_refresh:
            baseline_rows = [
                row
                for row in reused_rows
                if row["implementation"] != "Case-study baseline"
            ]
        elif ocaml_refresh:
            baseline_rows = [
                row
                for row in reused_rows
                if row["implementation"] != "OCaml baseline"
            ]
        else:
            replaced_prefix = "Stage-" if rust_refresh else "Stage-2"
            baseline_rows = [
                row
                for row in reused_rows
                if not row["implementation"].startswith(replaced_prefix)
            ]
        rows = baseline_rows + rows
        write_raw(rows)
    summary = summarize(
        rows,
        environment["host_instructions"]["available"],
        selected
        if (args.rust_only or args.diagnostic or args.prefer_owned_ablation)
        and reused_from is None
        else None,
    )
    grouped_ablation = write_grouped_ablation_summary(
        rows,
        PREFER_OWNED_ABLATIONS
        if args.prefer_owned_ablation
        else DIAGNOSTIC_ABLATIONS
        if args.diagnostic
        else ABLATION_GROUPS,
    )
    write_experiment_record(
        summary,
        grouped_ablation,
        environment,
        reused_from,
        instruction_only,
        args.rust_only,
        args.diagnostic,
        args.prefer_owned_ablation,
        rust_refresh,
        baseline_refresh,
        ocaml_refresh,
    )
    print(json.dumps(summary, indent=2))
    print(f"RESULT_DIR={RESULT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
