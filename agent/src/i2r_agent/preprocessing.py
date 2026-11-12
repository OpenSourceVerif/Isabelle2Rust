from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from .common import ROOT, Failure, digest, read, save
from . import tool_sources


def isabelle_command(cfg, *args):
    executable = cfg["tools"]["isabelle"]
    # AFP is optional for this FPP corpus; omit an unset directory.
    args = list(args)
    args = [value for i, value in enumerate(args) if not (value == "-d" and i + 1 < len(args) and args[i + 1] == "") and not (value == "" and i > 0 and args[i - 1] == "-d")]
    return [executable, "env", "bash", "-c",
            'export ISABELLE_HEAPS="$1"; shift; exec "$@"', "--",
            str(cfg.get("tools",{}).get("isabelle_heaps", ROOT / "cache/heaps")), executable, *map(str, args)]


def project_info(project):
    project = Path(project).resolve()
    settings = read(project / "agent.toml") if (project / "agent.toml").exists() else {}
    theories = settings.get("isabelle", {}).get("theories", ["Export"])
    sessions = set(settings.get("isabelle", {}).get("sessions", []))
    # Qualified theory imports expose the existing session; unqualified imports
    # stay inside the copied project. No parallel CLI entry list is maintained.
    for path in project.glob("*.thy"):
        text = path.read_text()
        imports = text.split("imports", 1)[-1].split("begin", 1)[0]
        for name in re.findall(r'"([^"\n]+)"', imports):
            if "." in name and "/" not in name:
                sessions.add(name.split(".")[0])
    sessions.discard("I2R_Agent")
    return theories, sorted(sessions)


def build_project(project, cfg, work, executor, reference=False):
    tools = tool_sources.manifest()
    project, work = Path(project), Path(work)
    work.mkdir(parents=True, exist_ok=True)
    theories, sessions = project_info(project)
    for p in project.rglob("*"):
        if p.is_file() and p.suffix in {".thy", ".ML"}:
            dest = work / p.relative_to(project)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
    if reference:
        for theory in theories:
            path = work / (theory + ".thy")
            text = path.read_text().replace('"I2R_Agent.Agent_Export"', '"Rust.Rust_BigInt_Setup"')
            # Isabelle still parses each export command. Only the target changes.
            pattern = r'(export_code\s+[\s\S]*?\s+in\s+)Rust_Agent(\s+module_name\s+\w+)'
            text, n = re.subn(pattern, lambda m: m[1] + 'Rust' + m[2] + '\n' +
                re.sub(r'\s+in\s+$', ' nat_of_integer integer_of_nat in ', m[1]) + 'OCaml' + m[2], text)
            if not n:
                raise Failure("invalid_export", "Expected export_code … in Rust_Agent module_name NAME")
            path.write_text(text)
    identity = hashlib.sha256("".join(p.read_text() for p in sorted(work.rglob("*.thy"))).encode()).hexdigest()[:14]
    session = ("I2R_Reference_" if reference else "I2R_Program_") + identity
    parent = "Rust" if reference else "I2R_Agent"
    quoted = lambda s: '"' + s + '"'
    root = f'session {session} = {parent} +\n  options [document=false, skip_proofs=false, timeout=1200]\n'
    if sessions:
        root += '  sessions\n    ' + '\n    '.join(map(quoted, sessions)) + '\n'
    root += '  theories\n    ' + '\n    '.join(theories) + '\n'
    root += '  export_files (in "exported") [2]\n' + ''.join(f'    "{session}.{t}:code/**"\n' for t in theories)
    (work / "ROOT").write_text(root)
    command = isabelle_command(cfg, "build", "-e", "-j", "1", "-o", "threads=2", "-o", "parallel_proofs=0",
        "-o", "document=false", "-d", ROOT / "isabelle", "-d", tool_sources.repository("Isabelle2Rust"),
        "-d", cfg["tools"]["afp"], "-d", work, session)
    record = executor.run(command, timeout=cfg["budgets"]["build_seconds"])
    tool_sources.verify(tools)
    save(work / "build.json", {"tool_sources": tools, "session": session, "record": record, "source_hashes": {
        str(p.relative_to(work)): digest(p) for p in work.rglob("*.thy")}})
    return work / "exported"


def preprocess(project, cfg, work, executor):
    """Extract the source model used by the delivered workflow."""
    from .source_input import preprocess as source_preprocess
    return source_preprocess(project, cfg, work, executor)
