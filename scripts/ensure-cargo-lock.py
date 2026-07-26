#!/usr/bin/env python3

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def cargo_command():
    return shlex.split(os.environ.get("CARGO", "cargo"))


def lock_is_current(manifest: Path):
    result = subprocess.run(
        [
            *cargo_command(),
            "metadata",
            "--locked",
            "--offline",
            "--format-version",
            "1",
            "--manifest-path",
            str(manifest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def main():
    if len(sys.argv) not in (2, 3):
        print(
            "usage: ensure-cargo-lock.py MANIFEST [SHARED_LOCK]",
            file=sys.stderr,
        )
        return 2

    manifest = Path(sys.argv[1]).resolve()
    shared_lock = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else None
    lock = manifest.parent / "Cargo.lock"

    if lock.is_file() and lock_is_current(manifest):
        return 0

    original = lock.read_bytes() if lock.is_file() else None
    if shared_lock is not None and shared_lock.is_file():
        shutil.copyfile(shared_lock, lock)
        if lock_is_current(manifest):
            return 0

    lock.unlink(missing_ok=True)
    result = subprocess.run(
        [
            *cargo_command(),
            "generate-lockfile",
            "--offline",
            "--manifest-path",
            str(manifest),
        ],
        check=False,
    )
    if result.returncode == 0:
        return 0

    if original is not None:
        lock.write_bytes(original)
    else:
        lock.unlink(missing_ok=True)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
