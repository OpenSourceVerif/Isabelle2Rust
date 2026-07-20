#!/usr/bin/env python3
"""Prepare, validate, and measure the RQ3 SBPF performance matrix."""

from __future__ import annotations

import argparse
import csv
import ctypes
import errno
import hashlib
import json
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
HERE = Path(__file__).resolve().parent
DATA = ROOT / "tests_sbpf" / "tests" / "data"
PROGRAM_INPUT = DATA / "interp_in.json"
STEP_INPUT = DATA / "ocaml_in_6000.json"
DEFAULT_EXPORT = ROOT / "tests_sbpf" / "theory" / "stage1" / "bpf_generator"
ADAPTED_EXPORTS = {
    "interp_test": ROOT
    / "tests_sbpf"
    / "theory"
    / "stage1"
    / "bpf_generator_word_native_interp"
    / "interp_test",
    "step_test": ROOT
    / "tests_sbpf"
    / "theory"
    / "stage1"
    / "bpf_generator_word_native"
    / "step_test",
}
GENERATED_ROOT = ROOT / "tests_sbpf" / "theory" / "performance"
OPTIMIZER = ROOT / "optimize" / "target" / "release" / "cargo-opt"
BASELINE = HERE / "case-study-baseline"
BUILD = HERE / "build"
RESULTS = ROOT / "evaluation" / "performance" / "results"
TIME = Path("/usr/bin/time")
CPU = "0"
INSTRUCTION_SUITE_REPETITIONS = 17

IMPLEMENTATIONS = [
    "Stage-1",
    "Stage-2 minus Copy",
    "Stage-2 minus Borrow",
    "Stage-2 minus Mut",
    "Stage-2 Full",
    "OCaml baseline",
    "Case-study baseline",
]

STAGES = {
    "Stage-1": ("stage1", None, False),
    "Stage-2 minus Copy": ("stage2-no-copy", "--disable-copy", True),
    "Stage-2 minus Borrow": ("stage2-no-borrow", "--disable-borrow", False),
    "Stage-2 minus Mut": ("stage2-no-mut", "--disable-mut", True),
    "Stage-2 Full": ("stage2-full", None, True),
}

