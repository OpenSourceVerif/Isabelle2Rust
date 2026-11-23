"""Compile the sealed SML, OCaml, Haskell, Scala and Go exports from fixed-plan-v3."""

from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import csv
from dataclasses import dataclass
import json
import os
from pathlib import Path
import select
import shlex
import shutil
import signal
import subprocess
import tempfile
import threading
import time

import afp_common as common
from dependency_plan import ENTRY_PIPELINE
from fixed_export import groups, native_view
from scan_store import digest, file_digest
from state import State

TARGETS = ("SML", "OCaml", "Haskell", "Scala", "Go")
RESULT = "target-compile/result/"
SUMMARY = "target-compile/summary"
TABLE = "target-compilation.csv"
REPORT_LINK = ("\n五种其他目标的编译结果见 [编译报告](target-compilation.md)"
               " 和 [逐请求回执](target-compilation.csv)。\n")
SML_REFERENCES = """structure Unsynchronized =
struct
  datatype ref = datatype ref
  val op := = op :=
  val ! = !
end
"""
SML_PROJECT = "$(SML_LIB)/basis/basis.mlb\nIsabelle_References.sml\nAFP_Code.sml\n"
SML_LARGE_SOURCE_BYTES = 32 * 1024 * 1024
SML_POLY_DRIVER = SML_REFERENCES + """;
val _ =
  let
    val source = TextIO.openIn "AFP_Code.sml"
    val contents = TextIO.inputAll source before TextIO.closeIn source
    val text = "structure AFP_Compile_Only = struct\\n" ^ contents ^ "\\nend;\\n"
    val position = Unsynchronized.ref 0
    fun get () =
      if !position >= size text then NONE
      else
        let val c = String.sub (text, !position)
        in position := !position + 1; SOME c end
    fun finish (_, NONE) = raise Fail "Static errors in AFP_Code.sml"
      | finish (_, SOME code) = (fn () => ignore (code ()))
    val artifact = PolyML.compiler (get,
      [PolyML.Compiler.CPFileName "AFP_Code.sml",
       PolyML.Compiler.CPCompilerResultFun finish])
    val _ = if !position >= size text - 2 then ()
      else raise Fail "Compiler did not consume the complete source"
  in PolyML.export ("AFP_Code", artifact) end
"""


@dataclass(frozen=True)
class Input:
    target: str
    files: tuple
    large_sml: bool = False


@dataclass(frozen=True)
class Request:
    entry: str
    group: str
    context: str
    target: str
    status: str
    job: str = ""


def executable(value, env):
    path = shutil.which(value, path=env.get("PATH"))
    if not path:
        raise ValueError("Missing target compiler: " + value)
    return str(Path(path).absolute())


def output(argv, env):
    return subprocess.check_output(argv, env=env, stdin=subprocess.DEVNULL,
                                   stderr=subprocess.STDOUT, text=True).strip()


