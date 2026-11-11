"""Read workspace tool sources directly; record hashes, never copy their sources."""
from pathlib import Path
import os
from .common import ROOT, Failure, digest


def repository(name):
    path = ROOT.parent if name == 'Isabelle2Rust' else Path(os.environ.get('RUSTLIGHTAST_ROOT', ROOT.parent.parent / name))
    required = {"Isabelle2Rust": "ROOT", "RustLightAST": "Cargo.toml"}
    if name not in required or not (path / required[name]).is_file():
        raise Failure("missing_tool_repository", "Expected workspace repository: " + str(path))
    return path.resolve()


def manifest():
    files = {}
    roots = {name: repository(name) for name in ("Isabelle2Rust", "RustLightAST")}
    trees = {"Isabelle2Rust": ["translate", "optimize/src", "optimize/.cargo"],
             "RustLightAST": ["src", ".cargo"]}
    metadata = {"Isabelle2Rust": ["ROOT", "ROOTS", "rust-toolchain.toml", "optimize/Cargo.toml", "optimize/Cargo.lock", "optimize/build.rs"],
                "RustLightAST": ["Cargo.toml", "Cargo.lock", "build.rs", "rust-toolchain.toml"]}
    for name, root in roots.items():
        paths = [root / rel for rel in metadata[name]]
        paths += [p for rel in trees[name] for p in (root / rel).rglob("*")
                  if not {"target", ".git", "__pycache__"}.intersection(p.relative_to(root).parts)]
        for path in sorted(set(paths)):
            if path.is_file() and path.name != ".DS_Store":
                files[name + "/" + str(path.relative_to(root))] = digest(path)
    return {"schema_version": 1, "mode": "workspace-reference",
            "repositories": {name: str(path) for name, path in roots.items()}, "files": files}


def verify(expected):
    if manifest() != expected:
        raise Failure("tool_sources_changed", "Workspace tool sources changed during this operation; start a new run")
