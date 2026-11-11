"""Load per-run Isabelle code adapters and materialize their Rust support.

The isolated target uses Isabelle's actual registered printers. No reference
OCaml text or complete Stage1 Rust program is used as generation context.
"""
from __future__ import annotations
import hashlib
import json
import re
import shutil
from pathlib import Path
from .common import ROOT, Failure, digest, read, save


def syntax_hints(source):
    """Point at literal identifier underscores; never rewrite model output."""
    hints=[]
    for number,line in enumerate(source.splitlines(),1):
        match=re.search(r'\(Rust\)\s+(?:infix[lr]?\s+[0-9]+\s+)?"([^"\n]*)"',line)
        if not match:continue
        actual=match[1]
        suggested=re.sub(r"(?<=[A-Za-z0-9])_(?=[A-Za-z0-9])","'_",actual)
        if actual!=suggested:
            hints.append({'line':number,'actual_template':actual,'suggested_template':suggested,
                'reason':"A Rust identifier's literal underscore is an Isabelle argument hole unless escaped with an apostrophe. Keep actual argument holes unchanged."})
    return hints


def safe_files(files):
    if not isinstance(files,dict):raise Failure('invalid_adapter','rust_files must be an object')
    for name,content in files.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or name in {'Cargo.toml','Cargo.lock','src/main.rs','src/lib.rs'} or not isinstance(content,str):
            raise Failure('invalid_adapter_path',name)


def instance_bindings(program,bindings):
    """Resolve class operations through Thingol's existing instance equations."""
    direct={b['source']:b for b in bindings.get('operations',[])}
    dispatch={}
    for node in program['nodes']:
        statement=node['statement']
        if statement['kind']!='instance':continue
        for parameter in statement['parameters']+statement['super_parameters']:
            name='constant:'+parameter['name'];implementation=parameter['const']['symbol']
            row={'source':name,'type':statement['type'],'implementation':implementation,
                 'source_theorem':parameter.get('source_theorem'),
                 'application':direct.get(implementation,{}).get('application')}
            dispatch.setdefault(name,{})[(statement['type'],implementation)]=row
    rows=[row for group in dispatch.values() for row in group.values()]
    resolved={name for name,group in dispatch.items() if group and all(row['application'] is not None for row in group.values())}
    return rows,resolved


def support_sources(plan,bindings):
    adapter=plan['adapter'];files=dict(adapter['rust_files']);safe_files(files)
    roots=[adapter['rust_root']]
    for item in bindings.get('support_modules',[]):
        name=item['module']
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name):
            raise Failure('invalid_adapter_module','Rust support module needs a valid Rust identifier: '+name)
        path='src/'+name+'.rs'
        if path in files and files[path]!=item['code']:
            raise Failure('adapter_file_conflict',path)
        files[path]=item['code'];roots.append(f'pub mod {name};')
    return {'files':files,'root':'\n'.join(x for x in roots if x.strip())+'\n'}


def materialize_support(directory,support):
    directory=Path(directory)
    for name,content in support['files'].items():
        p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)


