#!/usr/bin/env python3
"""Shared execution, resource monitoring and reporting for the AFP 2025 experiment."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time
import tempfile

HERE = Path(__file__).resolve().parent
# The tool directory is a resource root; experiments and installations may
# live elsewhere. Relative artifact references are resolved against the repository.
EXPERIMENT = HERE.parent
DEFAULT_PROJECT = next(p for p in EXPERIMENT.parents
                       if (p / "translate").is_dir() and (p / "ROOT").is_file())
PROJECT = DEFAULT_PROJECT
WORK = EXPERIMENT / "work"
CONFIG = {}


def configure(path=None):
    """Load a server-local JSON configuration without importing shell code."""
    global CONFIG, PROJECT, WORK
    candidate = path or os.environ.get("AFP_CONFIG")
    if candidate is None:
        local = EXPERIMENT / "setup/server.local.json"
        candidate = local if local.is_file() else None
    CONFIG = json.loads(Path(candidate).read_text()) if candidate else {}
    PROJECT = Path(CONFIG.get("repository", DEFAULT_PROJECT)).resolve()
    WORK = Path(CONFIG.get("work", EXPERIMENT / "work")).resolve()
    if CONFIG.get("user_home"):
        # Isabelle supports USER_HOME as its settings/cache root. Its release
        # identifier must stay unchanged because it is also the version string.
        os.environ["USER_HOME"] = CONFIG["user_home"]
    cargo_bin = str(Path(CONFIG.get("cargo_bin", Path.home() / ".cargo/bin")))
    if cargo_bin not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = cargo_bin + os.pathsep + os.environ.get("PATH", "")
    if not (PROJECT / "translate").is_dir() or not (PROJECT / "ROOT").is_file():
        raise ValueError("repository must contain ROOT and translate/")
    return CONFIG


def resolve_path(value):
    """Resolve repository-relative artifacts or absolute external work paths."""
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT / path).resolve()


def isabelle_source_root(project=None):
    """Use installed sources on a server and explicit reference trees in fixtures."""
    project = Path(project or PROJECT)
    if CONFIG.get("isabelle") and project.resolve() == Path(CONFIG.get("repository", DEFAULT_PROJECT)).resolve():
        return Path(CONFIG["isabelle"]).resolve().parent.parent / "src"
    return project / "temp/Isabelle2025_ref/src"


configure()
BEGIN = "(* BEGIN GENERATED AFP RUST EXPORT SESSIONS *)"
END = "(* END GENERATED AFP RUST EXPORT SESSIONS *)"


def read_record(path, default=None):
    """Read current run metadata from SQLite; standalone fixtures use JSON."""
    from state import State, locate
    path = Path(path).absolute()
    base = locate(path)
    return State(base).get(str(path.relative_to(base)), default) if base else read_json(path, default)


def write_record(path, value):
    """Replace one run record without creating another JSON sidecar."""
    from state import State, locate
    path = Path(path).absolute()
    base = locate(path)
    if base:
        State(base).put(str(path.relative_to(base)), value)
    else:
        write_json(path, value)


def has_record(path):
    sentinel = object()
    return read_record(path, sentinel) is not sentinel


def remove_record(path):
    from state import State, locate
    path = Path(path).absolute()
    base = locate(path)
    if base:
        State(base).update({}, [str(path.relative_to(base))])
    elif path.exists():
        path.unlink()


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path, value):
    """Durably replace one record; callers use one receipt as a transaction."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # A unique temporary also avoids two unrelated sidecars sharing a .tmp.
    # fsync both the bytes and directory entry before acknowledging a commit.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=path.parent, prefix=path.name + ".",
                                     suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def relative(path):
    path = path.resolve()
    return str(path.relative_to(PROJECT)) if path.is_relative_to(PROJECT) else str(path)


def quote(text):
    """Quote Isabelle outer-syntax strings, including symbolic constant names."""
    # Isabelle symbols such as \<alpha> are atomic lexer symbols. Escaping
    # their leading backslash as an ordinary character corrupts the token.
    symbols = re.findall(r"\\<[^>]+>|.", text, re.DOTALL)
    return '"' + "".join(
        s if s.startswith("\\<") else s.replace("\\", "\\\\").replace('"', '\\"')
        for s in symbols) + '"'


