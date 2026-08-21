#!/usr/bin/env python3
"""Run the OCaml SBPF instruction-level micro test from Isabelle-generated code."""

from __future__ import annotations

import hashlib
import json
import os
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
OCAML_DIR = EXEC_DIR / "sbpf_ocaml"
STEP_ML = OCAML_DIR / "step.ml"

EXPECTED_OCAML_VERSION = os.environ.get("OCAML_VERSION", "4.11.2")

SIG_MARKER = """  val step_test :
    int list ->
      int list ->
        int list -> int list -> int -> int -> int -> int -> int -> bool
"""

SIG_GLUE = """  val step_test :
    int list ->
      int list ->
        int list -> int list -> int -> int -> int -> int -> int -> bool
  val int_of_standard_int : int64 -> int
  val int_list_of_standard_int_list : int64 list -> int list
"""

STRUCT_END = "end;; (*struct Step_test*)"

STRUCT_GLUE = """
let int_of_standard_int (n : int64) : int =
  Int_of_integer (Z.of_int64 n);;

let int_list_of_standard_int_list (xs : int64 list) : int list =
  List.map int_of_standard_int xs;;

end;; (*struct Step_test*)"""

GLUE_VERSION = "step-micro-zarith-ocamlopt-v2"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def announce(title: str, detail: str) -> None:
    print(f">>> [sbpf_ocaml] {title}: {detail}", flush=True)


def run_command(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> tuple[int, str]:
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


def command_output(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def check_ocaml_environment() -> bool:
    try:
        actual = command_output(["ocamlopt", "-version"])
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: could not run ocamlopt: {exc}")
        return False

    announce("OCaml version", f"ocamlopt {actual}")
    if EXPECTED_OCAML_VERSION and actual != EXPECTED_OCAML_VERSION:
        print(
            f"ERROR: expected ocamlopt {EXPECTED_OCAML_VERSION}, got {actual}. "
            "Set OCAML_VERSION=... only when intentionally changing the fixed test version."
        )
        return False

    for package in ("zarith", "yojson"):
        try:
            path = command_output(["ocamlfind", "query", package])
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            print(f"ERROR: OCaml package {package} is required: {exc}")
            return False
        announce("OCaml package", f"{package} at {path}")
    return True


def add_step_glue(src: str) -> str:
    if SIG_MARKER not in src:
        raise ValueError("could not find step_test signature in generated OCaml export")
    if STRUCT_END not in src:
        raise ValueError("could not find Step_test module end marker in generated OCaml export")
    src = src.replace(SIG_MARKER, SIG_GLUE, 1)
    src = src.replace(STRUCT_END, STRUCT_GLUE, 1)
    return src


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_key(export_file: Path) -> dict[str, str]:
    return {
        "ocaml_version": EXPECTED_OCAML_VERSION,
        "glue_version": GLUE_VERSION,
        "export_sha256": file_sha256(export_file),
        "step_ml_sha256": file_sha256(STEP_ML),
    }


def cache_is_valid(build_dir: Path, key: dict[str, str]) -> bool:
    stamp = build_dir / ".micro_step_cache.json"
    binary = build_dir / "step"
    if os.environ.get("REBUILD") == "1" or os.environ.get("OCAML_REBUILD") == "1":
        return False
    if not stamp.exists() or not binary.exists():
        return False
    try:
        return json.loads(stamp.read_text(encoding="utf-8")) == key
    except json.JSONDecodeError:
        return False


def prepare_build_dir() -> tuple[Path, bool]:
    export_file = EXPORT_DIR / "step_test.ocaml"
    if not export_file.exists():
        raise FileNotFoundError(f"missing Isabelle OCaml export: {rel(export_file)}")

    build_dir = OCAML_DIR / "_build" / "micro_step"
    key = cache_key(export_file)
    if cache_is_valid(build_dir, key):
        announce("cache", f"reusing compiled OCaml micro binary at {rel(build_dir / 'step')}")
        return build_dir, True

    announce("glue", f"preparing {rel(build_dir)} from {rel(export_file)}")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    glued = add_step_glue(export_file.read_text(encoding="utf-8"))
    (build_dir / "step_test.ml").write_text(glued, encoding="utf-8")
    shutil.copy2(STEP_ML, build_dir / "step.ml")
    (build_dir / ".micro_step_cache.json").write_text(
        json.dumps(key, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return build_dir, False


def main() -> int:
    if not check_ocaml_environment():
        return 2
    if not STEP_JSON.exists():
        print(f"ERROR: missing step JSON: {rel(STEP_JSON)}")
        return 2

    try:
        build_dir, reused = prepare_build_dir()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    compile_base = ["ocamlfind", "ocamlopt", "-package", "zarith,yojson", "-linkpkg"]
    if not reused:
        announce("compile", "ocamlfind ocamlopt -package zarith,yojson -linkpkg -c step_test.ml")
        rc, _ = run_command(compile_base + ["-c", "step_test.ml"], cwd=build_dir)
        if rc != 0:
            return rc

        announce("compile", "ocamlfind ocamlopt -package zarith,yojson -linkpkg -o step step_test.cmx step.ml")
        rc, _ = run_command(compile_base + ["-o", "step", "step_test.cmx", "step.ml"], cwd=build_dir)
        if rc != 0:
            return rc

    env = os.environ.copy()
    env["CROSS_JSON"] = str(STEP_JSON)
    announce("run", f"./step over {rel(STEP_JSON)}")
    rc, _ = run_command(["./step"], cwd=build_dir, env=env)
    return rc


if __name__ == "__main__":
    sys.exit(main())
