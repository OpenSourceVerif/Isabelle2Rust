#!/usr/bin/env python3
"""Prepare, validate, and measure the RQ3 x64-stepper matrix."""

from __future__ import annotations

import argparse
import csv
import ctypes
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
X64_HARNESS = HARNESS / "x64"
VALIDATION = ROOT / "tests_x64" / "x64-validation"
WORK = ROOT / "evaluation" / ".work" / "rq3" / "x64"
FIXED_INPUT = X64_HARNESS / "data" / "x64_step_6000.json"
RAW_EXPORT = (
    ROOT
    / "tests_x64"
    / "theory"
    / "stage1"
    / "x64StepRustPerformanceGenerator"
    / "x64_step_test"
)
GENERATED_ROOT = ROOT / "tests_x64" / "theory" / "performance" / "x64"
OPTIMIZER = ROOT / "optimize" / "target" / "release" / "cargo-opt"
RUSTLIGHTAST = ROOT.parent / "RustLightAST"
BUILD = WORK / "build"
RESULTS = WORK / "runs"
EXPORTER = VALIDATION / "run_rust_export.py"
TIME = Path("/usr/bin/time")
CPU = "0"
CASE_COUNT = 6000
RUNTIME_TARGET_SECONDS = 5.0

STAGES = {
    "Stage-1": ("stage1", [], False),
    "Stage-2 minus Borrow": ("stage2-no-borrow", ["--disable-borrow"], False),
    "Stage-2 minus Last-Use": (
        "stage2-no-last-use",
        ["--disable-last-use"],
        False,
    ),
    "Stage-2 minus Closure": (
        "stage2-no-closure",
        ["--disable-closure"],
        False,
    ),
    "Stage-2 Full": ("stage2-full", [], False),
    "Stage-2 minus Copy": ("stage2-no-copy", ["--disable-copy"], False),
    "Stage-2 minus Mut": ("stage2-no-mut", ["--disable-mut"], False),
    "Stage-2 minus PreferOwned": (
        "stage2-no-prefer-owned",
        ["--disable-prefer-owned"],
        False,
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
    "Native x64 baseline",
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


def output(command: list[str], cwd: Path = ROOT) -> str:
    return subprocess.check_output(
        command, cwd=cwd, text=True, stderr=subprocess.STDOUT
    ).strip()


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("RUSTC_BOOTSTRAP", None)
    env.pop("RUSTFLAGS", None)
    if extra:
        env.update(extra)
    return env


def command_text(command: list[str], env: dict[str, str] | None = None) -> str:
    visible = {}
    if env:
        visible = {
            key: value
            for key, value in env.items()
            if key
            in {
                "CARGO_TARGET_DIR",
                "CROSS_JSON",
                "RUSTFLAGS",
                "RUST_TOOLCHAIN",
                "SUITE_REPETITIONS",
                "X64_MEASURE",
            }
        }
    prefix = " ".join(
        f"{key}={shlex.quote(value)}" for key, value in sorted(visible.items())
    )
    return (prefix + " " if prefix else "") + shlex.join(command)


def save_commands() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "commands.txt").write_text(
        "\n".join(COMMANDS) + "\n", encoding="utf-8"
    )


def execute(
    command: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    rendered = command_text(command, env)
    COMMANDS.append(f"cd {shlex.quote(str(cwd))} && {rendered}")
    save_commands()
    print(f">>> {rendered}", flush=True)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=clean_env(env),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.returncode != 0 and completed.stderr:
        print(
            completed.stderr,
            file=sys.stderr,
            end="" if completed.stderr.endswith("\n") else "\n",
        )
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode, command, completed.stdout, completed.stderr
        )
    return completed


def validate_input() -> None:
    fixed = json.loads(FIXED_INPUT.read_text(encoding="utf-8"))
    if len(fixed) != CASE_COUNT:
        raise RuntimeError(
            f"{FIXED_INPUT} contains {len(fixed)} vectors; {CASE_COUNT} required"
        )


def generate_rust_export() -> None:
    execute(
        ["python3", str(EXPORTER), "performance"],
        env={"RUST_TOOLCHAIN": "stable"},
    )
    required = [
        RAW_EXPORT / "Cargo.toml",
        RAW_EXPORT / "src" / "X64_step_test.rs",
        RAW_EXPORT / "src" / "Rust_Checked128.rs",
        RAW_EXPORT / "src" / "Rust_Word.rs",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing x64 performance export files: {missing}")


def add_benchmark_dependencies(manifest: Path) -> None:
    text = manifest.read_text(encoding="utf-8")
    if "serde =" not in text:
        text = text.replace(
            "[lints.rust]",
            'serde = { version = "1.0", features = ["derive"] }\n'
            'serde_json = "1.0"\n\n[lints.rust]',
            1,
        )
    if "unexpected_cfgs" not in text:
        text = text.rstrip() + (
            "\nunexpected_cfgs = { level = \"allow\", "
            "check-cfg = ['cfg(x64_borrowed)', 'cfg(allocation_metrics)'] }\n"
        )
    manifest.write_text(text, encoding="utf-8")


def copy_clean_package(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    (destination / "src").mkdir(parents=True)
    shutil.copy2(source / "Cargo.toml", destination / "Cargo.toml")
    for rust_source in sorted((source / "src").glob("*.rs")):
        shutil.copy2(rust_source, destination / "src" / rust_source.name)


def install_rust_harness(package: Path) -> None:
    module = package / "src" / "X64_step_test.rs"
    with module.open("a", encoding="utf-8") as destination:
        destination.write("\n")
        destination.write(
            (X64_HARNESS / "rust" / "observe.rs").read_text(encoding="utf-8")
        )
    shutil.copy2(
        X64_HARNESS / "rust" / "stepper.rs",
        package / "src" / "main.rs",
    )
    add_benchmark_dependencies(package / "Cargo.toml")
    execute(
        [
            "cargo",
            "+stable",
            "generate-lockfile",
            "--offline",
            "--manifest-path",
            str(package / "Cargo.toml"),
        ]
    )


def source_shape_metrics(package: Path) -> dict[str, int]:
    sources = sorted((package / "src").glob("*.rs"))
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
    package: Path,
    implementation: str,
    optimizer_flags: list[str],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    optimized = implementation != "Stage-1"
    generated_hashes = {
        source.name: sha256(source)
        for source in sorted((package / "src").glob("*.rs"))
    }
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
        "source_shape": source_shape_metrics(package),
    }
    (package.parent / "configuration.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def prepare_generated(
    configurations: dict[str, Any], implementations: list[str] | None = None
) -> None:
    selected = set(implementations or RUST_IMPLEMENTATIONS)
    if any(implementation != "Stage-1" for implementation in selected):
        execute(["cargo", "+stable", "build", "--release", "--locked"], cwd=ROOT / "optimize")
    source_hashes = {
        source.name: sha256(source)
        for source in sorted((RAW_EXPORT / "src").glob("*.rs"))
    }
    for implementation, (directory, optimizer_flags, _) in STAGES.items():
        if implementation not in selected:
            continue
        package = GENERATED_ROOT / directory / "x64_step_test"
        if package.parent.exists():
            shutil.rmtree(package.parent)
        if implementation == "Stage-1":
            copy_clean_package(RAW_EXPORT, package)
        else:
            scratch = GENERATED_ROOT / ".stage1-source" / "x64_step_test"
            copy_clean_package(RAW_EXPORT, scratch)
            command = [
                str(OPTIMIZER),
                str(scratch),
                "--out-dir",
                str(package),
                *optimizer_flags,
            ]
            execute(command)
            shutil.rmtree(scratch.parent)
        install_rust_harness(package)
        configurations[implementation] = write_stage_manifest(
            package, implementation, optimizer_flags, source_hashes
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
        package = GENERATED_ROOT / directory / "x64_step_test"
        binaries[implementation] = {"x64-stepper": {}}
        for metric, allocation in (("runtime", False), ("allocation", True)):
            flags = []
            if borrowed:
                flags.append("--cfg x64_borrowed")
            if allocation:
                flags.append("--cfg allocation_metrics")
            target = package / "target" / metric
            env = {"CARGO_TARGET_DIR": str(target)}
            if flags:
                env["RUSTFLAGS"] = " ".join(flags)
            execute(
                ["cargo", "+stable", "build", "--release", "--locked"],
                cwd=package,
                env=env,
            )
            binary = target / "release" / "isabelle_exported"
            binaries[implementation]["x64-stepper"][metric] = {
                "path": str(binary),
                "sha256": sha256(binary),
                "rustflags": env.get("RUSTFLAGS", ""),
            }
        configurations[implementation]["borrowed_adapter"] = borrowed
        configurations[implementation]["entry_point_calling_convention"] = (
            "by value for all five x64_step_test arguments; borrow optimization remains active inside the generated semantics when enabled"
        )
        configurations[implementation]["executables"] = binaries[implementation]


OCAML_SIGNATURE_EXTENSION = """  val int64_to_myint : int64 -> myint
  val int64_list_to_myint_list : int64 list -> myint list
  val x64_step_observe :
    myint -> myint list -> myint list -> myint list -> myint list -> int64 list
  val x64_step_benchmark :
    myint -> myint list -> myint list -> myint list -> myint list -> unit
"""

OCAML_GLUE = r"""
let rec num_of_z value =
  if Z.equal value Z.one then One
  else
    let quotient, remainder = Z.ediv_rem value (Z.of_int 2) in
    if Z.equal remainder Z.zero then Bit0 (num_of_z quotient)
    else Bit1 (num_of_z quotient)

let int64_to_myint value =
  let value = Z.of_int64 value in
  if Z.equal value Z.zero then Zero_int
  else if Z.sign value > 0 then Pos (num_of_z value)
  else Neg (num_of_z (Z.neg value))

let int64_list_to_myint_list values = List.map int64_to_myint values

let rec num_to_int64 = function
  | One -> 1L
  | Bit0 value -> Int64.mul 2L (num_to_int64 value)
  | Bit1 value -> Int64.add (Int64.mul 2L (num_to_int64 value)) 1L

let myint_to_int64 = function
  | Zero_int -> 0L
  | Pos value -> num_to_int64 value
  | Neg value -> Int64.neg (num_to_int64 value)

let ireg_table = [
  RAX; RBX; RCX; RDX; RSI; RDI; RBP; RSP;
  R8; R9; R10; R11; R12; R13; R14
]

let crbit_table = [ZF; CF; PF; SF; OF]
let preg_list = PC :: List.map (fun register -> IR register) ireg_table
  @ List.map (fun flag -> CR flag) crbit_table
let len8 = len_bit0 (len_bit0 (len_bit0 len_num1))
let len16 = len_bit0 len8
let len32 = len_bit0 len16
let len64 = len_bit0 len32

let int64_of_vala = function
  | Vundef -> 0L
  | Vbyte word -> myint_to_int64 (the_int len8 word)
  | Vshort word -> myint_to_int64 (the_int len16 word)
  | Vint word -> myint_to_int64 (the_int len32 word)
  | Vlong word -> myint_to_int64 (the_int len64 word)

let x64_step_observe bits lbin lc lr lm =
  match x64_step_test bits lbin lc lr lm with
  | Stuck -> []
  | Next (registers, _) ->
      List.map (fun register -> int64_of_vala (registers register)) preg_list

let x64_step_benchmark bits lbin lc lr lm =
  ignore (Sys.opaque_identity (x64_step_test bits lbin lc lr lm))

"""


def glue_ocaml(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = re.sub(r"\bmodule\s+x64_step_test\b", "module X64_step_test", text, count=1)
    text = re.sub(r"\bint\b", "myint", text)
    signature_end = "end = struct"
    ending = "end;; (*struct x64_step_test*)"
    if signature_end not in text or ending not in text:
        raise RuntimeError(f"OCaml glue marker missing in {source}")
    text = text.replace(signature_end, OCAML_SIGNATURE_EXTENSION + signature_end, 1)
    text = text.replace(ending, OCAML_GLUE + ending, 1)
    destination.write_text(text, encoding="utf-8")


def build_ocaml(configurations: dict[str, Any], binaries: dict[str, Any]) -> None:
    compiler = output(["ocamlopt", "-version"])
    if compiler != "4.11.2":
        raise RuntimeError(f"expected ocamlopt 4.11.2, got {compiler}")
    source = (
        ROOT
        / "tests_x64"
        / "theory"
        / "stage1"
        / "x64StepGenerator"
        / "x64_step_test.ocaml"
    )
    build_dir = BUILD / "ocaml"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    module = build_dir / "x64_step_test.ml"
    glue_ocaml(source, module)
    shutil.copy2(
        X64_HARNESS / "ocaml" / "stepper.ml",
        build_dir / "stepper.ml",
    )
    shutil.copy2(
        HARNESS / "common" / "monotonic_stubs.c",
        build_dir / "monotonic_stubs.c",
    )
    packages = "zarith,yojson,unix"
    execute(["ocamlfind", "ocamlopt", "-c", "monotonic_stubs.c"], cwd=build_dir)
    execute(
        ["ocamlfind", "ocamlopt", "-package", packages, "-linkpkg", "-c", module.name],
        cwd=build_dir,
    )
    binary = build_dir / "x64-stepper-ocaml"
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
            "x64_step_test.cmx",
            "stepper.ml",
        ],
        cwd=build_dir,
    )
    binary_info = {"path": str(binary), "sha256": sha256(binary)}
    binaries["OCaml baseline"] = {
        "x64-stepper": {"runtime": binary_info, "allocation": binary_info}
    }
    configurations["OCaml baseline"] = {
        "compiler": f"ocamlopt {compiler}",
        "runtime_clock": "clock_gettime(CLOCK_MONOTONIC) through an OCaml C stub",
        "source_export_sha256": sha256(source),
        "executables": binaries["OCaml baseline"],
    }


def build_native(configurations: dict[str, Any], binaries: dict[str, Any]) -> None:
    build_dir = BUILD / "native"
    build_dir.mkdir(parents=True, exist_ok=True)
    binary = build_dir / "x64-stepper-native"
    cflags = shlex.split(output(["pkg-config", "--cflags", "jansson"]))
    libs = shlex.split(output(["pkg-config", "--libs", "jansson"]))
    command = [
        "cc",
        "-O2",
        "-Wall",
        "-Wextra",
        "-std=c11",
        "-Wl,--wrap=malloc",
        "-Wl,--wrap=calloc",
        "-Wl,--wrap=realloc",
        *cflags,
        str(X64_HARNESS / "native" / "stepper.c"),
        "-o",
        str(binary),
        *libs,
    ]
    execute(command)
    binary_info = {"path": str(binary), "sha256": sha256(binary)}
    binaries["Native x64 baseline"] = {
        "x64-stepper": {"runtime": binary_info, "allocation": binary_info}
    }
    configurations["Native x64 baseline"] = {
        "compiler": output(["cc", "--version"]).splitlines()[0],
        "jansson": output(["pkg-config", "--modversion", "jansson"]),
        "source_sha256": sha256(X64_HARNESS / "native" / "stepper.c"),
        "core_operation": "ptrace-driven execution of one encoded instruction",
        "allocation_rule": (
            "Successful malloc and calloc requests, and successful realloc requests, "
            "contribute their requested size to a cumulative counter that is reset "
            "immediately before the prepared step loop. This counter excludes prepared "
            "state and OS-managed ptrace resources, so cross-implementation allocation "
            "is reported as unavailable."
        ),
        "executables": binaries["Native x64 baseline"],
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
    attribute.config = 1
    attribute.flags = 1
    libc = ctypes.CDLL(None, use_errno=True)
    fd = libc.syscall(298, ctypes.byref(attribute), 0, -1, -1, 0)
    error = ctypes.get_errno()
    if fd >= 0:
        os.close(fd)
    paranoid = Path("/proc/sys/kernel/perf_event_paranoid")
    return {
        "available": fd >= 0,
        "errno": error,
        "error": os.strerror(error) if error else None,
        "perf_event_paranoid": paranoid.read_text().strip() if paranoid.exists() else None,
    }


def record_environment() -> dict[str, Any]:
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
        "cc": output(["cc", "--version"]).splitlines()[0],
        "cpu_affinity_before": sorted(os.sched_getaffinity(0)),
        "measurement_cpu": int(CPU),
        "input": {
            "path": str(FIXED_INPUT),
            "sha256": sha256(FIXED_INPUT),
            "cases": CASE_COUNT,
            "selection": "frozen x64 native-observation corpus",
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


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def run_binary(
    binary: Path, metric: str, repetitions: int, log_stem: Path
) -> tuple[dict[str, str], int, int]:
    log_stem.parent.mkdir(parents=True, exist_ok=True)
    env = {
        "CROSS_JSON": str(FIXED_INPUT),
        "X64_MEASURE": metric,
        "SUITE_REPETITIONS": str(repetitions),
    }
    time_log = log_stem.with_suffix(".time")
    command = [str(TIME), "-v", "-o", str(time_log), "taskset", "-c", CPU, str(binary)]
    rendered = command_text(command, env)
    COMMANDS.append(f"cd {shlex.quote(str(ROOT))} && {rendered}")
    save_commands()
    print(f">>> x64-stepper | {metric} | {log_stem.name}", flush=True)
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
    return result, int(rss_match.group(1)), completed.returncode


def validate_all(
    binaries: dict[str, Any], implementations: list[str] | None = None
) -> None:
    for implementation in implementations or IMPLEMENTATIONS:
        binary = Path(binaries[implementation]["x64-stepper"]["runtime"]["path"])
        result, _, _ = run_binary(
            binary,
            "correctness",
            1,
            RESULT_DIR / "correctness" / slug(implementation),
        )
        if int(result.get("passed", -1)) != CASE_COUNT or int(result.get("failed", -1)) != 0:
            raise RuntimeError(f"correctness failed for {implementation}: {result}")


def pilot_all(
    binaries: dict[str, Any], implementations: list[str] | None = None
) -> dict[str, int]:
    selected = implementations or IMPLEMENTATIONS
    repetitions = {}
    for implementation in selected:
        binary = Path(binaries[implementation]["x64-stepper"]["runtime"]["path"])
        result, _, _ = run_binary(
            binary, "pilot", 1, RESULT_DIR / "pilot" / slug(implementation)
        )
        elapsed = float(result["elapsed_seconds"])
        if elapsed <= 0.0:
            raise RuntimeError(
                f"non-positive pilot time for {implementation}: {elapsed}"
            )
        # The fixed 17-traversal SBPF instruction protocol lasts long enough for
        # that workload, but only about 0.3 seconds for optimized x64.  Select a
        # per-implementation whole-suite batch here so every independent timing
        # process measures at least five seconds according to its pilot.
        repetitions[implementation] = max(
            1, math.ceil(RUNTIME_TARGET_SECONDS / elapsed)
        )
    if all(
        implementation in repetitions
        for implementation in ("Stage-2 minus Closure", "Stage-2 Full")
    ):
        paired_repetitions = max(
            repetitions["Stage-2 minus Closure"], repetitions["Stage-2 Full"]
        )
        repetitions["Stage-2 minus Closure"] = paired_repetitions
        repetitions["Stage-2 Full"] = paired_repetitions
    if all(
        implementation in repetitions
        for implementation in PREFER_OWNED_IMPLEMENTATIONS
    ):
        paired_repetitions = max(
            repetitions[implementation]
            for implementation in PREFER_OWNED_IMPLEMENTATIONS
        )
        for implementation in PREFER_OWNED_IMPLEMENTATIONS:
            repetitions[implementation] = paired_repetitions
    (RESULT_DIR / "suite_repetitions.json").write_text(
        json.dumps(repetitions, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return repetitions


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
    "measurement_status",
    "exit_status",
]


def write_raw(rows: list[dict[str, Any]]) -> None:
    with (RESULT_DIR / "raw.csv").open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=RAW_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def measure_all(
    binaries: dict[str, Any],
    environment: dict[str, Any],
    repetitions: dict[str, int],
    implementations: list[str] | None = None,
) -> list[dict[str, Any]]:
    selected = implementations or IMPLEMENTATIONS
    rows: list[dict[str, Any]] = []
    if selected == IMPLEMENTATIONS:
        round_orders = [
            [selected[4], selected[3], selected[0], selected[1], selected[2], selected[5], selected[6]],
            [selected[0], selected[1], selected[2], selected[3], selected[4], selected[5], selected[6]],
            [selected[0], selected[1], selected[2], selected[5], selected[6], selected[4], selected[3]],
        ]
    elif selected == RUST_IMPLEMENTATIONS:
        round_orders = [
            [selected[4], selected[3], selected[0], selected[1], selected[2]],
            [selected[0], selected[1], selected[2], selected[3], selected[4]],
            [selected[0], selected[2], selected[1], selected[4], selected[3]],
        ]
    elif selected == STAGE2_IMPLEMENTATIONS:
        round_orders = [
            [selected[3], selected[2], selected[0], selected[1]],
            [selected[0], selected[1], selected[2], selected[3]],
            [selected[1], selected[3], selected[2], selected[0]],
        ]
    elif selected == DIAGNOSTIC_IMPLEMENTATIONS:
        round_orders = [
            [selected[2], selected[0], selected[1]],
            [selected[0], selected[1], selected[2]],
            [selected[1], selected[2], selected[0]],
        ]
    else:
        round_orders = [selected[offset:] + selected[:offset] for offset in range(3)]
    for run_id in range(1, 4):
        order = round_orders[run_id - 1]
        for metric in ("runtime", "allocation"):
            for implementation in order:
                reps = repetitions[implementation] if metric == "runtime" else 1
                binary_info = binaries[implementation]["x64-stepper"][metric]
                result, rss, status = run_binary(
                    Path(binary_info["path"]),
                    metric,
                    reps,
                    RESULT_DIR
                    / "runs"
                    / f"run-{run_id}"
                    / f"{metric}__{slug(implementation)}",
                )
                elapsed = float(result["elapsed_seconds"])
                allocation_unavailable = (
                    metric == "allocation"
                    and implementation == "Native x64 baseline"
                )
                actual_repetitions = int(result["suite_repetitions"])
                rows.append(
                    {
                        "benchmark": "x64-stepper",
                        "implementation": implementation,
                        "metric": metric,
                        "run_id": run_id,
                        "process_id": result["process_id"],
                        "cpu": CPU,
                        "input_sha256": environment["input"]["sha256"],
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
                        "measurement_status": (
                            "unavailable: non-comparable measurement boundary"
                            if allocation_unavailable
                            else "measured"
                        ),
                        "exit_status": status,
                    }
                )
                write_raw(rows)
    return rows


def summarize(
    rows: list[dict[str, Any]], implementations: list[str] | None = None
) -> list[dict[str, Any]]:
    selected = implementations or IMPLEMENTATIONS
    summary = []
    for implementation in selected:
        runtime_rows = [
            row for row in rows if row["implementation"] == implementation and row["metric"] == "runtime"
        ]
        allocation_rows = [
            row for row in rows if row["implementation"] == implementation and row["metric"] == "allocation"
        ]
        metrics = [
            ("Median runtime", "s", [float(row["normalized_seconds"]) for row in runtime_rows]),
            ("Peak RSS", "MiB", [int(row["peak_rss_kib"]) / 1024.0 for row in runtime_rows]),
        ]
        for metric, unit, values in metrics:
            if len(values) != 3:
                raise RuntimeError(f"expected three {metric} rows for {implementation}")
            summary.append(
                {
                    "benchmark": "x64-stepper",
                    "implementation": implementation,
                    "metric": metric,
                    "unit": unit,
                    "run_1": f"{values[0]:.9f}",
                    "run_2": f"{values[1]:.9f}",
                    "run_3": f"{values[2]:.9f}",
                    "median": f"{statistics.median(values):.9f}",
                }
            )
        allocation_values = (
            None
            if implementation == "Native x64 baseline"
            else [
                int(row["allocated_bytes"]) / int(row["logical_units"]) / 1024.0
                for row in allocation_rows
            ]
        )
        summary.append(
            {
                "benchmark": "x64-stepper",
                "implementation": implementation,
                "metric": "Heap allocation",
                "unit": "KiB/step",
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
    full_rows = sorted(
        (
            row
            for row in rows
            if row["implementation"] == "Stage-2 Full"
            and row["metric"] == "runtime"
        ),
        key=lambda row: int(row["run_id"]),
    )
    if len(full_rows) != 3:
        raise RuntimeError("expected three runtime rows for Stage-2 Full")
    full = [float(row["normalized_seconds"]) for row in full_rows]

    results = []
    for group, implementation in (ablation_groups or ABLATION_GROUPS).items():
        minus_rows = sorted(
            (
                row
                for row in rows
                if row["implementation"] == implementation
                and row["metric"] == "runtime"
            ),
            key=lambda row: int(row["run_id"]),
        )
        if len(minus_rows) != 3:
            raise RuntimeError(f"expected three runtime rows for {implementation}")
        minus = [float(row["normalized_seconds"]) for row in minus_rows]
        ratios = [
            minus_value / full_value
            for minus_value, full_value in zip(minus, full)
        ]
        median_ratio = statistics.median(ratios)
        results.append(
            {
                "benchmark": "x64-stepper",
                "ablated_group": group,
                "implementation": implementation,
                "run_1_minus_over_full": f"{ratios[0]:.9f}",
                "run_2_minus_over_full": f"{ratios[1]:.9f}",
                "run_3_minus_over_full": f"{ratios[2]:.9f}",
                "median_minus_over_full": f"{median_ratio:.9f}",
                "minus_cost_percent": f"{(median_ratio - 1.0) * 100.0:.6f}",
                "full_speedup_percent": f"{(1.0 - 1.0 / median_ratio) * 100.0:.6f}",
                "full_wins": sum(ratio > 1.0 for ratio in ratios),
                "conclusion": (
                    "Full faster"
                    if median_ratio > 1.0
                    else f"{implementation} faster"
                    if median_ratio < 1.0
                    else "tie"
                ),
            }
        )
    with (RESULT_DIR / "grouped_ablation.csv").open(
        "w", newline="", encoding="utf-8"
    ) as destination:
        writer = csv.DictWriter(
            destination, fieldnames=list(results[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(results)
    return results


def write_derived(
    summary: list[dict[str, Any]], implementations: list[str] | None = None
) -> list[dict[str, Any]]:
    selected = implementations or IMPLEMENTATIONS
    runtime = {
        row["implementation"]: float(row["median"])
        for row in summary
        if row["metric"] == "Median runtime"
    }
    allocation = {
        row["implementation"]: float(row["median"])
        for row in summary
        if row["metric"] == "Heap allocation" and row["median"] != "unavailable"
    }
    derived = []
    for implementation in selected:
        seconds = runtime[implementation]
        allocated = allocation.get(implementation)
        derived.append(
            {
                "implementation": implementation,
                "median_seconds": f"{seconds:.9f}",
                "steps_per_second": f"{CASE_COUNT / seconds:.3f}",
                "speedup_vs_stage1": (
                    f"{runtime['Stage-1'] / seconds:.6f}"
                    if "Stage-1" in runtime
                    else "N/A"
                ),
                "time_vs_ocaml": (
                    f"{seconds / runtime['OCaml baseline']:.6f}"
                    if "OCaml baseline" in runtime
                    else "N/A"
                ),
                "time_vs_native": (
                    f"{seconds / runtime['Native x64 baseline']:.6f}"
                    if "Native x64 baseline" in runtime
                    else "N/A"
                ),
                "allocation_kib_per_step": (
                    "unavailable" if allocated is None else f"{allocated:.9f}"
                ),
                "allocation_vs_stage1": (
                    f"{allocated / allocation['Stage-1']:.6f}"
                    if allocated is not None
                    and "Stage-1" in allocation
                    and allocation["Stage-1"] != 0
                    else "unavailable"
                ),
            }
        )
    fields = list(derived[0])
    with (RESULT_DIR / "derived.csv").open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(derived)
    return derived


def write_record(
    summary: list[dict[str, Any]],
    derived: list[dict[str, Any]],
    grouped_ablation: list[dict[str, Any]],
    environment: dict[str, Any],
    repetitions: dict[str, int],
    implementations: list[str] | None = None,
    reused_from: Path | None = None,
    diagnostic: bool = False,
    prefer_owned_ablation: bool = False,
    rust_refresh: bool = False,
    ocaml_refresh: bool = False,
) -> None:
    selected = implementations or IMPLEMENTATIONS
    runtime = {row["implementation"]: row for row in summary if row["metric"] == "Median runtime"}
    allocation = {row["implementation"]: row for row in summary if row["metric"] == "Heap allocation"}
    derived_by_name = {row["implementation"]: row for row in derived}
    git_dirty = bool(environment["git_status"].strip())
    paired_ablation = "PreferOwned" if prefer_owned_ablation else "Closure"
    ablation_kind = "policy" if prefer_owned_ablation else "pass"
    lines = [
        "# RQ3 x64-stepper experiment record",
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
        f"- Fixed input: `{environment['input']['path']}`",
        f"- Input SHA-256: `{environment['input']['sha256']}`",
        f"- Corpus: {environment['input']['selection']}.",
        (
            "- Correctness: all five regenerated Rust implementations passed "
            "6000/6000 vectors against the recorded native x64 observations; "
            "the unchanged OCaml and native baseline rows retain their earlier "
            "correctness validation."
            if rust_refresh
            else "- Correctness: the rebuilt OCaml baseline passed "
            "6000/6000 vectors against the recorded native x64 observations; "
            "all generated-Rust and native baseline rows retain their earlier "
            "correctness validation."
            if ocaml_refresh
            else "- Correctness: both PreferOwned configurations passed "
            "6000/6000 vectors against the recorded native x64 observations."
            if prefer_owned_ablation
            else f"- Correctness: all {len(selected)} measured implementations passed "
            "6000/6000 vectors against the recorded native x64 observations."
        ),
        (
            f"- Reuse: unchanged baseline rows were reused from `{reused_from}`; "
            + (
                "all five Rust configurations were regenerated and remeasured."
                if rust_refresh
                else "the OCaml baseline was rebuilt and remeasured."
                if ocaml_refresh
                else "the four paper-facing Stage-2 configurations were regenerated and remeasured."
            )
            if reused_from
            else "- Reuse: no performance rows were reused."
        ),
        f"- Timing: JSON parsing, input conversion, observation, and per-case comparison are outside the timed region. A one-traversal pilot selects a whole-suite repetition count for each newly measured implementation targeting approximately {RUNTIME_TARGET_SECONDS:.0f} seconds per independent CPU-pinned runtime process. Full and minus {paired_ablation} use the larger of their two pilot repetition counts and run adjacently with alternating order. Each ablation effect is the median of the three within-round minus-{ablation_kind}/Full ratios. Results are normalized to one 6,000-vector traversal.",
        f"- Runtime suite repetitions: {json.dumps(repetitions, sort_keys=True)}.",
        "- OCaml runtime uses `clock_gettime(CLOCK_MONOTONIC)` through a C stub.",
        "- Rust allocation uses the same cumulative allocation counter as the SBPF experiment. OCaml uses `Gc.allocated_bytes`. The native C baseline uses linker-wrapped allocation functions and resets its cumulative counter immediately before the prepared ptrace step loop.",
        "",
        (
            "## Diagnostic Stage-2 pass ablations"
            if diagnostic
            else "## PreferOwned ablation"
            if prefer_owned_ablation
            else "## Paper-facing Stage-2 ablations"
        ),
        "",
    ]
    for row in grouped_ablation:
        lines.append(
            f"- {row['ablated_group']}: minus/Full ratios "
            f"{row['run_1_minus_over_full']}, {row['run_2_minus_over_full']}, "
            f"{row['run_3_minus_over_full']}; median {row['median_minus_over_full']} "
            f"({row['conclusion']}, Full speedup {row['full_speedup_percent']}%, "
            f"Full wins {row['full_wins']}/3)."
        )
    lines.extend(
        [
        "",
        "| Implementation | Run 1 (s) | Run 2 (s) | Run 3 (s) | Median (s) | KiB/step | Steps/s | Speedup vs Stage-1 | Time / OCaml | Time / native |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for implementation in selected:
        r = runtime[implementation]
        a = allocation[implementation]
        d = derived_by_name[implementation]
        lines.append(
            f"| {implementation} | {r['run_1']} | {r['run_2']} | {r['run_3']} | {r['median']} | "
            f"{a['median']} | {d['steps_per_second']} | {d['speedup_vs_stage1']} | "
            f"{d['time_vs_ocaml']} | {d['time_vs_native']} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `environment.json`: host, toolchains, CPU affinity, source/fixed input hashes, and counter probe.",
            "- `configurations.json`: optimization-pass matrix, source hashes, build settings, and executable hashes.",
            "- `binaries.json`: exact executables and hashes.",
            "- `raw.csv`: one row per formal measurement process.",
            "- `summary.csv`: three measurements and median for each paper metric.",
            "- `grouped_ablation.csv`: within-round minus-group/Full ratios and their medians.",
            "- `derived.csv`: throughput and cross-baseline ratios.",
            "- `commands.txt`, `correctness/`, `pilot/`, and `runs/`: full reproduction trail.",
            "",
        ]
    )
    host = environment["host_instructions"]
    if not host["available"]:
        lines.extend(
            [
                f"Host instruction counts remain TBD: perf_event_open failed with errno {host['errno']} ({host['error']}), perf_event_paranoid={host['perf_event_paranoid']}.",
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
        help="reuse unchanged Stage-1/OCaml/native rows and rebuild the four paper-facing Stage-2 configurations",
    )
    parser.add_argument(
        "--rust-from",
        type=Path,
        help="regenerate and remeasure all five Rust configurations while reusing only OCaml/native baseline rows",
    )
    parser.add_argument(
        "--ocaml-only-from",
        type=Path,
        help="rebuild and remeasure only the OCaml baseline while reusing all other rows",
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
        "--reuse-stage1-export",
        action="store_true",
        help="use the existing raw Stage-1 export instead of regenerating it",
    )
    args = parser.parse_args()
    global RESULT_DIR
    if not TIME.is_file():
        raise RuntimeError("/usr/bin/time is required")

    if args.resume and (
        args.stage2_only_from
        or args.rust_from
        or args.ocaml_only_from
        or args.rust_only
        or args.diagnostic
        or args.prefer_owned_ablation
    ):
        parser.error("--resume cannot be combined with another experiment mode")
    if args.stage2_only_from and (
        args.rust_from
        or args.ocaml_only_from
        or args.rust_only
        or args.diagnostic
        or args.prefer_owned_ablation
    ):
        parser.error("--stage2-only-from cannot be combined with another experiment mode")
    if args.rust_from and (
        args.ocaml_only_from
        or args.rust_only
        or args.diagnostic
        or args.prefer_owned_ablation
    ):
        parser.error("--rust-from cannot be combined with another experiment mode")
    if args.ocaml_only_from and (
        args.rust_only or args.diagnostic or args.prefer_owned_ablation
    ):
        parser.error("--ocaml-only-from cannot be combined with a targeted mode")
    if sum(
        bool(mode)
        for mode in (args.rust_only, args.diagnostic, args.prefer_owned_ablation)
    ) > 1:
        parser.error("--rust-only and targeted ablation modes are mutually exclusive")

    reused_from: Path | None = None
    rust_refresh = args.rust_from is not None
    ocaml_refresh = args.ocaml_only_from is not None
    if args.resume:
        RESULT_DIR = args.resume.resolve()
        command_log = RESULT_DIR / "commands.txt"
        if command_log.exists():
            COMMANDS.extend(command_log.read_text(encoding="utf-8").splitlines())
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
        timestamp = datetime.now().astimezone().strftime("x64-%Y%m%d-%H%M%S%z")
        RESULT_DIR = RESULTS / timestamp
        RESULT_DIR.mkdir(parents=True)
        validate_input()
        environment = record_environment()
        if args.stage2_only_from or args.rust_from or args.ocaml_only_from:
            reused_from = (
                args.rust_from.resolve()
                if args.rust_from
                else args.ocaml_only_from.resolve()
                if args.ocaml_only_from
                else args.stage2_only_from.resolve()
            )
            configurations = json.loads(
                (reused_from / "configurations.json").read_text(encoding="utf-8")
            )
            binaries = json.loads(
                (reused_from / "binaries.json").read_text(encoding="utf-8")
            )
            if ocaml_refresh:
                configurations.pop("OCaml baseline", None)
                binaries.pop("OCaml baseline", None)
                build_ocaml(configurations, binaries)
                configurations["ocaml_rerun"] = {
                    "reused_unchanged_implementations_from": str(reused_from),
                    "remeasured_implementation": "OCaml baseline",
                    "runtime_repetition_rule": (
                        f"whole-suite pilot target of at least {RUNTIME_TARGET_SECONDS:.0f} "
                        "seconds per process"
                    ),
                    "allocation_rule": "one complete suite per independent process",
                    "clock": "clock_gettime(CLOCK_MONOTONIC) through an OCaml C stub",
                }
            else:
                if rust_refresh and not args.reuse_stage1_export:
                    generate_rust_export()
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
                        "Stage-2 configuration; unchanged OCaml/native baseline rows reused"
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
            if not args.reuse_stage1_export:
                generate_rust_export()
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
                "benchmark": "x64-stepper",
                "cases": CASE_COUNT,
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
                    "Rust WordU128 layer plus Checked128 Int/Nat profile for Stage-1 and every Stage-2 configuration; fixed default OCaml export for the OCaml baseline"
                ),
                "rust_build": "cargo +stable build --release --locked",
                "timed_region": "raw x64_step_test call only; parsing, conversion, observation, and comparison excluded",
                "allocation_rule": (
                    "Successful Rust alloc and alloc_zeroed add layout.size(); successful realloc adds new_size; dealloc subtracts nothing. The counter is reset immediately before the measured workload."
                ),
            }
            binaries = {}
            prepare_generated(configurations, selected_rust)
            build_generated(configurations, binaries, selected_rust)
            if not args.rust_only and not args.diagnostic and not args.prefer_owned_ablation:
                build_ocaml(configurations, binaries)
                build_native(configurations, binaries)
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
        ["OCaml baseline"]
        if ocaml_refresh
        else RUST_IMPLEMENTATIONS
        if rust_refresh
        else STAGE2_IMPLEMENTATIONS
        if reused_from
        else PREFER_OWNED_IMPLEMENTATIONS
        if args.prefer_owned_ablation
        else DIAGNOSTIC_IMPLEMENTATIONS
        if args.diagnostic
        else RUST_IMPLEMENTATIONS
        if args.rust_only
        else IMPLEMENTATIONS
    )
    validate_all(binaries, selected)
    repetitions = pilot_all(binaries, selected)
    rows = measure_all(binaries, environment, repetitions, selected)
    if reused_from:
        with (reused_from / "raw.csv").open(newline="", encoding="utf-8") as source:
            baseline_rows = [
                row
                for row in csv.DictReader(source)
                if (
                    row["implementation"] != "OCaml baseline"
                    if ocaml_refresh
                    else not row["implementation"].startswith(
                        "Stage-" if rust_refresh else "Stage-2"
                    )
                )
            ]
        rows = baseline_rows + rows
        write_raw(rows)
    report_implementations = IMPLEMENTATIONS if reused_from else selected
    summary = summarize(rows, report_implementations)
    derived = write_derived(summary, report_implementations)
    grouped_ablation = write_grouped_ablation_summary(
        rows,
        PREFER_OWNED_ABLATIONS
        if args.prefer_owned_ablation
        else DIAGNOSTIC_ABLATIONS
        if args.diagnostic
        else ABLATION_GROUPS,
    )
    write_record(
        summary,
        derived,
        grouped_ablation,
        environment,
        repetitions,
        report_implementations,
        reused_from,
        args.diagnostic,
        args.prefer_owned_ablation,
        rust_refresh,
        ocaml_refresh,
    )
    print(json.dumps(summary, indent=2))
    print(f"RESULT_DIR={RESULT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