def load_adapter(plan,bundle,cfg,directory,executor,check_support=True):
    from .preprocessing import isabelle_command,project_info
    from .planning import manifest
    from .references import cargo
    directory=Path(directory);project=Path(bundle['source_project']);work=directory/'isabelle';work.mkdir(parents=True,exist_ok=True)
    for p in project.rglob('*'):
        if p.is_file() and p.suffix in {'.thy','.ML'}:
            dest=work/p.relative_to(project);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    theories,sessions=project_info(project)
    adapter=plan['adapter'];imports=list(dict.fromkeys(theories+['I2R_Agent.Adapter_Export']+adapter['imports']))
    if any('\n' in x or '"' in x for x in imports):raise Failure('invalid_adapter','Invalid theory import')
    source='theory Rust_Program_Setup\n imports '+ ' '.join(json.dumps(x) for x in imports)+'\nbegin\n'+adapter['declarations']+'\nend\n'
    (work/'Rust_Program_Setup.thy').write_text(source)
    original_programs=bundle.get('original_programs',bundle['programs'])
    entries=list(dict.fromkeys(e.split(':',1)[1] for p in original_programs for e in p['entries']))
    ml_names='['+', '.join(json.dumps(x) for x in entries)+']'
    export='theory Adapted_Export\n imports Rust_Program_Setup\nbegin\nML \\<open>I2R_Adapter_Export.requested := '+ml_names+'\\<close>\n'
    original_ids={n['id'] for p in original_programs+bundle['programs'] for n in p['nodes']}
    for prefix,field in [('constant:','source_names'),('type:','source_types')]:
        names=sorted(x[len(prefix):] for x in original_ids if x.startswith(prefix))
        export+='ML \\<open>I2R_Adapter_Export.'+field+' := ['+', '.join(json.dumps(x) for x in names)+']\\<close>\n'
    export+='export_code '+' '.join(entries)+' in Rust module_name Adapted\nend\n'
    (work/'Adapted_Export.thy').write_text(export)
    session='I2R_Adapter_'+hashlib.sha256((source+export).encode()).hexdigest()[:16]
    root=f'session {session} = I2R_Agent +\n options [document=false, skip_proofs=false]\n'
    session_names=sorted(set(sessions+['HOL-Library']))
    root+=' sessions\n  '+'\n  '.join(json.dumps(x) for x in session_names)+'\n'
    root+=' theories Adapted_Export\n export_files (in "exported") [2]\n  "'+session+'.Adapted_Export:code/**"\n'
    (work/'ROOT').write_text(root)
    record=executor.run(isabelle_command(cfg,'build','-e','-j','1','-o','threads=2','-o','document=false',
        '-d',ROOT/'isabelle','-d',cfg['tools']['afp'],'-d',work,session),timeout=cfg['budgets']['build_seconds'],check=False)
    if record['status']!='passed':
        diagnostic=Path(record['stdout']).read_text()+Path(record['stderr']).read_text()
        evidence={'execution':record,'theory_source':source,'printing_syntax_hints':syntax_hints(source)}
        raise Failure('adapter_isabelle_failed',diagnostic,evidence)
    paths=list((work/'exported').rglob('adapter-bindings.json'))
    if len(paths)!=1:raise Failure('adapter_export_missing','Expected one effective adapter binding export',record)
    bindings=read(paths[0]);support=support_sources(plan,bindings)
    from .program_model import build as build_source_model
    source_model=build_source_model([read(paths[0].with_name('source-model.json'))])
    before=read(paths[0].with_name('adapter-before-target.json'));after=read(paths[0].with_name('adapter-after-target.json'))
    loaded={b['source'] for key in ['types','operations'] for b in bindings[key]}
    dispatch,resolved=instance_bindings(before,bindings)
    bindings['class_dispatch']=dispatch
    declared={o['source'] for d in plan['adaptation']['decisions'] if isinstance(d,dict)
              for o in d.get('operations',[]) if isinstance(o,dict) and 'source' in o}
    audit={'loaded_symbols':sorted(loaded),'resolved_via_instances':sorted(declared & resolved),
           'declared_without_printing':sorted(declared-loaded-resolved),
           'original_nodes':sum(len(p['nodes']) for p in bundle['programs']),
           'adapter_context_nodes':len(before['nodes']),'target_remaining_nodes':len(after['nodes']),
           'non_template_printers':[b for key in ['types','operations'] for b in bindings[key]
                if b['application']['status']!='rendered']}
    # A claim that an operation is adapted must correspond to an installed rule.
    if audit['declared_without_printing']:
        raise Failure('adapter_binding_missing','Operation mappings were declared in the plan but not installed by the adapter theory',audit)
    if not check_support:
        result={'status':'loaded','theory':str(work/'Rust_Program_Setup.thy'),'theory_sha256':digest(work/'Rust_Program_Setup.thy'),
                'bindings':bindings,'support':support,'audit':audit,'isabelle_check':record,
                'support_check':{'status':'deferred','reason':'Compile support with the complete algorithm in test/repair'},
                'before_target':before,'after_target':after,'source_model':source_model,
                'limits':'Effective printer bindings are not a proof of Rust equivalence.'}
        save(directory/'loaded-adapter.json',result)
        return result
    check_dir=directory/'support-check';check_dir.mkdir()
    materialize_support(check_dir,support)
    (check_dir/'src').mkdir(exist_ok=True)
    (check_dir/'src/lib.rs').write_text(support['root'])
    (check_dir/'Cargo.toml').write_text(manifest(plan['dependencies'],package='i2r_adapter_check',build_dependencies=plan.get('build_dependencies')))
    from .storage import cargo_cache
    with cargo_cache(executor,cfg) as target:
        checked=executor.run(cargo(cfg,'check','--manifest-path',check_dir/'Cargo.toml','--target-dir',target),timeout=cfg['budgets']['build_seconds'],check=False)
    if checked['status']!='passed':
        diagnostic=Path(checked['stdout']).read_text()+Path(checked['stderr']).read_text()
        raise Failure('adapter_support_failed',diagnostic,checked)
    result={'status':'loaded','theory':str(work/'Rust_Program_Setup.thy'),'theory_sha256':digest(work/'Rust_Program_Setup.thy'),
            'bindings':bindings,'support':support,'audit':audit,'isabelle_check':record,'support_check':checked,
            'before_target':before,'after_target':after,'source_model':source_model,
            'limits':'Rendered templates are application evidence, not proof that LLM code obeys them; concrete-only printers remain visible.'}
    save(directory/'loaded-adapter.json',result)
    return result
