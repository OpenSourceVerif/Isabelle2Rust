from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def read(path):
    path = Path(path)
    if path.suffix == ".toml":
        return tomllib.loads(path.read_text())
    return json.loads(path.read_text())


def merge(base, changes):
    result = dict(base)
    for key, value in changes.items():
        result[key] = merge(result.get(key, {}), value) if isinstance(value, dict) else value
    return result


class Failure(Exception):
    def __init__(self, code, message, evidence=None):
        super().__init__(message)
        self.code, self.evidence = code, evidence


class Executor:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.sequence = len(list(self.directory.glob("*.json")))

    def run(self, argv, cwd=None, timeout=300, env=None, stdin=None, check=True):
        self.sequence += 1
        stem = self.directory / f"{self.sequence:04d}"
        started = time.monotonic()
        record = {"command": list(map(str, argv)), "cwd": str(cwd or ROOT),
                  "started_at": now(), "timeout_seconds": timeout}
        process_env = dict(os.environ)
        process_env.update(env or {})
        with stem.with_suffix(".stdout").open("w") as out, stem.with_suffix(".stderr").open("w") as err:
            process = subprocess.Popen(record["command"], cwd=cwd or ROOT, env=process_env,
                                       stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True, text=True)
            try:
                process.communicate(stdin, timeout=timeout)
                record.update(status="passed" if process.returncode == 0 else "failed", returncode=process.returncode)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
                try:os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:pass
                    process.wait()
                record.update(status="timeout" if isinstance(error, subprocess.TimeoutExpired) else "interrupted", returncode=process.returncode)
                if isinstance(error, KeyboardInterrupt):
                    save(stem.with_suffix(".json"), record)
                    raise
        record.update(seconds=time.monotonic() - started,
                      stdout=str(stem.with_suffix(".stdout")), stderr=str(stem.with_suffix(".stderr")))
        save(stem.with_suffix(".json"), record)
        if check and record["status"] != "passed":
            tail = (Path(record["stdout"]).read_text() + Path(record["stderr"]).read_text())[-18000:]
            raise Failure("tool_" + record["status"], tail, record)
        return record


def config(path=None):
    local = read(ROOT / "config/local.toml") if (ROOT / "config/local.toml").exists() else {}
    defaults = read(ROOT / "config/default.toml")
    overrides=read(path) if path else {}
    effective=merge(merge(defaults, local),overrides)
    if effective.get('generation',{}).get('workflow')in {'segmented-v7','segmented-v8'}:
        from .segmented_config import origins
        effective['_configuration_sources']=origins(effective,[('config/default.toml',defaults),('config/local.toml',local),(str(path) if path else 'no-explicit-override',overrides)])
    return effective
