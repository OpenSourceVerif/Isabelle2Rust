"""Executed diagnostics for a saved candidate; never performance feedback."""
import json
import tomllib
from pathlib import Path
from .common import save
from .references import cargo


def compiler_messages(record):
    result=[]
    for line in Path(record['stdout']).read_text().splitlines():
        try: row=json.loads(line)
        except ValueError: continue
        if row.get('reason')=='compiler-message':
            m=row['message']
            if m.get('level')=='error': result.append(m)
    return result


def runtime(crate, inputs, cfg, executor, directory, arguments=()):
    crate, directory=Path(crate).resolve(),Path(directory).resolve()
    target=directory/'target'; directory.mkdir(parents=True,exist_ok=True)
    manifest=crate/'Cargo.toml';package=tomllib.loads(manifest.read_text())['package']['name']
    build=executor.run(cargo(cfg,'build','--manifest-path',manifest,'--target-dir',target),
        env={'RUSTFLAGS':'-C debuginfo=2 -C opt-level=0'},timeout=cfg['budgets']['build_seconds'],check=False)
    result={'build':build,'scope':'Debug replay of exact current sources; no timing feedback','reproductions':[]}
    if build['status']=='passed':
        for values in inputs[:3]:
            run=executor.run([target/'debug'/package,*arguments],stdin=' '.join(map(str,values))+'\n',
                env={'RUST_BACKTRACE':'full'},timeout=cfg['testing']['process_timeout'],check=False)
            result['reproductions'].append({'input':values,'status':run['status'],
                'stdout':Path(run['stdout']).read_text(),
                'stderr':'\n'.join(s for s in Path(run['stderr']).read_text().splitlines() if not s.startswith('I2R_KERNEL_NS ')),
                'record':run})
    else: result['build_diagnostic']=Path(build['stdout']).read_text()+Path(build['stderr']).read_text()
    save(directory/'diagnostic.json',result)
    return result
