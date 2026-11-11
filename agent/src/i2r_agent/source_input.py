"""Independent source-model entry point; no Rust target or Thingol material."""
import hashlib
import json
import re
import shutil
from pathlib import Path
from .common import ROOT, Failure, digest, read, save
from . import tool_sources


def preprocess(project, cfg, work, executor):
    from .preprocessing import project_info, isabelle_command
    from .program_model import build
    from .planning import numeric_policy
    project, work = Path(project).resolve(), Path(work)
    target = work / 'isabelle'
    target.mkdir(parents=True, exist_ok=True)
    tools = tool_sources.manifest()
    theories, sessions = project_info(project)
    sources = {}
    for p in project.rglob('*'):
        if p.is_file() and p.suffix in {'.thy', '.ML'}:
            rel = p.relative_to(project); sources[str(rel)] = p.read_text()
            dest = target / rel; dest.parent.mkdir(parents=True, exist_ok=True)
            text = p.read_text()
            if p.suffix == '.thy':
                text = text.replace('I2R_Agent.Agent_Export', 'I2R_Source.Source_Export')
                # Only command heads are rerouted; Isabelle still parses the
                # complete explicit export expression and resolves its names.
                text = re.sub(r'(?m)^(\s*)export_code\b', r'\1i2r_export_source', text)
            dest.write_text(text)
    identity = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()[:14]
    session = 'I2R_Source_Program_' + identity
    root = f'session {session} = I2R_Source +\n options [document=false, skip_proofs=false]\n'
    sessions = [s for s in sessions if s not in {'I2R_Agent', 'I2R_Source'}]
    if sessions: root += ' sessions ' + ' '.join(json.dumps(s) for s in sessions) + '\n'
    root += ' theories ' + ' '.join(theories) + '\n export_files (in "exported") [2]\n'
    root += ''.join(f' "{session}.{t}:code/**"\n' for t in theories)
    (target/'ROOT').write_text(root)
    record = executor.run(isabelle_command(cfg, 'build', '-e', '-j', '1', '-o', 'threads=2',
        '-o', 'parallel_proofs=0', '-d', ROOT/'isabelle', '-d', tool_sources.repository('Isabelle2Rust'), '-d', cfg['tools']['afp'], '-d', target, session),
        timeout=cfg['budgets']['build_seconds'])
    model = build([read(p) for p in sorted((target/'exported').rglob('source-model.json'))])
    catalog = {}
    for p in (target/'exported').rglob('source-index.json'):
        for item in read(p)['theories']:
            f = Path(item['path']); item['available'] = f.is_file()
            if f.is_file(): item.update(sha256=digest(f), bytes=f.stat().st_size)
            catalog[item['theory']] = item
    bundle = {'workflow': cfg['generation']['workflow'], 'source_model': model, 'original_source_model': model,
        'source_project': str(project), 'sources': sources, 'source_catalog': list(catalog.values()),
        'source_hashes': {n: hashlib.sha256(s.encode()).hexdigest() for n,s in sources.items()},
        'numeric_policy': numeric_policy(cfg), 'tool_sources': tools,
        'source_collection': {'dependency_graph':'agent-owned typed occurrence graph',
            'limits':'Explicit export constants; not wildcard export patterns. No target printers or Thingol program.'}}
    bundle['numeric_policy']=numeric_contract(cfg)
    metadata = read(project/'case.json') if (project/'case.json').exists() else {}
    if metadata.get('id'): bundle['case']=metadata['id']
    # Small administrative summary for existing study/report storage, not an IR.
    bundle['programs'] = [{'entries':model['entries'], 'nodes':[], 'sccs':model['recursive_groups']}]
    save(work/'source-build.json', record); save(work/'program.json', bundle)
    tool_sources.verify(tools)
    return bundle


def numeric_contract(cfg):
    from .planning import numeric_policy
    bundle={'numeric_policy':numeric_policy(cfg)}
    if cfg['generation']['workflow']in {'segmented-v7','segmented-v8'}:
        bundle['numeric_policy']['representation_selection'] = ('Checked mode: nat u128, int i128; explicit range failure, no silent wrap or big-integer fallback.' if cfg['preprocessing']['numeric_mode']=='checked' else 'Arbitrary mode: prefer dashu_int::UBig for nat and dashu_int::IBig for int (dashu-int =0.6.2); justify any alternative. Preserve totalized source operations; generic parameters remain generic.')
    return bundle['numeric_policy']