def arguments(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--isabelle", default=os.environ.get("ISABELLE", "isabelle"))
    parser.add_argument("--afp", type=Path, help="complete AFP 2025 root or its thys/ directory")
    parser.add_argument("--entries", nargs="+", help="entry directory names (default: all)")
    parser.add_argument("--retry-failed", action="store_true", help="retry incomplete/failed entries only")
    parser.add_argument("--timeout", type=int, default=0,
                        help="seconds per build/process; 0 disables both watchdog and session timeout")
    parser.add_argument("--stack-space-mb", type=int, default=512,
                        help="Poly/ML stack reserve; avoids the small default on large code certificates")
    parser.add_argument("--max-heap-mb", type=int, default=4500)
    parser.add_argument("--java-heap-mb", type=int, default=1536)
    parser.add_argument("--java-active-processors", type=int, default=2,
                        help="bound JVM worker/native-thread memory independently of ML proof threads")
    parser.add_argument("--min-available-mb", type=int, default=512,
                        help="stop a command below this available-memory threshold; 0 disables")
    parser.add_argument("--skip-proofs", action="store_true",
                        help="explicit exploratory mode; recorded separately from checked proofs")
    parser.add_argument("--refresh-manifest", action="store_true")
    return parser


def environment(args):
    """Reject wrong releases before interpreting ROOT files or reusing reports."""
    if args.timeout < 0:
        raise ValueError("timeout must be nonnegative")
    for name in ("max_heap_mb", "java_heap_mb", "stack_space_mb", "java_active_processors"):
        if getattr(args, name) <= 0:
            raise ValueError(name.replace("_", "-") + " must be positive")
    if args.min_available_mb < 0:
        raise ValueError("min-available-mb must be nonnegative")
    version = subprocess.check_output([args.isabelle, "version"], text=True).strip()
    if version != "Isabelle2025":
        raise ValueError("Expected Isabelle2025, got " + version)
    if args.afp is None:
        detected = subprocess.check_output([args.isabelle, "getenv", "-b", "AFP"], text=True).strip()
        args.afp = Path(detected) if detected else PROJECT / "temp/afp-Isabelle2025"
    root = args.afp.resolve()
    if root.name == "thys":
        root = root.parent
    version_file = root / "etc/version"
    if not version_file.is_file() or not re.search(r"(?m)^VERSION=['\"]?2025['\"]?\s*$",
                                                  version_file.read_text()):
        raise ValueError("AFP must be the Isabelle2025 release: " + str(root))
    roots = root / "thys/ROOTS"
    entries = [line.strip() for line in roots.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    # A small hand-picked AFP subset cannot serve as the requested full archive.
    if len(entries) < 800 or any(not (root / "thys" / entry / "ROOT").is_file() for entry in entries):
        raise ValueError("Incomplete AFP archive; install the full 2025 release")
    args.afp = root
    # Initialize Isabelle first: getsettings otherwise overwrites ML_OPTIONS and
    # Java flags supplied by the caller. Its inherited settings marker makes
    # subsequent tool invocations retain these per-experiment resource bounds.
    initialized = subprocess.check_output([args.isabelle, "env", "-0"])
    env = dict(os.fsdecode(item).split("=", 1) for item in initialized.split(b"\0")
               if b"=" in item)
    env.pop("RUSTC_BOOTSTRAP", None)
    # Explicit stack space is essential when inspecting deeply nested code equations.
    env["ML_OPTIONS"] = ("--minheap 256 --maxheap " + str(args.max_heap_mb)
                         + " --stackspace " + str(args.stack_space_mb))
    compiler_settings = CONFIG.get("compilers", {})
    if not isinstance(compiler_settings, dict) or any(
            not isinstance(k, str) or not k.startswith("ISABELLE_") or not isinstance(v, str)
            for k, v in compiler_settings.items()):
        raise ValueError("config.compilers must map ISABELLE_* names to string values")
    # This section configures external conditional compilers, not arbitrary
    # Isabelle state, heap locations or proof/executor options.
    allowed_compilers = {"ISABELLE_CC", "ISABELLE_OCAMLFIND", "ISABELLE_GOEXE",
                         "ISABELLE_GOROOT", "ISABELLE_SMLNJ", "ISABELLE_CAKEML_HOME",
                         "ISABELLE_GHC", "ISABELLE_MLTON"}
    if set(compiler_settings) - allowed_compilers:
        raise ValueError("unsupported compiler setting: " +
                         ", ".join(sorted(set(compiler_settings) - allowed_compilers)))
    env.update(compiler_settings)
    env["ISABELLE_TOOL_JAVA_OPTIONS"] = (
        "-Djava.awt.headless=true -Xms128m -Xmx" + str(args.java_heap_mb) + "m -Xss16m"
        + " -XX:ActiveProcessorCount=" + str(args.java_active_processors))
    env["CARGO_BUILD_JOBS"] = "1"
    env["ISABELLE_CARGO"] = str(Path(CONFIG.get("cargo_bin", Path.home() / ".cargo/bin")) / "cargo")
    metadata = {"isabelle": version, "afp_version": "2025", "afp_root": str(root),
                "afp_roots_sha256": hashlib.sha256(roots.read_bytes()).hexdigest(),
                "proofs": "skipped" if args.skip_proofs else "checked",
                "threads": 1, "ml_heap_mb": args.max_heap_mb,
                "java_heap_mb": args.java_heap_mb, "java_active_processors": args.java_active_processors,
                "command_timeout_seconds": args.timeout,
                "stack_space_mb": args.stack_space_mb, "compiler_settings": compiler_settings}
    return env, metadata


def available_mb():
    """Linux MemAvailable accounts for reclaimable cache, unlike MemFree."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return None


@contextmanager
def experiment_lock():
    """Serialize report writers as well as builds, preventing lost checkpoints."""
    directory = EXPERIMENT / "setup"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "batch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


@contextmanager
def build_lock():
    """Use the Makefile's lock so scans cannot race ordinary project builds."""
    with (PROJECT / ".isabelle-build.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield



def process_identity(pid):
    """Stable boot/PID/birth identity; reparenting is not a process restart."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        return boot, pid, fields[19]
    except (OSError, IndexError, ValueError):
        return None


def process_parent(pid):
    """PPID is topology used to find descendants, never an identity field."""
    try:
        return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1])
    except (OSError, IndexError, ValueError):
        return None


def identity_matches(record):
    """Match the current boot, PID and birth time; parent changes are irrelevant."""
    actual = process_identity(record.get("pid", -1))
    identity = record.get("identity")
    return bool(actual and identity and list(actual) == list(identity))


def stop_process(process):
    """Stop detached Isabelle descendants while guarding against PID reuse."""
    identities = {}
    parents = {}
    for path in Path("/proc").iterdir():
        if path.name.isdigit():
            pid = int(path.name)
            identity = process_identity(pid)
            if identity:
                identities[pid] = identity
                parents[pid] = process_parent(pid)
    children = {process.pid}
    while True:
        found = {pid for pid, parent in parents.items() if parent in children}
        if found <= children:
            break
        children.update(found)

    def send(pid, sig):
        if process_identity(pid) != identities.get(pid) or pid not in identities:
            return
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass

    if process_identity(process.pid) == identities.get(process.pid):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for pid in children - {process.pid}:
        send(pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        send(process.pid, signal.SIGKILL)
        process.wait()
    for pid in children - {process.pid}:
        send(pid, signal.SIGKILL)


def command(argv, log, args, env):
    """Monitor resources and retain command identity even across host shutdowns."""
    log.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    outcome = {"status": "starting", "command": argv, "log": relative(log), "started": timestamp()}
    evidence = log.with_suffix(log.suffix + ".json")
    # A session may spend hours proving before its entry checkpoint is written.
    # Its database record survives loss of the driver or WSL environment,
    # while the text log remains the complete unmodified subprocess output.
    write_record(evidence, outcome)
    # Every native descendant inherits the run marker, so cleanup can find it
    # even when its original driver and parent process have disappeared.
    from state import locate
    base = locate(log)
    if base:
        env = dict(env, AFP_SCAN_RUN=str(base))
    minimum = available_mb()
    with log.open("w") as stream:
        stream.write("$ " + shlex.join(argv) + "\n")
        stream.flush()
        try:
            process = subprocess.Popen(argv, cwd=PROJECT, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as error:
            outcome.update(status="failed", finished=timestamp(), error=str(error))
            write_record(evidence, outcome)
            raise
        reason = None
        try:
            try:
                # Keep startup-record writes within descendant cleanup too:
                # an interrupted checkpoint write must not orphan its process.
                boot = Path("/proc/sys/kernel/random/boot_id")
                outcome.update(status="running", pid=process.pid, identity=process_identity(process.pid),
                               boot_id=boot.read_text().strip() if boot.is_file() else None)
                write_record(evidence, outcome)
                while process.poll() is None:
                    memory = available_mb()
                    if memory is not None:
                        minimum = min(minimum, memory) if minimum is not None else memory
                    # Zero disables both watchdog and Isabelle's session timeout.
                    if args.timeout and time.monotonic() - start > args.timeout:
                        reason = "timeout"
                    elif memory is not None and memory < args.min_available_mb:
                        reason = "memory_limit"
                    if reason:
                        break
                    time.sleep(0.5)
            finally:
                # Interruptions and resource limits must not leave ML children.
                if process.poll() is None:
                    stop_process(process)
        except BaseException as error:
            outcome.update(status="interrupted", returncode=process.returncode, finished=timestamp(),
                           seconds=round(time.monotonic() - start, 2), min_available_mb=minimum,
                           interruption=type(error).__name__)
            write_record(evidence, outcome)
            raise
        outcome.update(status=reason or ("passed" if process.returncode == 0 else "failed"),
                       returncode=process.returncode, finished=timestamp(),
                       seconds=round(time.monotonic() - start, 2), min_available_mb=minimum)
    if outcome["status"] != "passed":
        outcome["error_excerpt"] = ("\n".join(log.read_text(errors="replace").splitlines()[-24:]))[-12000:]
    write_record(evidence, outcome)
    return outcome


def build_options(args):
    # Disable document production, but check proofs unless explicitly requested.
    options = ["-j", "1", "-o", "threads=1", "-o", "parallel_proofs=0",
               "-o", "document=false", "-o", "timeout=" + str(args.timeout),
               "-o", "skip_proofs=" + str(args.skip_proofs).lower()]
    # ROOT session options take precedence over the system's timeout default.
    # Disable Isabelle's build timer explicitly for unlimited experiments: a
    # local timeout otherwise survives timeout=0, while timeout_scale=0 would
    # schedule termination immediately instead of disabling the timer.
    if args.timeout == 0:
        options += ["-o", "timeout_build=false"]
    return options


def manifest_identity(args):
    """Invalidate discovery caches on ROOT, import/source or parser changes.

    Content hashing is read-only input verification, not candidate discovery.
    Include all AFP files because ML_file and external assets can change imports
    without changing ROOTS or a .thy suffix.
    """
    root = args.afp / "thys"
    sha = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        sha.update(str(path.relative_to(root)).encode())
        sha.update(b"\0")
        sha.update(hashlib.sha256(path.read_bytes()).digest())
    return {"manifest_version": 4, "afp_root": str(args.afp),
            "sources_sha256": sha.hexdigest(),
            "parser_sha256": hashlib.sha256((HERE / "sessions.scala").read_bytes()).hexdigest()}


def manifest(args, env):
    # Isolated runs retain their discovery inputs/logs without overwriting
    # the manifest evidence belonging to an earlier experiment.
    directory = getattr(args, "manifest_dir", WORK / "_build")
    path = directory / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = manifest_identity(args)
    cached = read_json(path)
    if cached is not None and cached.get("identity") == identity and not args.refresh_manifest:
        return cached
    manifest_env = dict(env, AFP_THYS=str(args.afp / "thys"), AFP_MANIFEST=str(path))
    with build_lock():
        result = command([args.isabelle, "scala", str(HERE / "sessions.scala")],
                         directory / "manifest.log", args, manifest_env)
    if result["status"] != "passed":
        raise RuntimeError("Isabelle session discovery failed; see " + result["log"])
    value = read_json(path)
    value["identity"] = identity
    write_json(path, value)
    return value


def candidates(theories):
    return sorted({constant for constants in theories.values() for constant in constants})


def select(args, data, result, phase, required_phases=()):
    names = args.entries if args.entries else data["order"]
    unknown = set(names) - data["entries"].keys()
    if unknown:
        raise ValueError("Unknown entries: " + ", ".join(sorted(unknown)))
    names = list(dict.fromkeys(names))
    if args.retry_failed:
        def incomplete(entry):
            record = result["entries"][entry]
            status = record.get(phase, {}).get("status") if phase else record.get("status")
            return status not in ("passed", "no_candidates") or (
                status != "no_candidates" and any(
                    record.get(name, {}).get("status") != "passed" for name in required_phases))
        names = [entry for entry in names if incomplete(entry)]
    return names
