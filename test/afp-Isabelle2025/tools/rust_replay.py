"""Replay every frozen request for Rust with the experiment's current numeric profile."""

from collections import Counter, defaultdict, deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import nullcontext
import copy
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import threading
import xml.etree.ElementTree as ET

import afp_common as common
import fixed_export
import fixed_plan
import full
from dependency_plan import ENTRY_PIPELINE, SETUPS, TARGETS
from entry_audit import command_evidence, validate_crate
from scan_frozen import active_children, tools_identity
from scan_store import Store, digest, file_digest
from state import State

OLD_PROFILE = "Rust.Rust_BigInt_Setup"
PROFILE = SETUPS[0]
PHASES = ("stage1_compile", "optimization", "stage2_compile")


@dataclass(frozen=True)
class Request:
    entry: str
    group: str
    context: str
    session: str
    source: Path
    seal: str
    previously_failed: bool

    @property
    def key(self):
        return self.entry + "/" + self.group


def rust_request(original):
    request = ET.fromstring(original)
    parents = request.findall("parent")
    numeric = [n for n in parents if n.get("name") in {OLD_PROFILE, PROFILE}]
    if (request.tag != "request" or request.get("mode") != "export"
            or [n.get("name") for n in request.findall("target")] != list(TARGETS)
            or len(numeric) != 1):
        raise ValueError("Expected a frozen six-target request with one numeric profile")
    numeric[0].set("name", PROFILE)
    request.set("mode", "rust-replay")
    for target in request.findall("target"):
        if target.get("name") != "Rust":
            request.remove(target)
    return request


def inventory(source, original, entries):
    for entry in entries:
        record = original.get("entry/" + entry)
        stage = record["full_export"]
        plan = original.get("plan/" + entry)
        groups = fixed_export.groups(plan)
        if (stage["mode"] != ENTRY_PIPELINE or stage["plan_id"] != plan["id"]
                or sorted(groups) != sorted(run["group"] for run in stage["runs"])):
            raise ValueError("Published requests differ from frozen plan: " + entry)
        recorded = record.get("full_compile", {})
        for run in stage["runs"]:
            context, group = groups[run["group"]]
            work = common.resolve_path(run["directory"])
            if (work.parent != source / "exports" / entry / group["id"]
                    or run["context"] != context["id"] or run["session"] != group["session"]
                    or run["scope"] != group["entries"]):
                raise ValueError("Foreign frozen request: " + run["directory"])
            manifest = work / "artifacts" / context["id"] / "code" / "Rust" / group["id"] / "Cargo.toml"
            previous = recorded.get(str(manifest), {}).get(PHASES[0], {})
            path = work / "request.xml"
            seal = run["evidence"][str(path.relative_to(source))]["sha256"]
            yield Request(entry, group["id"], context["id"], group["session"], path, seal,
                          previous.get("status") == "failed")


def prepare_request(base, job):
    original = job.source.read_bytes()
    if digest_bytes(original) != job.seal:
        raise ValueError("Changed frozen request: " + str(job.source))
    request = rust_request(original)
    if request.attrib != {"mode": "rust-replay", "context": job.context,
                          "group": job.group, "module": "AFP_Code"}:
        raise ValueError("Foreign frozen request XML")
    work = full.next_attempt(base / "exports" / job.key)
    (work / "request.xml").write_bytes(ET.tostring(request, encoding="utf-8"))
    return work


def digest_bytes(contents):
    return hashlib.sha256(contents).hexdigest()


def read_export(base, job, work, batch):
    attempts, finished, error = fixed_export.native_view(work)
    if finished is None:
        return None
    if finished.tag != "finished" or finished.attrib != {"context": job.context, "group": job.group} or error:
        raise ValueError("Invalid native Rust witness: " + job.key)
    roots = [node.get("name") for node in ET.parse(work / "request.xml").getroot().findall("entry")]
    by_target = {a["target"]: a for a in attempts}
    if len(attempts) != len(by_target) or any(
            a["context"] != job.context or a["batch"] != job.group or a["constants"] != roots for a in attempts):
        raise ValueError("Native Rust receipt changed scope: " + job.key)
    rust = by_target.get("Rust")
    manifest = ""
    failure = ""
    if rust and rust["status"] == "passed":
        if set(by_target) != {"frontend", "Rust"} or by_target["frontend"]["status"] != "passed":
            raise ValueError("Missing strict frontend witness: " + job.key)
        crate = work / "artifacts" / job.context / "code" / "Rust" / job.group / "Cargo.toml"
        if str(crate) in rust["files"]:
            manifest = str(crate)
        elif rust["files"] or not rust["library_only"]:
            raise ValueError("Successful Rust export without a crate or library witness: " + job.key)
        status = "passed" if manifest else "library_only"
    else:
        diagnostic = rust or by_target.get("frontend") or by_target.get("context")
        if not diagnostic or diagnostic["status"] != "failed":
            raise ValueError("Failed Rust export without a native diagnostic: " + job.key)
        status, failure = "failed", diagnostic["error"]
    return {"status": status, "manifest": manifest, "directory": str(work), "batch": str(batch),
            "failure": failure, "evidence": fixed_export.seal(base, {"directory": str(work)})}


