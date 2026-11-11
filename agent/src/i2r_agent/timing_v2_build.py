"""Rebuild timing-only executables from immutable, validated algorithm artifacts."""
from pathlib import Path
import os,re,shlex,shutil
from .common import ROOT,read,save,digest,Failure,Executor,config,now
from . import timing_drivers as drivers
from .references import compile_rust
from .native_baseline import shell_launcher,haskell_strictness

RUN_ID='kernel-v2-20261102'
STORE=ROOT/'data/baselines/runs/timing-v2'/RUN_ID


def inventory():
    from .workbench import dataset
    result=[]
    for case in dataset()['cases']:
        for card in case['implementations']:
            active=card['implementation_id'] in case['active_baseline_implementation_ids'] if card['kind']=='baseline' else card['round_id']==case['latest_round']
            if not active or card['status']!='passed':continue
            lang=card['implementation_id'].rsplit(':',1)[-1] if card['kind']=='baseline' else 'rust'
            path=Path(card['record_path'] if card['kind']=='baseline' else card['reference'])
            record=read(path)
            ref=record['references'][lang] if lang in ['ocaml','stage2'] else record.get('reference') if lang!='rust' else None
            if ref and (digest(ref['source'])!=ref['sha256'] or digest(ref['binary'])!=ref['binary_sha256']):raise Failure('artifact_changed',str(path))
            if card['kind']=='baseline':
                work=ROOT/'data/baselines'/card['baseline_id']/'artifacts'/lang/RUN_ID
            else:work=path.parent/RUN_ID
            result.append({'id':card['implementation_id'],'case':case['id'],'language':lang,'kind':card['kind'],
                           'source_record':str(path),'source':card['code_path'],'work':str(work),'reference':ref,
                           'baseline_id':card.get('baseline_id') or case['active_baseline_id'],
                           'numeric_profile':card['numeric_profile'],'round_id':card['round_id']})
    return result


