"""Trial-local immutable evidence and reusable Cargo build caches."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import platform

from .common import ROOT, save


def link(source, destination):
    source, destination = Path(source).resolve(), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".link-tmp")
    temporary.symlink_to(os.path.relpath(source, destination.parent.resolve()), target_is_directory=source.is_dir())
    temporary.replace(destination)


def attach_adapter(directory, loaded, programs):
    directory = Path(directory)
    # Evidence is shared only within this trial; no cross-case knowledge store.
    payload = {"loaded": loaded, "programs": programs,
               "theory_sha256": hashlib.sha256(Path(loaded["theory"]).read_bytes()).hexdigest() if loaded.get("theory") else None}
    key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    version = directory.parent / "adapter-artifacts" / key
    if not (version / "complete.json").exists():
        version.mkdir(parents=True, exist_ok=True)
        save(version / "loaded-adapter.json", loaded)
        adapter = version / "adapter"; adapter.mkdir(exist_ok=True)
        if loaded.get("theory"):
            shutil.copy2(loaded["theory"], adapter / "Rust_Program_Setup.thy")
        for field, name in [("bindings", "bindings.json"), ("before_target", "before-target.json"), ("after_target", "after-target.json")]:
            if field in loaded: save(adapter / name, loaded[field])
        save(adapter / "original-program.json", programs)
        # Consumers never modify shared evidence; revision creates another version.
        for p in version.rglob("*"):
            if p.is_file(): p.chmod(0o444)
        save(version / "complete.json", {"sha256": key})
    link(version / "loaded-adapter.json", directory / "loaded-adapter.json")
    link(version / "adapter", directory / "adapter")


@contextmanager
def cargo_cache(executor, cfg):
    base = executor.__dict__.get("shared_cargo_root", executor.directory.parent / "cargo-cache")
    key = {"tools": cfg["tools"], "machine": platform.machine(), "system": platform.system(),
           "env": {k:v for k,v in os.environ.items() if k.startswith(("CARGO_", "RUST", "CC", "CXX"))}}
    target = Path(base) / hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:20]
    target.mkdir(parents=True, exist_ok=True)
    # Hold across build, Clippy and binary copy: same-named candidates cannot race.
    with (target / ".agent.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield target


def artifact_files(directory):
    for base, _, names in os.walk(directory, followlinks=True):
        for name in names:
            yield Path(base) / name