def verify_export(base, item):
    store = Store(base)
    for path, seal in item["evidence"].items():
        name = store.path(path)
        if not name.is_file() or name.stat().st_size != seal["bytes"] or file_digest(name) != seal["sha256"]:
            raise ValueError("Changed Rust export evidence: " + path)
    return item


def export_batch(base, jobs, args, env):
    state = State(base)
    publish_lock = getattr(args, "publish_lock", nullcontext())
    results = {}
    pending = []
    for job in jobs:
        cached = state.get("export/" + job.key)
        if cached:
            results[job.key] = verify_export(base, cached)
        else:
            pending.append(job)
    retry = deque([(pending, True)] if pending else [])
    while retry:
        jobs, reattempt = retry.popleft()
        if args.cancel_event.is_set():
            raise InterruptedError("Rust export interrupted")
        batch = full.next_attempt(base / "native" / jobs[0].session / digest([job.key for job in jobs])[:20])
        works = [prepare_request(base, job) for job in jobs]
        # Both the regular process command and the headless launcher take
        # the common theory context from the first request in the batch.
        shutil.copyfile(works[0] / "request.xml", batch / "request.xml")
        queue = batch / "queue.txt"
        queue.write_text("".join(str(work) + "\n" for work in works))
        State(batch)
        actual = dict(env, AFP_RUST_EXPORT_QUEUE=str(queue), AFP_RUST_QUIET="1")
        command = fixed_plan.native_command(jobs[0].session, batch, args, actual, "fixed_export.ML")
        remaining = []
        updates = {}
        for job, work in zip(jobs, works):
            item = read_export(base, job, work, batch)
            if item:
                results[job.key] = updates["export/" + job.key] = item
            else:
                remaining.append((job, work))
        if updates:
            with publish_lock:
                state.update(updates)
        if not remaining:
            continue
        if command["status"] == "passed":
            raise ValueError("Rust process completed without receipts: " + str(batch))
        if reattempt:
            # Completed prefixes are durable. Retry the remaining requests in
            # a fresh native process, starting with the first unfinished group.
            if len(remaining) > 1 and updates:
                retry.append(([remaining[0][0]], False))
                retry.append(([job for job, _ in remaining[1:]], True))
            else:
                retry.append(([job for job, _ in remaining], False))
            continue
        if updates and len(remaining) > 1:
            retry.append(([remaining[0][0]], False))
            retry.append(([job for job, _ in remaining[1:]], True))
            continue
        status = "timeout" if command["status"] == "timeout" else "failed"
        updates = {}
        for job, work in remaining:
            failure = command.get("error_excerpt") or "Native process exited with " + str(command["returncode"])
            item = {"status": status, "manifest": "", "directory": str(work), "batch": str(batch),
                    "failure": failure, "evidence": fixed_export.seal(base, {"directory": str(work)})}
            results[job.key] = item
            if status != "timeout":
                updates["export/" + job.key] = item
        if updates:
            with publish_lock:
                state.update(updates)
    return results


def compile_key(base, exported):
    root = common.resolve_path(exported["manifest"]).parent.relative_to(base)
    prefix = str(root) + "/"
    files = {name[len(prefix):]: seal["sha256"] for name, seal in exported["evidence"].items()
             if name.startswith(prefix)}
    if "Cargo.toml" not in files:
        raise ValueError("Rust crate missing its manifest seal")
    return digest(files), files


def compile_crate(base, worker, entry, key, files, manifest, args, env, optimizer):
    state = State(base)
    worker_state = State(worker)
    record_key = "compile/" + key
    saved = state.get(record_key, {})
    if not saved.get("item", {}).get("complete"):
        saved = worker_state.get(record_key, {})
    manifest = saved.get("manifest", manifest)
    record = {"full_export": {"mode": ENTRY_PIPELINE, "runs": [{
        "closed": True, "attempts": [{"target": "Rust", "status": "passed", "files": [manifest]}],
    }]}, "full_compile": {manifest: saved["item"]} if saved else {}}

    def persist():
        item = record["full_compile"][manifest]
        if item.get("stage1_inputs", files) != files:
            raise ValueError("Rust compilation input differs from export seal: " + manifest)
        worker_state.put(record_key, {"manifest": manifest, "item": item})

    # Retries get fresh logs and build copies, while previous native errors
    # with a terminal compiler exit retain their original diagnosis.
    for index in range(2):
        full.compile_entry(entry, record, worker, args, env, optimizer, persist)
        item = record["full_compile"][manifest]
        if full.crate_complete(item):
            if "command_evidence" not in item:
                item["command_evidence"] = command_evidence(base, item)
                persist()
            validate_crate(base, manifest, item, optimizer)
            return {"manifest": manifest, "item": item}
        worker_state.put("interrupted/" + key + "/" + Path(item["directory"]).name, item)
        if index == 0:
            record["full_compile"].clear()
    return {"manifest": manifest, "item": item}