def toolchains(env):
    scala = Path(env["SCALA_HOME"])
    jars = sorted((scala / "lib").glob("*.jar"))
    if not any(jar.name.startswith("scala3-compiler_3-") for jar in jars):
        raise ValueError("Missing Isabelle Scala 3 compiler")
    java = executable(str(Path(env["JAVA_HOME"]) / "bin/java"), env)
    mlton = executable(env.get("ISABELLE_MLTON") or "mlton", env)
    ocaml = executable(env.get("ISABELLE_OCAMLFIND") or "ocamlfind", env)
    ghc = executable(env.get("ISABELLE_GHC") or "ghc", env)
    go = executable(str(Path(env["ISABELLE_GOEXE"]) / "go") if env.get("ISABELLE_GOEXE") else "go", env)
    worker = Path(__file__).with_name("ScalaCompileWorker.java")
    configured_scala = shlex.split(env["ISABELLE_SCALAC_OPTIONS"])
    scala_args = [flag for flag in configured_scala if not flag.startswith("-J")]
    jvm_args = [flag[2:] for flag in configured_scala if flag.startswith("-J")
                and not flag.startswith(("-J-Xms", "-J-Xmx"))]
    commands = {"SML": [mlton, *shlex.split(env.get("ISABELLE_MLTON_OPTIONS", ""))],
                "OCaml": [ocaml], "Haskell": [ghc], "Scala": [java, *jvm_args], "Go": [go]}
    mlton_help = subprocess.run([mlton], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, check=False).stdout
    mlton_version = next((line for line in mlton_help.splitlines() if line.startswith("MLton ")), None)
    if not mlton_version:
        raise ValueError("Cannot determine MLton version")
    versions = {
        "SML": mlton_version,
        "OCaml": output([ocaml, "ocamlopt", "-version"], env),
        "Haskell": output([ghc, "--numeric-version"], env),
        "Go": output([go, "version"], env),
        "Scala": next(jar.name for jar in jars if jar.name.startswith("scala3-compiler_3-")),
    }
    identity = {target: {"version": versions[target], "executable": argv[0],
                         "sha256": file_digest(Path(argv[0]))} for target, argv in commands.items()}
    identity["Scala"]["jars"] = {jar.name: file_digest(jar) for jar in jars}
    identity["Scala"]["worker_sha256"] = file_digest(worker)
    identity["Scala"]["flags"] = scala_args
    identity["Scala"]["jvm_flags"] = jvm_args
    identity["SML"]["flags"] = commands["SML"][1:]
    identity["SML"]["isabelle_references_sha256"] = digest(SML_REFERENCES)
    # Isabelle ships a full-word-size Poly/ML alongside its default heap runtime.
    poly = executable(str(Path(env["ML_HOME"]).parent / env["ISABELLE_PLATFORM64"] / "poly"), env)
    commands["SML/polyml"] = [poly]
    identity["SML"]["large_source"] = {
        "min_bytes": SML_LARGE_SOURCE_BYTES, "executable": poly, "version": output([poly, "-v"], env),
        "sha256": file_digest(Path(poly)), "driver_sha256": digest(SML_POLY_DRIVER)}
    identity["OCaml"]["zarith"] = output([ocaml, "query", "zarith"], env)
    identity["Haskell"]["libdir"] = output([ghc, "--print-libdir"], env)
    return commands, identity, worker, os.pathsep.join(map(str, jars))


def fingerprints(identity, args):
    runner = file_digest(Path(__file__))
    return {target: digest({"tool": identity[target], "runner": runner, "java_heap_mb": args.java_heap_mb,
                            "available_memory": args.min_available_mb}) for target in TARGETS}


def inventory(base, state, entries, fingerprints):
    requests, jobs = [], {}
    for entry in entries:
        record = state.get("entry/" + entry)
        if record is None:
            raise ValueError("Missing published export record for " + entry)
        stage = record["full_export"]
        plan = state.get("plan/" + entry)
        if stage["mode"] != ENTRY_PIPELINE or plan["id"] != stage["plan_id"]:
            raise ValueError("Export inventory does not match the frozen plan for " + entry)
        expected = groups(plan)
        if sorted(expected) != sorted(run["group"] for run in stage["runs"]):
            raise ValueError("Missing or repeated export groups in " + entry)
        for run in stage["runs"]:
            context, group = expected[run["group"]]
            work = common.resolve_path(run["directory"])
            if (work.parent != base / "exports" / entry / group["id"] or not work.name.startswith("attempt-")
                    or run["context"] != context["id"] or run["session"] != group["session"]
                    or run["scope"] != group["entries"]):
                raise ValueError("Foreign export receipt in " + entry)
            attempts, _, error = native_view(work)
            if (error != run.get("receipt_error") or (run["closed"] and error)
                    or run.get("attempts", attempts) != attempts):
                raise ValueError("Changed native export receipt in " + entry)
            by_target = {a["target"]: a for a in attempts}
            if len(by_target) != len(attempts):
                raise ValueError("Duplicate native export target in " + entry)
            for target in TARGETS:
                attempt = by_target.get(target)
                status, key = "not_exported", ""
                if attempt and attempt["status"] == "passed":
                    evidence = common.resolve_path(attempt["evidence"])
                    check_seal(base, run, evidence)
                    if (attempt["context"] != run["context"] or attempt["batch"] != run["group"]
                            or attempt["constants"] != run["scope"]):
                        raise ValueError("Export receipt scope changed in " + entry)
                    if attempt["files"]:
                        files = sources(base, run, work, target, attempt["files"])
                        job = compile_input(target, files)
                        parameters = {"target": target, "compiler": fingerprints[target],
                                      "files": [(str(name), seal) for name, _, seal in files]}
                        if job.large_sml:
                            parameters["compiler_profile"] = "Poly/ML"
                        key = digest(parameters)
                        jobs.setdefault(key, job)
                        status = "pending"
                    elif attempt["library_only"]:
                        status = "library_only"
                    else:
                        raise ValueError("Successful export without source evidence")
                requests.append(Request(entry, group["id"], context["id"], target, status, key))
    return requests, jobs


