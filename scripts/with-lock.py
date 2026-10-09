#!/usr/bin/env python3
"""Run a command under an advisory file lock on Linux and macOS."""

import fcntl
import os
import sys


def main():
    if len(sys.argv) < 3:
        sys.exit("Usage: with-lock.py LOCK_FILE COMMAND [ARG ...]")
    # Keep the descriptor open across exec so the command owns the lock until
    # it exits. Never unlink the file: waiters must lock the same inode.
    with open(sys.argv[1], "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        os.set_inheritable(lock.fileno(), True)
        os.execvp(sys.argv[2], sys.argv[2:])


if __name__ == "__main__":
    main()