def batches(jobs, size):
    by_context = defaultdict(list)
    for job in jobs:
        by_context[(job.entry, job.session, job.context)].append(job)
    # Round robin over contexts. Large branches should start before short
    # branches exhaust the available native workers.
    queue = deque(sorted(by_context.values(), key=lambda xs: -len(xs)))
    while queue:
        group = queue.popleft()
        yield group[:size]
        if len(group) > size:
            queue.append(group[size:])


def recover_compile_results(base, state):
    existing = set(state.keys("compile/"))
    for database in sorted(base.glob("workers/*/state.sqlite3")):
        worker = State(database.parent)
        recovered = {}
        for key in worker.keys("compile/"):
            if key in existing:
                continue
            result = worker.get(key)
            item = result["item"]
            if (item.get("complete") and item.get("command_evidence")
                    and digest(item["stage1_inputs"]) == key.removeprefix("compile/")):
                recovered[key] = result
                existing.add(key)
        if recovered:
            state.update(recovered)


def run(base, jobs, args, env, optimizer):
    args.cancel_event = threading.Event()
    options = copy.copy(args)
    options.wait_for_exit = True
    options.publish_lock = threading.Lock()
    env = dict(env, AFP_RUST_REPLAY_ROOT=str(base))
    state = State(base)
    recover_compile_results(base, state)
    finished = {}
    for slot in range(args.compile_workers):
        worker = State(base / "workers" / str(slot))
        with worker.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
    work = iter(batches(jobs, args.batch_size))
    slots = list(range(args.compile_workers))
    exports, compiled, queued = {}, {}, set()
    ready = deque()
    pending_export, pending_compile = {}, {}
    crate_keys = {}
    with ThreadPoolExecutor(max_workers=args.export_workers) as export_pool, \
            ThreadPoolExecutor(max_workers=args.compile_workers) as compile_pool:
        try:
            while True:
                if shutil.disk_usage(base).free < args.min_free_gib * 1024 ** 3:
                    raise OSError(f"Free disk space fell below {args.min_free_gib} GiB")
                while len(pending_export) < args.export_workers and len(ready) < args.compile_workers * 4:
                    requests = next(work, None)
                    if requests is None:
                        break
                    pending_export[export_pool.submit(export_batch, base, requests, options, env)] = requests
                while slots and ready:
                    entry, key, files, manifest = ready.popleft()
                    slot = slots.pop()
                    settings = full.compilation_environment(env, base, slot)
                    future = compile_pool.submit(compile_crate, base, base / "workers" / str(slot), entry,
                                                 key, files, manifest, options, settings, optimizer)
                    pending_compile[future] = key, slot
                if not pending_export and not pending_compile:
                    with options.publish_lock:
                        state.update(finished)
                    return exports, compiled, crate_keys
                done, _ = wait((*pending_export, *pending_compile), timeout=5, return_when=FIRST_COMPLETED)
                for future in done:
                    if future in pending_export:
                        requests = pending_export.pop(future)
                        result = future.result()
                        for job in requests:
                            exported = result[job.key]
                            exports[job.key] = exported
                            if not exported["manifest"]:
                                continue
                            key, files = compile_key(base, exported)
                            crate_keys[job.key] = key
                            if key not in queued:
                                queued.add(key)
                                ready.append((job.entry, key, files, exported["manifest"]))
                        if len(exports) // 1000 != (len(exports) - len(requests)) // 1000:
                            print(f"[rust-replay] exported {len(exports)}/{len(jobs)}, "
                                  f"compiled {len(compiled)}/{len(queued)} distinct crates", flush=True)
                    else:
                        key, slot = pending_compile.pop(future)
                        slots.append(slot)
                        compiled[key] = finished["compile/" + key] = future.result()
                        if len(finished) >= 128:
                            with options.publish_lock:
                                state.update(finished)
                            finished.clear()
                        if len(compiled) % 1000 == 0:
                            print(f"[rust-replay] compiled {len(compiled)} distinct crates", flush=True)
        except BaseException:
            args.cancel_event.set()
            for future in (*pending_compile, *pending_export):
                future.cancel()
            with options.publish_lock:
                state.update(finished)
            raise