STAGE2_IMPLEMENTATIONS = [
    "Stage-2 minus Copy",
    "Stage-2 minus Borrow",
    "Stage-2 minus Mut",
    "Stage-2 Full",
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
            "check-cfg = ['cfg(sbpf_borrowed)', 'cfg(sbpf_native_int)', "
            "'cfg(allocation_metrics)'] }\n"
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


def write_stage_manifest(
    stage_dir: Path,
    implementation: str,
    flag: str | None,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    generated_hashes = {}
    for package, _, _ in BENCHMARKS.values():
        for source in sorted((stage_dir / package / "src").glob("*.rs")):
            generated_hashes[f"{package}/{source.name}"] = sha256(source)
    manifest = {
        "implementation": implementation,
        "optimizer_flag": flag,
        "source_stage1_sha256": source_hashes,
        "generated_source_sha256": generated_hashes,
        "optimizer_sha256": sha256(OPTIMIZER),
        "ownership_passes": {
            "copy": flag != "--disable-copy" and implementation != "Stage-1",
            "borrow": flag != "--disable-borrow" and implementation != "Stage-1",
            "mut": flag != "--disable-mut" and implementation != "Stage-1",
        },
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


def generate_exports() -> None:
    for theory in (
        "bpf_generator",
        "bpf_generator_word_native",
        "bpf_generator_word_native_interp",
    ):
        execute(
            [
                "make",
                "build",
                "TEST_DIR=tests_sbpf/theory",
                f"TEST_THEORY={theory}",
            ]
        )
    required = [
        DEFAULT_EXPORT / "interp_test.ocaml",
        DEFAULT_EXPORT / "step_test.ocaml",
        ADAPTED_EXPORTS["interp_test"] / "src" / "Interp_test.rs",
        ADAPTED_EXPORTS["step_test"] / "src" / "Step_test.rs",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing regenerated exports: {missing}")


def prepare_generated(
    configurations: dict[str, Any], implementations: list[str] | None = None
) -> None:
    selected = set(implementations or STAGES)
    execute(["cargo", "+stable", "build", "--release", "--locked"], cwd=ROOT / "optimize")
    source_hashes = {}
    for package, source_package in ADAPTED_EXPORTS.items():
        for source in sorted((source_package / "src").glob("*.rs")):
            source_hashes[f"{package}/{source.name}"] = sha256(source)
    for implementation, (directory, flag, borrowed) in STAGES.items():
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
                command = [str(OPTIMIZER), str(scratch / package), "--out-dir", str(stage_dir / package)]
                if flag:
                    command.append(flag)
                execute(command)
                add_benchmark_dependencies(stage_dir / package / "Cargo.toml")
            shutil.rmtree(scratch)

        for benchmark, (package, _, template) in BENCHMARKS.items():
            shutil.copy2(HERE / "rust" / template, stage_dir / package / "src" / "main.rs")
            execute(
                ["cargo", "+stable", "generate-lockfile", "--manifest-path", str(stage_dir / package / "Cargo.toml")]
            )
        configurations[implementation] = write_stage_manifest(
            stage_dir, implementation, flag, source_hashes
        )
        configurations[implementation]["borrowed_adapter"] = borrowed


def build_generated(
    configurations: dict[str, Any],
    binaries: dict[str, Any],
    implementations: list[str] | None = None,
) -> None:
    selected = set(implementations or STAGES)
    for implementation, (directory, _, borrowed) in STAGES.items():
        if implementation not in selected:
            continue
        binaries[implementation] = {}
        for benchmark, (package, _, _) in BENCHMARKS.items():
            package_dir = GENERATED_ROOT / directory / package
            binaries[implementation][benchmark] = {}
            for metric, allocation in (("runtime", False), ("allocation", True)):
                flags = ["--cfg sbpf_native_int"]
                if borrowed:
                    flags.append("--cfg sbpf_borrowed")
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
        shutil.copy2(HERE / "ocaml" / f"{short}.ml", build_dir / f"{short}.ml")
        packages = "zarith,yojson,unix"
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
        "source_export_sha256": {
            "interp_test.ocaml": sha256(DEFAULT_EXPORT / "interp_test.ocaml"),
            "step_test.ocaml": sha256(DEFAULT_EXPORT / "step_test.ocaml"),
        },
        "executables": binaries["OCaml baseline"],
    }


def build_case_study(configurations: dict[str, Any], binaries: dict[str, Any]) -> None:
    execute(["cargo", "+stable", "generate-lockfile"], cwd=BASELINE)
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
    "exit_status",
]


def write_raw(rows: list[dict[str, Any]]) -> None:
    with (RESULT_DIR / "raw.csv").open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=RAW_FIELDS)
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
            if benchmark == "SBPF-program":
                repetitions[benchmark][implementation] = 1 if elapsed >= 1.0 else 20
            else:
                # Keep all 6,000 fixed vectors in every traversal. Repeating
                # the complete suite 17 times yields 102,000 measured steps
                # per process while preserving equal weight for every vector.
                repetitions[benchmark][implementation] = INSTRUCTION_SUITE_REPETITIONS
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
        # Counterbalance the four-treatment order.  A simple cyclic rotation
        # preserves every predecessor relation and would place the much slower
        # minus-Mut treatment immediately before Full in all three rounds.
        # These three sequences expose Full and minus Copy to minus Mut once
        # each, give both the same position multiset {1, 3, 4}, and vary their
        # other predecessors.
        round_orders = [
            [selected[3], selected[2], selected[0], selected[1]],
            [selected[2], selected[1], selected[3], selected[0]],
            [selected[0], selected[1], selected[2], selected[3]],
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
                    # deterministic byte counter and one complete suite avoids
                    # needless work (especially for the Stage-1 baseline).
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
                    actual_repetitions = int(result.get("suite_repetitions", "1"))
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
                            "allocated_bytes": int(float(result["allocated_bytes"])),
                            "host_instructions": "",
                            "exit_status": exit_status,
                        }
                    )
                    write_raw(rows)
    return rows


def summarize(rows: list[dict[str, Any]], host_available: bool) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for benchmark in BENCHMARKS:
        for implementation in IMPLEMENTATIONS:
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
            if benchmark == "SBPF-program":
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
                ("Heap allocation", allocation_unit, allocation_values),
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
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary)
    return summary


