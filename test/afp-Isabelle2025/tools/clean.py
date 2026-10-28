#!/usr/bin/env python3
"""Preview or clean an owned AFP work directory, always protecting retained data."""
import fcntl
from pathlib import Path
import shutil

import afp_common as common


CACHE = ('_build', '_tmp', 'cache')
COMPILE = ('compilation', 'rust-stage2', 'logs/compile', 'optimizer-build.json', 'optimizer-build.log')
EXPORT = ('exports', 'export-progress', 'export-checkpoint.json', 'frontend-faults', 'report')


def validate_root(base):
    """Refuse aliases, retained-tree ancestors and shared dependency subtrees."""
    original = Path(base).absolute()
    base = original.resolve()
    protected = [common.EXPERIMENT / p for p in ('scan', 'report', 'tools', 'tests', 'setup')]
    protected += [common.PROJECT, common.PROJECT.parent / 'RustLightAST']
    # The repository itself is forbidden, but its dedicated work subdirectory
    # is allowed. All other protected trees forbid both ancestors and children.
    if original.is_symlink() or base in (common.PROJECT, common.PROJECT.parent):
        raise ValueError('Refusing unsafe work root')
    for p in protected[:5]:
        p = p.resolve()
        if base.is_relative_to(p) or p.is_relative_to(base):
            raise ValueError('Cleanup would reach protected tree: ' + str(p))
    if (common.PROJECT.parent / 'RustLightAST').resolve().is_relative_to(base) or base.is_relative_to((common.PROJECT.parent / 'RustLightAST').resolve()):
        raise ValueError('Cleanup would reach the shared RustLightAST dependency')
    return base


def targets(base, reset=None):
    """Select only fixed children of a marked experiment work directory."""
    base = validate_root(base)
    marker = common.read_json(base / 'afp-work.json', {})
    if marker.get('kind') != 'afp-work-v1':
        raise ValueError('Cleanup requires an initialized AFP work directory')
    names = CACHE + (COMPILE if reset in ('compile', 'export') else ()) + (EXPORT if reset == 'export' else ())
    result = []
    for name in names:
        path = base / name
        if path.is_symlink() or not path.resolve().is_relative_to(base):
            raise ValueError('Cleanup target is a symlink or escapes work: ' + name)
        if path.exists():
            result.append(path)
    return result


def clean(base, reset=None, apply=False):
    """Deletion is opt-in; explicit resets also invalidate the relevant results."""
    paths = targets(base, reset)
    base = Path(base).resolve()
    result = {'preview': not apply, 'reset': reset, 'paths': [str(p) for p in paths]}
    if not apply:
        return result
    # Use the same lock as export/compile. A busy run is rejected immediately,
    # so cleanup cannot wait and then erase the output of a running phase.
    lockpath = common.EXPERIMENT / 'setup/batch.lock'
    lockpath.parent.mkdir(parents=True, exist_ok=True)
    with lockpath.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('An AFP phase is running; cleanup refused') from None
        paths = targets(base, reset)
        if reset:
            import full
            _, state, exports = full.load(base)
            for entry in list(state['entries']):
                record = state['entries'][entry]
                for key in list(record):
                    if key.startswith('full_compile') or (reset == 'export' and key.startswith('full_export')):
                        del record[key]
                if isinstance(state['entries'], full.EntryStore):
                    state['entries'].commit(entry, full.entry_compiled(record, exports[entry], full.serializer_signature()))
            full.save(base, state, exports)
        for path in paths:
            # shutil.rmtree does not follow descendant symlinks on Linux.
            # Only the fixed child names above can become deletion roots.
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    return result
