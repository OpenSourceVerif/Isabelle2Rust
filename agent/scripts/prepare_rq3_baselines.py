#!/usr/bin/env python3
"""Prepare original-source RQ3 baselines without regeneration or measurement.

All mutations are confined to --output. The correctness cohort and exported
algorithms are read-only. Native targets are exported from the same frozen
testing theory; the only new code is an observation/timing driver. A separate
explicit measurement command must consume the resulting manifest.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from i2r_agent.common import Executor, Failure, ROOT, digest, now, read, save
from i2r_agent import numeric_experiment, timing_drivers, tool_sources
from i2r_agent.kernel_build import copy_crate
from i2r_agent.native_baseline import haskell_strictness
from i2r_agent.preprocessing import isabelle_command, project_info
from i2r_agent.references import compile_rust
from i2r_agent.validation import execute


LANGUAGES = ("stage2", "ocaml", "haskell", "go")
NUMERICS = {
    "stage2": "Isabelle Rust-S2 Dashu UBig/IBig; arbitrary precision",
    "ocaml": "Isabelle OCaml Zarith Z.t; arbitrary precision",
    "haskell": "Isabelle Haskell Integer; arbitrary precision",
    "go": "AFP Go math/big.Int; arbitrary precision",
}


def hash_tree(path, suffixes=None):
    return {str(p.relative_to(path)): digest(p) for p in sorted(Path(path).rglob("*"))
            if p.is_file() and (suffixes is None or p.suffix in suffixes)}


def failure(error):
    return {"status": "N/A", "code": getattr(error, "code", type(error).__name__),
            "reason": str(error), "evidence": getattr(error, "evidence", None)}


def case_context(args, row):
    cohort = read(args.cohort / "baseline-sources.json")["cases"][row["id"]]
    original = Path(cohort["run"])
    directory = args.output / "cases" / row["id"]
    directory.mkdir(parents=True, exist_ok=True)
    state, cfg, observations, seal = numeric_experiment.freeze(args.cohort, row, directory)
    matches = list((original / "baselines").glob(row["id"] + "-*/baseline.json"))
    if len(matches) != 1:
        raise Failure("baseline_ambiguous", str(matches))
    baseline = read(matches[0])
    project = original / "projects" / row["id"] / "testing"
    if not (project / "Kernel.thy").is_file():
        raise Failure("frozen_testing_project_missing", str(project))
    source_hashes = hash_tree(project, {".thy", ".ML", ".toml", ".json"})
    for name, sha in source_hashes.items():
        recorded = row["files"].get("testing/" + name)
        if recorded is not None and recorded != sha:
            raise Failure("testing_source_changed", str(project / name))
    inputs = {
        "case": row["id"], "created_at": now(), "cohort": str(args.cohort),
        "frozen_sha256": digest(directory / "frozen.json"),
        "reference_record": str(matches[0]), "reference_record_sha256": digest(matches[0]),
        "testing_project": str(project), "testing_source_sha256": source_hashes,
        "primary_workload": row["primary_workload"],
        "observations": [{"lane": lane, "input": list(x), "expected": y}
                         for (lane, x), y in observations.items()],
        "workloads": [{**w, "expected": observations[("kernel", tuple(w["input"]))]}
                      for w in row["performance_workloads"]],
        "model_calls": 0, "correctness_regenerated": False,
    }
    cached = directory / "input-manifest.json"
    if cached.exists():
        before = read(cached)
        if {k: v for k, v in inputs.items() if k != "created_at"} != {
                k: v for k, v in before.items() if k != "created_at"}:
            raise Failure("input_manifest_changed", str(cached))
    else:
        save(cached, inputs)
    local_cfg = deepcopy(cfg)
    local_cfg["tools"]["isabelle_heaps"] = str(args.output / "heaps")
    return directory, project, local_cfg, observations, baseline


def export_native(project, cfg, work):
    """One checked Isabelle session exports both native targets from fixed roots."""
    saved = work / "native-export.json"
    if saved.exists():
        result = read(saved)
        if any(digest(p) != h for p, h in result["input_hashes"].items()):
            raise Failure("native_export_input_changed", str(saved))
        if any(digest(p) != h for p, h in result["export_hashes"].items()):
            raise Failure("native_export_changed", str(saved))
        return result
    work.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for p in project.rglob("*"):
        if p.is_file() and p.suffix in {".thy", ".ML"}:
            inputs[str(p)] = digest(p)
            dest = work / p.relative_to(project)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
    theory = work / "Export.thy"
    original = theory.read_text()
    source = original.replace('"I2R_Agent.Agent_Export"',
                              '"Rust.Rust_Dashu_Setup" "Go.Go_Setup"')
    pattern = r"export_code\s+([\s\S]*?)\s+in\s+Rust_Agent\s+module_name\s+\w+"
    def replace(match):
        roots = match[1].strip() + " nat_of_integer integer_of_nat"
        return "\n".join(f"export_code {roots} in {target} module_name Candidate"
                         for target in ("Haskell", "Go"))
    source, count = re.subn(pattern, replace, source)
    if count != 1 or '"Go.Go_Setup"' not in source:
        raise Failure("unsupported_export_statement", str(theory))
    theory.write_text(source)
    theories, sessions = project_info(work)
    session = "RQ3_Preflight_" + hashlib.sha256(
        "".join(p.read_text() for p in sorted(work.glob("*.thy"))).encode()).hexdigest()[:16]
    root = f'session {session} = Rust +\n  options [document=false, skip_proofs=false, timeout=1200]\n'
    root += "  sessions\n" + "".join(f'    "{s}"\n' for s in sessions)
    directories = sorted({str(p.parent.relative_to(work)) for p in work.rglob("*.thy") if p.parent != work and "exported" not in p.parts})
    if directories:
        root += "  directories\n" + "".join(f'    "{d}"\n' for d in directories)
    root += "  theories\n" + "".join(f"    {t}\n" for t in theories)
    root += '  export_files (in "exported") [2]\n'
    root += "".join(f'    "{session}.{t}:code/**"\n' for t in theories)
    (work / "ROOT").write_text(root)
    ex = Executor(work / "commands")
    record = ex.run(isabelle_command(cfg, "build", "-e", "-j", "1", "-o", "threads=2",
        "-o", "parallel_proofs=0", "-o", "document=false", "-d", ROOT / "isabelle",
        "-d", tool_sources.repository("Isabelle2Rust"), "-d", cfg["tools"]["afp"],
        "-d", work, session), timeout=cfg["budgets"]["build_seconds"])
    hs = list((work / "exported").rglob("Candidate.hs"))
    go = [p for p in (work / "exported").rglob("*.go")
          if p.parent.name == "Candidate" and re.search(r"func Kernel_run\b", p.read_text())]
    if len(hs) != 1 or len(go) != 1:
        raise Failure("native_export_layout", repr({"haskell": hs, "go": go}))
    result = {"status": "exported", "session": session, "command": record,
              "haskell": str(hs[0]), "go": str(go[0]), "input_hashes": inputs,
              "export_hashes": {str(p): digest(p) for p in (work / "exported").rglob("*") if p.is_file()},
              "export_only_changes": {"old_Export.thy": original, "new_Export.thy": source}}
    save(saved, result)
    return result


def rust_batch(reference):
    modules = reference["kernel_modules"]
    prepare = "kernel_prepare(" + ("&" if modules["kernel_prepare"][1] else "") + "input)"
    run = "kernel_run(prepared)"
    encode = "kernel_encode(" + ("&" if modules["kernel_encode"][1] else "") + "result)"
    iterator = "prepared.iter()" if modules["kernel_run"][1] else "prepared.into_iter()"
    return r'''
fn rq3_batch_main() {
 use std::io::Write;
 let mut deltas=Vec::new();
 for _ in 0..10000 {let t=std::time::Instant::now();let d=t.elapsed().as_nanos();if d>0{deltas.push(d);}}
 deltas.sort();println!("V2_CLOCK {} {}",deltas[0],deltas[deltas.len()/2]);std::io::stdout().flush().unwrap();
 let stdin=std::io::stdin();let mut lines=stdin.lock().lines();
 while let Some(header)=lines.next() {
  let header=header.unwrap();let n:usize=header.strip_prefix("B ").unwrap().parse().unwrap();
  let line=lines.next().unwrap().unwrap();let expected=lines.next().unwrap().unwrap();
  let prepared=(0..n).map(|_| {
   let values:Vec<WireInt>=std::hint::black_box(&line).split_whitespace().map(|s|s.parse().unwrap()).collect();
   let input=values.iter().rev().fold(List::Nil,|tail,x|List::Cons(x.to_string().parse::<ReferenceNat>().unwrap(),Box::new(tail)));
   std::hint::black_box(@PREPARE@)
  }).collect::<Vec<_>>();
  let mut inputs=@ITERATOR@;let mut results=Vec::with_capacity(n);
  let start=std::time::Instant::now();
  for prepared in inputs.by_ref() {results.push(std::hint::black_box(@RUN@));}
  let elapsed=start.elapsed().as_nanos();drop(inputs);
  for result in results {
   let output=@ENCODE@;let mut words=Vec::new();let mut rest=output;
   while let List::Cons(x,tail)=rest {words.push(x.to_string());rest=*tail;}
   assert_eq!(words.join(" "),expected);
  }
  println!("V2 {} {}",elapsed,n);std::io::stdout().flush().unwrap();
 }
}
'''.replace("@PREPARE@", prepare).replace("@ITERATOR@", iterator).replace("@RUN@", run).replace("@ENCODE@", encode)


def ocaml_source(module):
    batch = timing_drivers.ocaml(module).replace("let () =", "let batch_main () =", 1)
    return batch + r'''
let () =
 if Array.exists ((=) "--i2r-batch-v2") Sys.argv then batch_main () else
 let kernel=Array.exists ((=) "--i2r-kernel-check") Sys.argv in
 try while true do
  let words=String.split_on_char ' ' (read_line ()) |> List.filter ((<>) "") in
  let input=List.map (fun s -> Reference.MODULE.nat_of_integer (Z.of_string s)) words in
  let output=if kernel then Reference.MODULE.kernel_encode (Reference.MODULE.kernel_run (Reference.MODULE.kernel_prepare input))
   else Reference.MODULE.observe input in
  print_endline (String.concat " " (List.map (fun n -> Z.to_string (Reference.MODULE.integer_of_nat n)) output))
 done with End_of_file -> ()
'''.replace("MODULE", module)


def haskell_source():
    batch = timing_drivers.HASKELL.replace("import System.IO", "import System.IO\nimport System.Environment (getArgs)")
    batch = batch.replace("main :: IO ()\nmain = do", "batchMain :: IO ()\nbatchMain = do", 1)
    return batch + r'''
main :: IO ()
main = do
 args <- getArgs
 if "--i2r-batch-v2" `elem` args then batchMain else validationLoop ("--i2r-kernel-check" `elem` args)
validationLoop :: Bool -> IO ()
validationLoop kernel = do
 eof <- isEOF
 if eof then pure () else do
  line <- getLine
  let input=map (C.nat_of_integer . read) (words line)
  output <- evaluate (force (if kernel then C.kernel_encode (C.kernel_run (C.kernel_prepare input)) else C.observe input))
  putStrLn (unwords (map (show . C.integer_of_nat) output))
  validationLoop kernel
'''


def go_source(source):
    def qualified_result(symbol):
        match = re.search(r"func " + symbol + r"\s*\(.*?\)\s+([^\n]+?)\s*\{", source)
        if not match:
            raise Failure("go_kernel_signature_missing", symbol)
        def qualify(token):
            name = token[0]
            return "B." + name.split(".", 1)[1] if name.startswith("Bigint.") else "C." + name
        return re.sub(r"\b[A-Z]\w*(?:\.[A-Z]\w*)?\b", qualify, match[1])
    batch = timing_drivers.GO.replace("PREPARED", qualified_result("Kernel_prepare"))
    batch = batch.replace("RESULT", qualified_result("Kernel_run"))
    batch = batch.replace("func main() {", "func batchMain() {", 1)
    return batch + r'''
func main() {
 kernel:=false
 for _,a:=range os.Args[1:] {if a=="--i2r-batch-v2"{batchMain();return};if a=="--i2r-kernel-check"{kernel=true}}
 scanner:=bufio.NewScanner(os.Stdin);scanner.Buffer(make([]byte,4096),64*1024*1024)
 for scanner.Scan() {
  words:=strings.Fields(scanner.Text());var input C.List[C.Nat]=C.Nil[C.Nat]{}
  for j:=len(words)-1;j>=0;j--{input=C.Cons[C.Nat]{A:C.Nat_of_integer(B.MkInt(words[j])),Aa:input}}
  var output C.List[C.Nat]
  if kernel {output=C.Kernel_encode(C.Kernel_run(C.Kernel_prepare(input)))} else {output=C.Observe(input)}
  result:=[]string{}
  for {node,ok:=output.(C.Cons[C.Nat]);if !ok{break};value:=C.Integer_of_nat(node.A);result=append(result,value.String());output=node.Aa}
  fmt.Println(strings.Join(result," "))
 }
 if err:=scanner.Err();err!=nil{panic(err)}
}
'''


def build_native(lang, reference, source, cfg, work, shared_cargo):
    saved = work / "build.json"
    if saved.exists():
        result = read(saved)
        if result["builder_sha256"] != digest(__file__):
            # Development preflight builds have no measurements to invalidate.
            # Retain their receipts, then rebuild instead of mixing drivers.
            if (work / "measurement-v2.json").exists():
                raise Failure("preflight_measured_build_immutable", str(saved))
            save(work / "build-history" / (result["builder_sha256"] + ".json"), result)
        else:
            for key in ["original_hashes", "artifact_hashes"]:
                if any(digest(p) != h for p, h in result[key].items()):
                    raise Failure("preflight_build_changed", str(saved))
            return result
    work.mkdir(parents=True, exist_ok=True)
    ex = Executor(work / "commands")
    ex.shared_cargo_root = shared_cargo
    binary = work / "reference"
    original_hashes = {}
    if lang == "stage2":
        crate = work / "crate"
        original_hashes = copy_crate(reference["crate"], crate)
        main = crate / "src/main.rs"
        original = main.read_text()
        if "use dashu_int::UBig as ReferenceNat;" not in original:
            raise Failure("unexpected_stage2_numeric_representation", str(main))
        source = original.replace("fn main() {", 'fn main() {\n if std::env::args().any(|s|s=="--i2r-batch-v2") {rq3_batch_main();return;} ', 1)
        main.write_text(source + rust_batch(reference))
        built = compile_rust(crate, cfg, ex)
        if built["status"] != "passed":
            raise Failure("stage2_driver_build_failed", lang, built)
        shutil.copy2(built["binary"], binary)
    elif lang == "ocaml":
        source = Path(source)
        original_hashes[str(source)] = digest(source)
        shutil.copy2(source, work / "reference.ml")
        modules = [name for name, sig in re.findall(r"module\s+(\w+)\s*:\s*sig(.*?)end\s*=", source.read_text(), re.S)
                   if all(re.search(r"\bval\s+"+s+r"\s*:", sig) for s in ["kernel_run", "kernel_prepare", "kernel_encode", "observe"])]
        if len(modules) != 1:
            raise Failure("ocaml_module_ambiguous", str(source))
        (work / "main.ml").write_text(ocaml_source(modules[0]))
        (work / "clock.c").write_text(timing_drivers.OCAML_CLOCK)
        ex.run([cfg["tools"]["ocamlfind"], "ocamlopt", "-package", "zarith", "-linkpkg", "-o", binary,
                "clock.c", "reference.ml", "main.ml"], cwd=work,
               env={"PATH": str(Path(cfg["tools"]["ocamlfind"]).parent)+os.pathsep+os.environ["PATH"]})
    elif lang == "haskell":
        source = Path(source)
        original_hashes[str(source)] = digest(source)
        (work / "Candidate.hs").write_text(haskell_strictness(source.read_text()))
        (work / "Main.hs").write_text(haskell_source())
        (work / "clock.c").write_text(timing_drivers.RAW_CLOCK)
        ex.run(["/opt/homebrew/bin/ghc", "-O2", "-fno-full-laziness", "-fno-cse", "-i"+str(work),
                "-outputdir", work / "objects", "-o", binary, work / "Main.hs", work / "clock.c"], cwd=work, timeout=300)
    elif lang == "go":
        source = Path(source)
        module, dest = source.parents[1], work / "module"
        for p in module.rglob("*"):
            if p.is_file() and p.name != "main.go" and (p.suffix == ".go" or p.name in ["go.mod", "go.sum"]):
                original_hashes[str(p)] = digest(p)
                target = dest / p.relative_to(module)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
        (dest / "main.go").write_text(go_source(source.read_text()))
        ex.run([cfg["tools"]["isabelle"], "go", "build", "-o", binary, "."], cwd=dest, timeout=300)
    if any(digest(p) != h for p, h in original_hashes.items()):
        raise Failure("original_algorithm_changed_during_build", lang)
    artifact_hashes = {str(p): digest(p) for p in work.rglob("*") if p.is_file()
                       and not {"commands", "target", "objects", "build-history", "validation-commands"}.intersection(p.relative_to(work).parts)
                       and p.name not in {"build.json", "validation.json", "failure.json", "ordinary-full-outputs.json", "kernel-full-outputs.json"}}
    result = {"status": "built", "id": lang, "language": lang, "kind": "original-reference",
              "binary": str(binary), "work": str(work), "numeric_semantics": NUMERICS[lang],
              "original_hashes": original_hashes, "artifact_hashes": artifact_hashes,
              "builder_sha256": digest(__file__), "drivers_sha256": digest(timing_drivers.__file__),
              "built_at": now(), "protocol": "kernel-v2", "measurement_performed": False,
              "scope": {"prepare": "outside timing; independently materialized for every call",
                        "run": "inside timing; complete result evaluation",
                        "encode_compare": "outside timing; full output comparison",
                        "borrowed_rust_inputs": "retained until outside timing",
                        "haskell": "NFData force of prepared input before timer and result inside timer"}}
    save(saved, result)
    return result


def validate(binary, observations, work, timeout):
    saved = work / "validation.json"
    if saved.exists():
        result = read(saved)
        if result["binary_sha256"] == digest(binary):
            return result
    ex = Executor(work / "validation-commands")
    results = []
    for lane in ["ordinary", "kernel"]:
        pairs = [(list(x), y) for (kind, x), y in observations.items() if kind == lane]
        actual = execute(binary, [x for x, _ in pairs], ex, timeout,
                         arguments=("--i2r-kernel-check",) if lane == "kernel" else ())
        if actual["status"] != "passed":
            raise Failure("reference_validation_execution_failed", lane, actual)
        outputs = actual["outputs"]
        if len(outputs) != len(pairs):
            raise Failure("reference_output_count_mismatch", lane, actual)
        rows = [{"input": x, "expected": y, "actual": z, "matched": y == z}
                for (x, y), z in zip(pairs, outputs)]
        save(work / (lane+"-full-outputs.json"), {"lane": lane, "rows": rows, "execution": actual["record"]})
        if not all(row["matched"] for row in rows):
            raise Failure("reference_output_mismatch", lane, str(work / (lane+"-full-outputs.json")))
        results.append({"lane": lane, "compared": len(rows), "status": "passed",
                        "full_outputs": str(work / (lane+"-full-outputs.json"))})
    result = {"status": "validated", "binary_sha256": digest(binary), "lanes": results,
              "expected_source": "frozen correctness cohort complete reference outputs",
              "measurement_performed": False, "model_calls": 0}
    save(saved, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=["freeze", "export", "build", "validate", "all"], default="all")
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--languages", nargs="+", choices=LANGUAGES, default=list(LANGUAGES))
    args = parser.parse_args()
    args.cohort, args.manifest, args.output = (p.resolve() for p in [args.cohort, args.manifest, args.output])
    args.output.mkdir(parents=True, exist_ok=True)
    cohort = read(args.cohort / "baseline-sources.json")["cases"]
    selected = set(args.cases or cohort)
    rows = [r for r in read(args.manifest)["cases"] if r["id"] in selected]
    if selected != {r["id"] for r in rows}:
        raise Failure("unknown_case", repr(selected - {r["id"] for r in rows}))
    if args.phase in ["export", "all"] and not (args.output / "heaps").exists():
        origin = Path(next(iter(cohort.values()))["run"]) / "heaps"
        shutil.copytree(origin, args.output / "heaps")
        save(args.output / "heap-seed.json", {"copied_from": str(origin), "new_heaps": str(args.output / "heaps")})
    for row in rows:
        print(f"{row['id']}: {args.phase}", flush=True)
        directory, project, cfg, observations, baseline = case_context(args, row)
        if args.phase == "freeze":
            continue
        native = None
        if any(lang in args.languages for lang in ["haskell", "go"]):
            try:
                if args.phase in ["export", "all"]:
                    native = export_native(project, cfg, directory / "native-export")
                else:
                    native = read(directory / "native-export/native-export.json")
            except Exception as error:
                native = failure(error)
                save(directory / "native-export-failure.json", native)
                print(f"  native export: {native['code']}", flush=True)
        if args.phase == "export":
            continue
        statuses = {}
        for lang in args.languages:
            work = directory / "builds" / lang
            try:
                ref = baseline["references"].get(lang, {})
                if lang in ["stage2", "ocaml"]:
                    if ref.get("status") != "passed":
                        raise Failure("original_reference_unavailable", lang, ref)
                    source = ref["source"]
                else:
                    if native is None or native.get("status") != "exported":
                        raise Failure("native_export_unavailable", lang, native)
                    source = native[lang]
                build = build_native(lang, ref, source, cfg, work, args.output / "cargo-cache")
                statuses[lang] = {"status": "built", "build": str(work / "build.json"), "binary": build["binary"]}
                if args.phase in ["validate", "all"]:
                    validation = validate(build["binary"], observations, work, cfg["testing"]["process_timeout"])
                    statuses[lang].update(status="validated", validation=str(work / "validation.json"))
                print(f"  {lang}: {statuses[lang]['status']}", flush=True)
            except Exception as error:
                statuses[lang] = failure(error)
                save(work / "failure.json", statuses[lang])
                print(f"  {lang}: N/A ({statuses[lang]['code']})", flush=True)
            summary = directory / "baseline-status.json"
            save(summary, {**(read(summary) if summary.exists() else {}), **statuses})
    manifest = {"schema": 1, "created_at": now(), "cohort": str(args.cohort),
                "workload_manifest": str(args.manifest), "workload_manifest_sha256": digest(args.manifest),
                "model_calls": 0, "measurement_performed": False, "cases": {}}
    for case in cohort:
        directory = args.output / "cases" / case
        if (directory / "input-manifest.json").exists():
            manifest["cases"][case] = {"inputs": str(directory / "input-manifest.json"),
                "inputs_sha256": digest(directory / "input-manifest.json"),
                "baselines": read(directory / "baseline-status.json") if (directory / "baseline-status.json").exists() else {}}
    save(args.output / "rq3-preflight-manifest.json", manifest)


if __name__ == "__main__":
    lock_path = ROOT / "cache/timing-v2.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        main()