def phase_status(item, phase):
    value = item[phase]
    commands = value.get("checks", [value])
    if any(command["status"] == "timeout" for command in commands):
        return "timeout"
    return value["status"] if value["status"] in {"passed", "blocked"} else "failed"


def publish(base, jobs, exports, compiled, keys, origin):
    if len(jobs) != len(exports) or set(keys.values()) != compiled.keys():
        raise ValueError("Rust replay inventory is incomplete")
    directory = base / "report"
    directory.mkdir(exist_ok=True)
    counts = {phase: Counter() for phase in ("export", *PHASES)}
    former_failures = Counter()
    table = directory / "rust-replay.csv"
    with table.with_suffix(".tmp").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("entry", "context", "group", "export", *PHASES, "compile_key",
                         "manifest", "export_evidence", "compile_evidence", "error"))
        for job in jobs:
            exported = exports[job.key]
            key = keys.get(job.key, "")
            compiled_item = compiled.get(key, {}).get("item")
            statuses = [phase_status(compiled_item, p) for p in PHASES] if compiled_item else ["not_run"] * len(PHASES)
            counts["export"][exported["status"]] += 1
            for phase, status in zip(PHASES, statuses):
                counts[phase][status] += 1
            if job.previously_failed:
                former_failures[statuses[0]] += 1
            writer.writerow((job.entry, job.context, job.group, exported["status"], *statuses, key,
                             exported["manifest"], exported["directory"],
                             compiled_item["directory"] if compiled_item else "", exported["failure"]))
    table.with_suffix(".tmp").replace(table)
    summary = {"origin": origin, "profile": PROFILE, "requests": len(jobs), "distinct_crates": len(compiled),
               "counts": counts, "previous_stage1_failures": former_failures,
               "unresolved": sum(c["timeout"] for c in counts.values()),
               "table_sha256": file_digest(table), "checked": common.timestamp()}
    common.write_json(directory / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return int(bool(summary["unresolved"]))


def main():
    parser = common.arguments(__doc__)
    parser.add_argument("--from-work", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--min-free-gib", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--cargo", default="cargo +1.94.0")
    args = parser.parse_args()
    source, base = args.from_work.resolve(), args.output_dir.resolve()
    if source.is_relative_to(base) or base.is_relative_to(source) or not (source / "state.sqlite3").is_file():
        raise ValueError("Use a separate output directory and an audited source run")
    if args.skip_proofs or args.refresh_manifest or args.batch_size < 1 or args.min_free_gib < 0:
        raise ValueError("Rust replay uses checked frozen requests and valid worker limits")
    env, _ = common.environment(args)
    env.update(CARGO_NET_OFFLINE="true", CARGO_INCREMENTAL="0",
               RUSTFLAGS=(env.get("RUSTFLAGS", "") + " -Awarnings").strip())
    original = State(source)
    audit = original.get("audit.json", {})
    manifest = original.get("run", {}).get("manifest", {})
    if not audit.get("passed") or audit["entries"] != manifest.get("order"):
        raise ValueError("Source run does not have a full terminal audit")
    entries = [entry for entry in manifest["order"] if not args.entries or entry in args.entries]
    if args.entries and set(args.entries) != set(entries):
        raise ValueError("Unknown AFP entries")
    optimizer = source / "_build/optimizer-target/debug/cargo-opt"
    origin = {"work": str(source), "audit": digest(audit), "optimizer": file_digest(optimizer), "entries": entries,
              "tools": digest(tools_identity()), "cargo": subprocess.check_output(shlex.split(args.cargo) + ["--version"],
                                                                                  env=env, text=True).strip()}
    with common.experiment_lock():
        if active_children(base) or active_children(base, "AFP_RUST_REPLAY_ROOT"):
            raise ValueError("Previous native processes are still active")
        state = State(base)
        with state.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
        previous = state.get("rust-replay")
        if previous and previous != origin:
            raise ValueError("Rust replay inputs changed")
        if not previous and any(base.glob("exports/*")):
            raise ValueError("Use a fresh output directory for Rust replay")
        state.put("rust-replay", origin)
        jobs = list(inventory(source, original, entries))
        print(f"[rust-replay] {len(entries)} entries, {len(jobs)} frozen Rust requests", flush=True)
        exports, compiled, keys = run(base, jobs, args, env, optimizer)
        if digest(original.get("audit.json")) != origin["audit"]:
            raise ValueError("Source audit changed during Rust replay")
        return publish(base, jobs, exports, compiled, keys, origin)


def interrupt(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupt)
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