def copy_crate(source,dest,include_harness=False):
    source=Path(source);dest.mkdir(parents=True,exist_ok=True)
    files=[p for p in source.rglob('*') if p.is_file() and 'target' not in p.relative_to(source).parts and
           (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock','rust-toolchain.toml','rust-config.json']) and
           (include_harness or 'harness' not in p.relative_to(source).parts)]
    hashes={str(p):digest(p) for p in files}
    for p in files:
        target=dest/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    return hashes


def build(item,cfg):
    work=Path(item['work']);work.mkdir(parents=True,exist_ok=True);saved=work/'build-v2.json'
    key={'builder':digest(__file__),'drivers':digest(drivers.__file__)}
    if saved.exists() and read(saved)['builder_identity']!=key:
        if (work/'measurement-v2.json').exists():raise Failure('timing_driver_changed','Measured builds are immutable: '+str(saved))
        save(work/'build-history'/(read(saved)['builder_identity']['drivers'][:16]+'.json'),read(saved))
        saved.unlink()
    if saved.exists():
        r=read(saved)
        if r['builder_identity']!=key:raise Failure('timing_driver_changed','Use a new build version: '+str(saved))
        if not all(Path(p).is_file() and digest(p)==h for p,h in r['source_hashes'].items()):raise Failure('algorithm_changed',str(saved))
        if not all(Path(p).is_file() and digest(p)==h for p,h in r['artifact_hashes'].items()):raise Failure('timing_artifact_changed',str(saved))
        return r
    ex=Executor(work/'build-logs');lang=item['language'];source=Path(item['source'])
    binary=work/'reference';isabelle=cfg['tools']['isabelle'];hashes={}
    if lang in ['rust','stage2','rust-crate']:
        crate=source if lang in ['rust','rust-crate'] else Path(item['reference']['crate'])
        hashes=copy_crate(crate,work/'crate',include_harness=lang=='rust')
        target=work/'crate/harness' if lang=='rust' else work/'crate'
        main=target/'src/main.rs';main.write_text(drivers.rust(main.read_text()))
        if (work/'crate/rust-config.json').exists() and lang=='rust':
            from .segmented_run import compile_crate
            check=compile_crate(target,read(work/'crate/rust-config.json'),cfg,ex,False)
        else:check=compile_rust(target,cfg,ex)
        if check['status']!='passed':raise Failure('timing_build_failed',lang,check)
        shutil.copy2(check['binary'],binary)
    elif lang=='ocaml':
        hashes[str(source)]=digest(source);shutil.copy2(source,work/'reference.ml')
        modules=[name for name,sig in re.findall(r'module\s+(\w+)\s*:\s*sig(.*?)end\s*=',source.read_text(),re.S) if all(re.search(r'\bval\s+'+sym+r'\s*:',sig) for sym in ['kernel_run','kernel_prepare','kernel_encode'])]
        if len(modules)!=1:raise Failure('ocaml_module_ambiguous',str(source))
        (work/'main.ml').write_text(drivers.ocaml(modules[0]));(work/'clock.c').write_text(drivers.OCAML_CLOCK)
        ex.run([cfg['tools']['ocamlfind'],'ocamlopt','-package','zarith','-linkpkg','-o',binary,'clock.c','reference.ml','main.ml'],cwd=work,env={'PATH':str(Path(cfg['tools']['ocamlfind']).parent)+os.pathsep+os.environ['PATH']})
    elif lang=='haskell':
        hashes[str(source)]=digest(source)
        (work/'Candidate.hs').write_text(haskell_strictness(source.read_text()));(work/'Main.hs').write_text(drivers.HASKELL);(work/'clock.c').write_text(drivers.RAW_CLOCK)
        ex.run(['/opt/homebrew/bin/ghc','-O2','-fno-full-laziness','-fno-cse','-i'+str(work),'-outputdir',work/'objects','-o',binary,work/'Main.hs',work/'clock.c'],cwd=work,timeout=300)
    elif lang=='scala':
        hashes[str(source)]=digest(source);shutil.copy2(source,work/'Candidate.scala');(work/'Main.scala').write_text(drivers.scala(source.read_text()))
        classes=work/'classes';classes.mkdir(exist_ok=True)
        r=ex.run([isabelle,'getenv','-b','ISABELLE_SCALAC_OPTIONS']);options=shlex.split(Path(r['stdout']).read_text().strip())
        ex.run([isabelle,'scalac',*options,'-d',classes,work/'Candidate.scala',work/'Main.scala'],timeout=300)
        shell_launcher(binary,[isabelle,'scala','-J-Xss16m','-classpath',classes,'Main'])
    elif lang=='sml':
        hashes[str(source)]=digest(source);shutil.copy2(source,work/'Candidate.ML');(work/'clock.c').write_text(drivers.RAW_CLOCK)
        clock=work/'clock.dylib';ex.run(['cc','-dynamiclib','-O2','-o',clock,work/'clock.c'])
        (work/'Main.ML').write_text(drivers.SML.replace('@CLOCK@',str(clock)))
        r=ex.run([isabelle,'getenv','-b','ML_HOME']);poly=Path(Path(r['stdout']).read_text().strip())/'poly';heap=work/'compiled.heap'
        ex.run([poly,'--error-exit','-q','--eval','use "'+str(work/'Candidate.ML')+'"; use "'+str(work/'Main.ML')+'"; PolyML.SaveState.saveState "'+str(heap)+'";'],timeout=300)
        shell_launcher(binary,[poly,'--error-exit','-q','--eval','val _ = PolyML.SaveState.loadState "'+str(heap)+'"; val _ = Main.main (); val _ = OS.Process.exit OS.Process.success;'])
    elif lang=='go':
        module=source.parents[1];dest=work/'module';dest.mkdir(exist_ok=True)
        for p in module.rglob('*'):
            if p.is_file() and p.name!='main.go' and (p.suffix=='.go' or p.name in ['go.mod','go.sum']):
                hashes[str(p)]=digest(p);target=dest/p.relative_to(module);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        (dest/'main.go').write_text(drivers.go(source.read_text()))
        ex.run([isabelle,'go','build','-o',binary,'.'],cwd=dest,timeout=300)
    else:raise Failure('unknown_backend',lang)
    if not all(digest(p)==h for p,h in hashes.items()):raise Failure('algorithm_changed_during_build',item['id'])
    artifacts={str(p):digest(p) for p in work.rglob('*') if p.is_file() and not any(x in p.relative_to(work).parts for x in ['build-logs','target']) and p.name not in ['build-v2.json']}
    r={**item,'binary':str(binary),'built_at':now(),'source_hashes':hashes,'artifact_hashes':artifacts,'builder_identity':key}
    save(saved,r);return r


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--cases',nargs='+');p.add_argument('--languages',nargs='+');args=p.parse_args()
    STORE.mkdir(parents=True,exist_ok=True);items=inventory();save(STORE/'inventory.json',items);cfg=config()
    for item in items:
        if args.cases and item['case'] not in args.cases:continue
        if args.languages and item['language'] not in args.languages:continue
        print('BUILD '+item['id'],flush=True)
        r=build(item,cfg);print('BUILT '+r['binary'],flush=True)

if __name__=='__main__':main()
