#!/usr/bin/env python3
"""Run the OCaml sBPF interpreter macro test from Isabelle-generated code."""

from __future__ import annotations

import os
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(os.environ.get("SBPF_ROOT", Path(__file__).resolve().parents[4]))
EXEC_DIR = Path(os.environ.get("SBPF_EXEC_DIR", ROOT / "tests_sbpf" / "tests" / "exec_semantics"))
EXPORT_DIR = Path(os.environ.get("SBPF_EXPORT_DIR", ROOT / "tests_sbpf" / "theory" / "stage1" / "bpf_generator"))
OCAML_DIR = EXEC_DIR / "sbpf_ocaml"
TEST_ML = OCAML_DIR / "test.ml"

EXPECTED_OCAML_VERSION = os.environ.get("OCAML_VERSION", "4.11.2")

SIG_MARKER = """  val bpf_interp_test :
    int list -> int list -> int list -> int -> int -> int -> bool -> bool
"""

SIG_GLUE = """  val bpf_interp_test :
    int list -> int list -> int list -> int -> int -> int -> bool -> bool
  val int_of_standard_int : int64 -> int
  val int_list_of_standard_int_list : int64 list -> int list
"""

STRUCT_END = "end;; (*struct Interp_test*)"

STRUCT_GLUE = """
let int_of_standard_int (n : int64) : int =
  Int_of_integer (Z.of_int64 n);;

let int_list_of_standard_int_list (xs : int64 list) : int list =
  List.map int_of_standard_int xs;;

end;; (*struct Interp_test*)"""

GLUE_VERSION = "interp-macro-zarith-v1"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def announce(title: str, detail: str) -> None:
    print(f">>> [sbpf_ocaml] {title}: {detail}", flush=True)


def run_command(cmd: list[str], *, cwd: Path) -> tuple[int, str]:
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
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
        actual = command_output(["ocamlc", "-version"])
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: could not run ocamlc: {exc}")
        return False

    announce("OCaml version", f"ocamlc {actual}")
    if EXPECTED_OCAML_VERSION and actual != EXPECTED_OCAML_VERSION:
        print(
            f"ERROR: expected ocamlc {EXPECTED_OCAML_VERSION}, got {actual}. "
            "Set OCAML_VERSION=... only when intentionally changing the fixed test version."
        )
        return False

    try:
        zarith_path = command_output(["ocamlfind", "query", "zarith"])
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: OCaml package zarith is required for the generated OCaml export: {exc}")
        return False

    announce("OCaml package", f"zarith at {zarith_path}")
    return True


def add_interp_glue(src: str) -> str:
    if SIG_MARKER not in src:
        raise ValueError("could not find bpf_interp_test signature in generated OCaml export")
    if STRUCT_END not in src:
        raise ValueError("could not find Interp_test module end marker in generated OCaml export")
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
        "test_ml_sha256": file_sha256(TEST_ML),
    }


def cache_is_valid(build_dir: Path, key: dict[str, str]) -> bool:
    stamp = build_dir / ".macro_interp_cache.json"
    binary = build_dir / "test"
    if os.environ.get("REBUILD") == "1" or os.environ.get("OCAML_REBUILD") == "1":
        return False
    if not stamp.exists() or not binary.exists():
        return False
    try:
        return json.loads(stamp.read_text(encoding="utf-8")) == key
    except json.JSONDecodeError:
        return False


def prepare_build_dir() -> tuple[Path, bool]:
    export_file = EXPORT_DIR / "interp_test.ocaml"
    if not export_file.exists():
        raise FileNotFoundError(f"missing Isabelle OCaml export: {rel(export_file)}")

    build_dir = OCAML_DIR / "_build" / "macro_interp"
    key = cache_key(export_file)
    if cache_is_valid(build_dir, key):
        announce("cache", f"reusing compiled OCaml macro binary at {rel(build_dir / 'test')}")
        return build_dir, True

    announce("glue", f"preparing {rel(build_dir)} from {rel(export_file)}")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    glued = add_interp_glue(export_file.read_text(encoding="utf-8"))
    (build_dir / "interp_test.ml").write_text(glued, encoding="utf-8")
    shutil.copy2(TEST_ML, build_dir / "test.ml")
    (build_dir / ".macro_interp_cache.json").write_text(
        json.dumps(key, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return build_dir, False


def main() -> int:
    if not check_ocaml_environment():
        return 2

    try:
        build_dir, reused = prepare_build_dir()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    compile_base = ["ocamlfind", "ocamlc", "-package", "zarith", "-linkpkg"]
    if not reused:
        announce("compile", "ocamlfind ocamlc -package zarith -linkpkg -c interp_test.ml")
        rc, _ = run_command(compile_base + ["-c", "interp_test.ml"], cwd=build_dir)
        if rc != 0:
            return rc

        announce("compile", "ocamlfind ocamlc -package zarith -linkpkg -o test interp_test.cmo test.ml")
        rc, _ = run_command(compile_base + ["-o", "test", "interp_test.cmo", "test.ml"], cwd=build_dir)
        if rc != 0:
            return rc

    announce("run", "./test over local Solana macro data in sbpf_ocaml/test.ml")
    rc, _ = run_command(["./test"], cwd=build_dir)
    return rc


if __name__ == "__main__":
    sys.exit(main())