def compile_input(target, files):
    size = sum(seal["bytes"] for _, _, seal in files)
    # Poly/ML can emit native objects without MLton's whole-program analysis.
    return Input(target, files, target == "SML" and size >= SML_LARGE_SOURCE_BYTES)


def check_seal(base, run, path):
    rel = str(path.relative_to(base))
    file = run["evidence"].get(rel)
    if not file or path.stat().st_size != file["bytes"] or file_digest(path) != file["sha256"]:
        raise ValueError("Changed sealed export file: " + str(path))
    return file


def sources(base, run, work, target, paths):
    paths = sorted(common.resolve_path(path) for path in paths)
    root = work / "artifacts" / run["context"] / "code" / target
    folder = root / run["group"]
    singleton = {"SML": "AFP_Code.sml", "OCaml": "AFP_Code.ml",
                 "Scala": "AFP_Code.scala", "Go": "export.go"}
    if any(not p.is_relative_to(root) for p in paths):
        raise ValueError("Source escapes the native target directory")
    if target in {"SML", "OCaml", "Scala"} and len(paths) != 1:
        raise ValueError("Unexpected multi-file " + target + " export")
    if len(paths) == 1 and target in singleton:
        names = [Path(singleton[target])]
    else:
        names = [path.relative_to(folder) for path in paths]
    return tuple((name, path, check_seal(base, run, path)) for name, path in zip(names, paths))


class ScalaProcess:
    def __init__(self, argv, classpath, directory, args):
        self.args = args
        active = min(getattr(args, "java_active_processors", 2), 2)
        self.command = [*argv, "-Dfile.encoding=UTF-8", "-Xmx" + str(args.java_heap_mb) + "m",
                        "-XX:ActiveProcessorCount=" + str(active), "-classpath", classpath]
        self.stderr = tempfile.TemporaryFile(dir=directory)
        self.process = None

    def start(self, worker, classpath, flags, env):
        self.process = subprocess.Popen([*self.command, str(worker), classpath, *flags],
                                        env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=self.stderr, start_new_session=True)
        if self.receive(time.monotonic() + 120) != b"ready":
            self.close_process()
            self.stderr.seek(0)
            raise ValueError("Scala compiler worker did not initialize: " +
                             self.stderr.read().decode(errors="replace")[-4000:])

    def receive(self, deadline):
        while True:
            if self.args.cancel_event.is_set():
                raise InterruptedError("Compilation interrupted")
            if deadline and time.monotonic() >= deadline:
                return None
            available = common.available_mb()
            if available is not None and available < self.args.min_available_mb:
                return b"memory_limit"
            if select.select([self.process.stdout], [], [], .2)[0]:
                return self.process.stdout.readline().strip()

    def compile(self, source, directory, log):
        fields = [str(source), str(directory), str(log)]
        if any(any(ch in field for ch in "\r\t\n") for field in fields):
            raise ValueError("Unsupported Scala compilation path")
        try:
            self.process.stdin.write(("\t".join(fields) + "\n").encode())
            self.process.stdin.flush()
            deadline = time.monotonic() + self.args.timeout if self.args.timeout else None
            response = self.receive(deadline)
        except BrokenPipeError:
            response = b""
        if response in (b"0", b"1"):
            return ("passed", 0) if response == b"0" else ("failed", 1)
        self.close_process()
        self.stderr.seek(0)
        with log.open("ab") as stream:
            shutil.copyfileobj(self.stderr, stream)
            stream.write(b"\nScala worker outcome: " + str(response).encode() + b"\n")
        return ("timeout", None) if response is None else ("failed", None)

    def close_process(self):
        if self.process:
            common.stop_process(self.process)
            self.process.stdin.close()
            self.process.stdout.close()
            self.process = None

    def close(self):
        self.close_process()
        self.stderr.close()


