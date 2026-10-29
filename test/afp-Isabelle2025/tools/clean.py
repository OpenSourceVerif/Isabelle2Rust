#!/usr/bin/env python3
"""Preview or clean an owned AFP work directory, always protecting retained data."""
import fcntl
from pathlib import Path

import afp_common as common


CACHE = ('_build', '_tmp', 'cache')


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
    from state import State, NAME
    base = validate_root(base)
    if not (base / NAME).is_file() or not State(base).get("run"):
        raise ValueError("Cleanup requires an initialized AFP work directory")
    names = CACHE + (("compilation", "rust-stage2", "report") if reset else ()) + (("exports",) if reset == "export" else ())
    result = []
    for name in names:
        path = base / name
        if path.is_symlink() or not path.resolve().is_relative_to(base):
            raise ValueError("Cleanup target escapes work: " + name)
        if path.exists():
            result.append(path)
    return result


def clean(base, reset=None, apply=False):
    from state import State
    base = validate_root(base)
    paths = targets(base, reset)
    result = {"preview": not apply, "reset": reset, "paths": [str(p) for p in paths]}
    if not apply:
        return result
    lockpath = common.EXPERIMENT / "setup/batch.lock"
    lockpath.parent.mkdir(parents=True, exist_ok=True)
    with lockpath.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("An AFP phase is running; cleanup refused") from None
        paths = targets(base, reset)
        state = State(base)
        from scan_frozen import active_children
        if active_children(base):
            raise ValueError("Native AFP children are still running; cleanup refused")
        if reset:
            # Invalidate results before deleting their evidence. A crash during
            # cleanup can leave unused files, but cannot leave a false success.
            replacements = {}
            for key in state.keys("entry/"):
                record = state.get(key)
                record.pop("full_compile", None)
                if reset == "export":
                    record.pop("full_export", None)
                replacements[key] = record
            remove = ["audit.json", "audit-preview.json", "compile-checkpoint.json"]
            if reset == "export":
                remove += ["export-checkpoint.json", *state.keys("export-progress/")]
            state.update(replacements, remove)
        for path in paths:
            state.remove_tree(path)
        state.compact()
    return result
