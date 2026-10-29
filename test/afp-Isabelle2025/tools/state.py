"""One transactional current state for an AFP run; no historical generations.

SQLite commits replace whole records atomically. Native logs, XML and generated
sources remain files; only their current owners retain references to them.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

NAME = "state.sqlite3"


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def locate(path):
    path = Path(path).absolute()
    for parent in (path.parent, *path.parents):
        if (parent / NAME).is_file():
            return parent
    return None


class State:
    def __init__(self, base):
        self.base = Path(base).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("PRAGMA user_version=1")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.base / NAME, timeout=60)
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM records WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        self.update({key: value})

    def update(self, values, remove=()):
        # Publication and removal share a transaction, so an interruption can
        # expose only the previous complete state or the next complete state.
        with self.connect() as db:
            db.executemany("INSERT OR REPLACE INTO records VALUES (?, ?)",
                           [(k, encode(v)) for k, v in values.items()])
            db.executemany("DELETE FROM records WHERE key=?", [(k,) for k in remove])

    def keys(self, prefix=""):
        with self.connect() as db:
            return [r[0] for r in db.execute("SELECT key FROM records ORDER BY key") if r[0].startswith(prefix)]

    def signature(self, prefixes):
        checksum = hashlib.sha256()
        with self.connect() as db:
            for key, value in db.execute("SELECT key,value FROM records ORDER BY key"):
                if any(key.startswith(p) for p in prefixes):
                    checksum.update(key.encode() + b"\0" + value.encode() + b"\0")
        return checksum.hexdigest()

    def remove_tree(self, path):
        # Every removal is checked inside this run. Neither a symlink nor a
        # computed ancestor may turn retirement into deletion of shared inputs.
        path = Path(path).absolute()
        resolved = path.resolve()
        redirected = any(p.is_symlink() for p in (path, *path.parents) if p != self.base and p.is_relative_to(self.base))
        if redirected or resolved == self.base or not resolved.is_relative_to(self.base):
            raise ValueError("Refusing removal outside the run: " + str(path))
        relative = str(resolved.relative_to(self.base))
        keys = [k for k in self.keys() if k == relative or k.startswith(relative + "/")]
        self.update({}, keys)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    def compact(self):
        # Reclaim replaced payloads rather than retaining database page history.
        with self.connect() as db:
            db.execute("VACUUM")