def write_experiment_record(
    summary: list[dict[str, Any]],
    environment: dict[str, Any],
    reused_from: Path | None = None,
    instruction_only: bool = False,
) -> None:
    lines = [
        "# RQ3 SBPF experiment record",
        "",
        f"- Git commit: `{environment['git_commit']}`",
        f"- Measurement CPU: `{environment['measurement_cpu']}`",
        f"- SBPF-program input SHA-256: `{environment['inputs']['SBPF-program']['sha256']}`",
        f"- SBPF-instruction input SHA-256: `{environment['inputs']['SBPF-instruction']['sha256']}`",
        "- Numeric representation: every Rust Stage-1 and Stage-2 configuration uses the "
        "Word adapter and hybrid Native Int/Nat adapter; the OCaml baseline uses the fixed "
        "default export of the same Isabelle/HOL semantics.",
        (
            "- Correctness: the four newly measured Stage-2 SBPF-instruction implementations "
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
        "- Each value below is from an independent pinned process. For runtime, SBPF-program uses one traversal when it takes at least one second and exactly 20 traversals otherwise. The newly measured Stage-2 SBPF-instruction rows repeat the fixed 6000-vector suite 17 times (102,000 steps); unchanged baseline rows retain their recorded protocol. Heap allocation uses one complete suite because its byte count is deterministic. Runtime results are normalized per suite, and every metric is reported as the median of three process runs.",
        "",
    ]
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
        help="reuse unchanged Stage-1/OCaml/case-study rows and rebuild only four Stage-2 variants",
    )
    parser.add_argument(
        "--instruction-only-from",
        type=Path,
        help="reuse baselines and program rows, and remeasure only Stage-2 SBPF-instruction",
    )
    args = parser.parse_args()
    global RESULT_DIR
    if not TIME.is_file():
        raise RuntimeError("/usr/bin/time is required")

    exclusive_modes = [args.resume, args.stage2_only_from, args.instruction_only_from]
    if sum(mode is not None for mode in exclusive_modes) > 1:
        parser.error(
            "--resume, --stage2-only-from, and --instruction-only-from are mutually exclusive"
        )

    reused_from: Path | None = None
    instruction_only = args.instruction_only_from is not None
    if args.resume:
        RESULT_DIR = args.resume.resolve()
        environment = json.loads((RESULT_DIR / "environment.json").read_text(encoding="utf-8"))
        binaries = json.loads((RESULT_DIR / "binaries.json").read_text(encoding="utf-8"))
    else:
        timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S%z")
        RESULT_DIR = RESULTS / timestamp
        RESULT_DIR.mkdir(parents=True)
        reused_from = (
            args.stage2_only_from.resolve()
            if args.stage2_only_from
            else args.instruction_only_from.resolve()
            if args.instruction_only_from
            else None
        )
        if reused_from is None:
            generate_exports()
            generate_step_input()
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
                "suite_repetitions": INSTRUCTION_SUITE_REPETITIONS,
                "measured_steps_per_process": 6000 * INSTRUCTION_SUITE_REPETITIONS,
            }
        elif reused_from is not None:
            configurations = json.loads(
                (reused_from / "configurations.json").read_text(encoding="utf-8")
            )
            binaries = json.loads((reused_from / "binaries.json").read_text(encoding="utf-8"))
            configurations["stage2_rerun"] = {
                "reused_unchanged_implementations_from": str(reused_from),
                "regenerated_implementations": STAGE2_IMPLEMENTATIONS,
            }
            prepare_generated(configurations, STAGE2_IMPLEMENTATIONS)
            build_generated(configurations, binaries, STAGE2_IMPLEMENTATIONS)
        else:
            configurations = {
                "matrix_order": IMPLEMENTATIONS,
                "numeric_representation": (
                    "Rust Word adapter plus hybrid native Int/Nat adapter for Stage-1 and every "
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
            prepare_generated(configurations)
            build_generated(configurations, binaries)
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
        STAGE2_IMPLEMENTATIONS
        if instruction_only
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
            baseline_rows = [
                row
                for row in csv.DictReader(source)
                if (
                    row["benchmark"] != "SBPF-instruction"
                    or row["implementation"] not in STAGE2_IMPLEMENTATIONS
                    if instruction_only
                    else row["implementation"] not in STAGE2_IMPLEMENTATIONS
                )
            ]
        rows = baseline_rows + rows
        write_raw(rows)
    summary = summarize(rows, environment["host_instructions"]["available"])
    write_experiment_record(summary, environment, reused_from, instruction_only)
    print(json.dumps(summary, indent=2))
    print(f"RESULT_DIR={RESULT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
