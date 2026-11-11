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
    if cfg.get('generation',{}).get('workflow') in {'source-v6','segmented-v7','segmented-v8'}:
        from .source_input import preprocess as source_preprocess
        return source_preprocess(project,cfg,work,executor)
    tools = tool_sources.manifest()
    exported = build_project(project, cfg, Path(work) / "isabelle", executor)
    programs = []
    for path in sorted(exported.rglob("*program.json")):
        program = read(path)
        if program.get("schema_version") != 1 or not program.get("entries"):
            raise Failure("invalid_program", f"Invalid program bundle: {path}")
        program["unimplemented"] = [n["id"] for n in program["nodes"] if n["statement"]["kind"] == "unimplemented"]
        programs.append(program)
    if not programs:
        raise Failure("missing_program", "Isabelle export produced no Thingol program.json")
    automatic = cfg.get('preprocessing',{}).get('mode') == 'auto'
    representation = {'mode':'llm_designed'} if automatic else cfg.get("representation", {"numeric":"bigint","sequence":"vec"})
    if not automatic and representation != {"numeric": "bigint", "sequence": "vec"}:
        raise Failure("unsupported_representation", "This implementation currently supports bigint + Vec; other profiles require explicit contracts")
    sources = {str(p.relative_to(project)): p.read_text() for p in Path(project).rglob("*")
               if p.is_file() and p.suffix in {".thy", ".ML"}}
    metadata_path = Path(project) / "case.json"
    metadata = read(metadata_path) if metadata_path.exists() else {}
    for name in metadata.get("source_files", []):
        path = Path(name)
        sources[str(path)] = path.read_text()
    bundle = {"schema_version": 1, "programs": programs, "sources": sources,
              "source_hashes": {k: hashlib.sha256(v.encode()).hexdigest() for k,v in sources.items()},
              "representation": representation, "contract": metadata.get("contract"),
              "external_boundaries": [{"symbol": n, "status": "unresolved"} for p in programs for n in p["unimplemented"]]}
    from .program_model import build as build_source_model
    bundle['source_model'] = build_source_model([read(p) for p in sorted(exported.rglob('source-model.json'))])
    bundle['original_source_model'] = bundle['source_model']
    from .adapters import support_sources
    base_paths=sorted(exported.rglob('adapter-bindings.json'))
    if len(base_paths)!=1:raise Failure('base_binding_export','Expected one base-adapted export')
    base_bindings=read(base_paths[0])
    bundle['base_adapter']={'bindings':base_bindings,'support':support_sources(
        {'adapter':{'rust_files':{},'rust_root':''}},base_bindings)}
    bundle['base_setup']={'path':str(tool_sources.repository('Isabelle2Rust')/'translate/Rust_Base_Setup.thy'),
        'mode':'Original backend registration with serializer hook; original base Isar declarations executed in agent theory; Rust_Agent derives from this Rust target.'}
    snapshots=[]
    for path in sorted(exported.rglob('*before-target.json')):
        raw=read(path)
        snapshots.append({'stage':'before_target','path':str(path),'sha256':digest(path),
                          'nodes':len(raw['nodes']),'edges':sum(len(n['dependencies']) for n in raw['nodes']),
                          'program':raw})
    catalog=[]
    for path in sorted(exported.rglob('*source-index.json')):
        catalog.extend(read(path)['theories'])
    catalog=list({item['theory']:item for item in catalog}.values())
    for item in catalog:
        path=Path(item['path'])
        item['available']=path.is_file()
        if path.is_file():item.update(sha256=digest(path),bytes=path.stat().st_size)
    wire=cfg['testing'].get('transport','dashu-ubig')
    if wire=='auto':wire='native-u128' if cfg.get('preprocessing',{}).get('numeric_mode','checked')=='checked' else 'dashu-ubig'
    wire_type={'dashu-ubig':'dashu_int::UBig','dashu-ibig':'dashu_int::IBig','native-u128':'u128','native-i128':'i128'}.get(wire)
    if automatic and wire_type is None:raise Failure('unsupported_transport','Choose auto, dashu-ubig/dashu-ibig, or native-u128/native-i128')
    from .inventory import inventory
    inv=inventory(programs,catalog,sources,metadata)
    bundle.update(source_project=str(Path(project).resolve()),source_catalog=catalog,
        structure_snapshots=snapshots,target_evidence=[],external_inventory=inv['external_implementations'],
        program_inventory=inv,dependency_origin='Isabelle Code_Symbol.Graph; unchanged',
        observation_binding={'input':'decimal natural-number list','output':'decimal natural-number list',
            'rust_wire_api':f'observe(&[{wire_type}]) -> Vec<{wire_type}>',
            'restriction':'Test transport only. Internal representations are independent.'})
    if not any(entry.endswith('.observe') for program in programs for entry in program['entries']):
        bundle.pop('observation_binding',None)
    from .planning import numeric_policy
    bundle['numeric_policy']=numeric_policy(cfg)
    bundle['source_collection']={'policy':'Full source facts archived; agent views use source specifications, typed execution equations, uses, types/classes and effective binding boundaries.',
        'full_import_source_closure':False,'dependency_graph':'Agent-owned constant-occurrence/type graph; Thingol retained only for the existing target bridge and legacy audits'}
    bundle['workload']={'contract':metadata.get('contract'),'observed_wire_domain':metadata.get('observation'),
        'performance_workload':'not supplied by project','hidden_tests_included':False}
    if metadata.get('id'):
        from .suites import scoped_performance_input,input_bits
        workload=scoped_performance_input(metadata['id'],input_bits(cfg))
        bundle['case']=metadata['id'];bundle['kernel']=metadata.get('kernel')
        bundle['workload'].update(performance_workload='case benchmark summary',performance_input_items=len(workload),
            performance_integer_bit_length_max=max((abs(x).bit_length() for x in workload),default=0),
            note='Benchmark sizes do not establish a bound for all source values.')
    save(Path(work)/'structure-manifest.json',{'before':snapshots})
    save(Path(work)/'program-inventory.json',inv)
    tool_sources.verify(tools)
    bundle["tool_sources"] = tools
    save(Path(work) / "program.json", bundle)
    return bundle


