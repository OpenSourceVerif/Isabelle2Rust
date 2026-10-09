#!/bin/sh
# Run a command with an enlarged stack, respecting the OS hard limit.
set -eu

if [ "$#" -lt 2 ]; then
    echo 'Usage: with-stack.sh STACK_KB COMMAND [ARG ...]' >&2
    exit 1
fi
requested=$1
shift
case "$requested" in
    ''|*[!0-9]*|0) echo 'STACK_KB must be a positive integer' >&2; exit 1 ;;
esac

# macOS commonly limits the stack to slightly less than 64 MiB.
hard=$(ulimit -H -s)
if [ "$hard" != unlimited ] && [ "$requested" -gt "$hard" ]; then
    requested=$hard
fi
ulimit -S -s "$requested"
exec "$@"