def native(argv, directory, log, args, env):
    with log.open("ab") as stream:
        process = subprocess.Popen(argv, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        start = time.monotonic()
        try:
            while True:
                try:
                    rc = process.wait(timeout=.2)
                    return ("passed" if rc == 0 else "failed"), rc
                except subprocess.TimeoutExpired:
                    if args.cancel_event.is_set():
                        raise InterruptedError("Compilation interrupted")
                    if args.timeout and time.monotonic() - start >= args.timeout:
                        return "timeout", None
                    available = common.available_mb()
                    if available is not None and available < args.min_available_mb:
                        stream.write(b"\nCompiler stopped at the configured available-memory limit\n")
                        return "failed", None
        finally:
            if process.poll() is None:
                common.stop_process(process)


def arguments_for(job, command, path):
    if job.large_sml:
        (path / "compile_only.ML").write_text(SML_POLY_DRIVER, encoding="utf-8")
        return [*command, "--error-exit", "--minheap", "256", "--script", "compile_only.ML"]
    if job.target == "SML":
        (path / "Isabelle_References.sml").write_text(SML_REFERENCES, encoding="utf-8")
        (path / "AFP_Code.mlb").write_text(SML_PROJECT, encoding="utf-8")
        return [*command, "-stop", "o", "-output", "AFP_Code.o", "AFP_Code.mlb"]
    if job.target == "OCaml":
        return [*command, "ocamlopt", "-w", "-p-u", "-package", "zarith", "-c", "AFP_Code.ml"]
    if job.target == "Haskell":
        modules = [str(name) for name, _, _ in job.files if name.suffix == ".hs"]
        if not modules:
            raise ValueError("Haskell export has no source modules")
        return [*command, "--make", "-no-link", "-O0", "-odir", "obj", "-hidir", "obj",
                "-XEmptyDataDecls", "-XRankNTypes", "-XScopedTypeVariables", *modules]
    if job.target == "Go":
        return [*command, "build", "-p", "1", "./..." if (path / "go.mod").is_file() else "export.go"]
    raise ValueError("Unsupported native compiler target: " + job.target)


def compile_jobs(base, state, jobs, commands, worker, classpath, args, env):
    receipts = {}
    remaining = []
    with state.connect() as db:
        rows = db.execute("SELECT key,value FROM records WHERE key>=? AND key<?", (RESULT, RESULT + chr(0x10ffff)))
        for key, raw in rows:
            job = key.removeprefix(RESULT)
            if job in jobs:
                receipt = json.loads(raw)
                log = base / receipt["log"]
                if (receipt["status"] in {"passed", "failed"} and log.is_file()
                        and file_digest(log) == receipt["log_sha256"]):
                    receipts[job] = receipt
    # Round-robin across the five tools and start the largest source trees early.
    tiers = {target: [] for target in TARGETS}
    for key, job in jobs.items():
        if key not in receipts:
            tiers[job.target].append((sum(file["bytes"] for _, _, file in job.files), key))
    for tier in tiers.values():
        tier.sort()
    while any(tiers.values()):
        remaining.extend(tier.pop()[1] for tier in tiers.values() if tier)
    print(f"[target-compilation] {len(jobs)} distinct inputs, {len(receipts)} verified cached", flush=True)
    if not remaining:
        return receipts

    storage = base / "target-compilation"
    storage.mkdir(exist_ok=True)
    cache = storage / "go-cache"
    cache.mkdir(exist_ok=True)
    env = dict(env, AFP_SCAN_RUN=str(base), GOCACHE=str(cache), GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local",
               GOWORK="off", GOFLAGS="", GOMAXPROCS="2")
    local = threading.local()
    scala_processes = []

    def compile_one(key):
        job = jobs[key]
        log = storage / "logs" / job.target / key[:2] / (key + ".log")
        log.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        evidence = {}
        with tempfile.TemporaryDirectory(prefix="build-", dir=storage) as temporary:
            path = Path(temporary)
            (path / "obj").mkdir()
            for name, source, seal in job.files:
                destination = path / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                if file_digest(destination) != seal["sha256"]:
                    raise ValueError("Export source changed during compilation")
            if job.target == "Scala":
                compiler = getattr(local, "scala", None)
                if compiler is None or compiler.process is None:
                    compiler = ScalaProcess(commands[job.target], classpath, storage, args)
                    scala_processes.append(compiler)
                    compiler.start(worker, classpath, args.scala_flags, env)
                    local.scala = compiler
                argv = [*compiler.command, str(worker), classpath, *args.scala_flags]
                log.write_text(shlex.join(argv) + "\nCompiler request: AFP_Code.scala -> obj\n", encoding="utf-8")
                status, rc = compiler.compile(path / "AFP_Code.scala", path / "obj", log)
            else:
                compiler = "SML/polyml" if job.large_sml else job.target
                argv = arguments_for(job, commands[compiler], path)
                log.write_text(shlex.join(argv) + "\n", encoding="utf-8")
                status, rc = native(argv, path, log, args, env)
                if job.large_sml and status == "passed":
                    artifact = path / "AFP_Code.o"
                    if artifact.is_file() and artifact.stat().st_size:
                        evidence["object_sha256"] = file_digest(artifact)
                    else:
                        with log.open("a", encoding="utf-8") as stream:
                            stream.write("Poly/ML exited without generating AFP_Code.o\n")
                        status = "failed"
        return {**evidence, "target": job.target, "status": status, "returncode": rc, "command": argv,
                "seconds": round(time.monotonic() - start, 3), "log": str(log.relative_to(base)),
                "log_sha256": file_digest(log)}

    batch = {}
    pool = ThreadPoolExecutor(max_workers=args.compile_workers)
    work = iter(remaining)
    pending = {}
    try:
        while True:
            while len(pending) < args.compile_workers * 2:
                key = next(work, None)
                if key is None:
                    break
                pending[pool.submit(compile_one, key)] = key
            if not pending:
                break
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                key = pending.pop(future)
                receipt = future.result()
                receipts[key] = receipt
                batch[RESULT + key] = receipt
                if len(batch) >= 128:
                    state.update(batch)
                    batch.clear()
                if len(receipts) % 1000 == 0:
                    print(f"[target-compilation] {len(receipts)}/{len(jobs)} distinct inputs", flush=True)
    finally:
        args.cancel_event.set()
        pool.shutdown(wait=True, cancel_futures=True)
        state.update(batch)
        for compiler in scala_processes:
            compiler.close()
    return receipts


def atomic_text(path, text):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(text)
    Path(stream.name).replace(path)


def attach_report(base, report):
    extra = State(base).get(SUMMARY)
    if extra:
        report["target_compilation"] = extra


def selection_id(selected):
    return digest(sorted(selected))


def checkpoint_problem(base, selected):
    state = State(base)
    export_state = state.signature(("entry/", "published/"))
    for key in (SUMMARY, SUMMARY + "/" + selection_id(selected)):
        summary = state.get(key, {})
        table = Path(base) / "report" / summary.get("table", TABLE)
        if (summary.get("complete") and set(selected).issubset(summary["scope"])
                and summary.get("export_state_sha256") == export_state
                and table.is_file() and file_digest(table) == summary.get("table_sha256")):
            return None
    return {"reason": "Five-language compilation evidence is absent, incomplete or stale"}


def publish(base, state, requests, receipts, jobs, identity, entries, chosen, full_manifest):
    report = base / "report"
    report.mkdir(exist_ok=True)
    suffix = selection_id(chosen)
    key = SUMMARY if full_manifest else SUMMARY + "/" + suffix
    stem = "target-compilation" if full_manifest else "target-compilation-" + suffix
    table = stem + ".csv"
    counts = {target: Counter() for target in TARGETS}
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=report,
                                     delete=False) as stream:
        writer = csv.writer(stream)
        writer.writerow(("entry", "group", "context", "target", "status", "source_compile_key", "log", "log_sha256"))
        for item in requests:
            receipt = receipts.get(item.job, {})
            status = receipt.get("status", item.status)
            counts[item.target][status] += 1
            writer.writerow((item.entry, item.group, item.context, item.target, status,
                             item.job, receipt.get("log", ""), receipt.get("log_sha256", "")))
    Path(stream.name).replace(report / table)
    summary = {"generated": common.timestamp(), "entries": len(entries), "full_manifest": full_manifest,
               "scope": list(entries), "distinct_inputs": len(jobs), "counts": counts, "toolchains": identity,
               "complete": set(entries) == chosen and all(not ({"pending", "timeout"} & c.keys()) for c in counts.values()),
               "table": table, "table_sha256": file_digest(report / table),
               "export_state_sha256": state.signature(("entry/", "published/"))}
    lines = ["# 五种非 Rust 目标的编译", "", f"本表覆盖 {len(entries)} 个已发布 AFP 条目。", "",
             "| 目标 | 通过 | 失败 | 超时 | 仅库映射 | 无导出源码 |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for target, count in counts.items():
        fields = [target, *(str(count[k]) for k in ("passed", "failed", "timeout", "library_only", "not_exported"))]
        lines.append("| " + " | ".join(fields) + " |")
    lines.extend(["", "使用编译器生成对象或类文件。相同源码、文件布局及编译器输入共享回执。", "",
                  f"[逐请求编译回执]({table})", ""])
    atomic_text(report / (stem + ".md"), "\n".join(lines))
    state.put(key, summary)
    if full_manifest:
        path = report / "summary.json"
        if path.is_file():
            payload = json.loads(path.read_text())
            payload["target_compilation"] = summary
            atomic_text(path, json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        overview = report / "README.md"
        if overview.is_file():
            contents = overview.read_text(encoding="utf-8")
            if REPORT_LINK not in contents:
                atomic_text(overview, contents + REPORT_LINK)
    print(json.dumps({k: summary[k] for k in ("entries", "distinct_inputs", "counts", "complete")}), flush=True)
    return summary


def run(base, selected, args, env):
    base = Path(base).resolve()
    state = State(base)
    manifest = state.get("run", {}).get("manifest")
    if not manifest or state.get("run")["experiment"] != ENTRY_PIPELINE:
        raise ValueError("Target compilation requires a fixed-plan-v3 work root")
    chosen = set(selected or manifest["order"])
    if chosen - manifest["entries"].keys() or args.compile_workers < 1:
        raise ValueError("Invalid target compilation selection or worker count")
    commands, identity, worker, classpath = toolchains(env)
    entries = [e for e in manifest["order"] if e in chosen and state.get("published/" + e)]
    requests, jobs = inventory(base, state, entries, fingerprints(identity, args))
    args.cancel_event = threading.Event()
    args.scala_flags = identity["Scala"]["flags"]
    receipts = compile_jobs(base, state, jobs, commands, worker, classpath, args, env)
    return publish(base, state, requests, receipts, jobs, identity, entries, chosen,
                   chosen == set(manifest["order"]))


def interrupt(signum, frame):
    raise KeyboardInterrupt


def main():
    from scan_frozen import active_children

    parser = common.arguments(__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, interrupt)
    env, _ = common.environment(args)
    with common.experiment_lock():
        if active_children(args.output_dir.resolve()):
            raise ValueError("Previous native processes are still active")
        result = run(args.output_dir, args.entries, args, env)
    return int(not result["complete"])


if __name__ == "__main__":
    raise SystemExit(main())
