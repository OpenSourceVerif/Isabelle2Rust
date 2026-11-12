"""Independent reference export/build attempts; Rust stage2 explicitly depends on Rust source."""
import hashlib,json,os,re,shutil
from pathlib import Path
from .common import ROOT,Failure,digest,save,read
from . import tool_sources
from .preprocessing import project_info,isabelle_command
from .references import cargo,compile_rust,rust_driver,ocaml_driver
POLICY='available-per-input-v1'


def export_target(project,cfg,work,executor,target):
    tools=tool_sources.manifest();project=Path(project);work=Path(work);work.mkdir(parents=True,exist_ok=True)
    theories,sessions=project_info(project)
    dashu=cfg.get('testing',{}).get('reference_numeric_profile')=='dashu'
    for p in project.rglob('*'):
        if p.is_file() and p.suffix in {'.thy','.ML'}:
            dest=work/p.relative_to(project);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    for theory in theories:
        p=work/(theory+'.thy');text=p.read_text().replace('"I2R_Agent.Agent_Export"','"Rust.Rust_Dashu_Setup"' if dashu else '"Rust.Rust_BigInt_Setup"')
        pattern=r'(export_code\s+[\s\S]*?\s+in\s+)Rust_Agent(\s+module_name\s+\w+)'
        def replace(m):
            roots=m[1] if target=='Rust' else re.sub(r'\s+in\s+$',' nat_of_integer integer_of_nat in ',m[1])
            return roots+target+m[2]
        text,n=re.subn(pattern,replace,text)
        if not n:raise Failure('invalid_export','Expected original Rust_Agent export command')
        p.write_text(text)
    identity=hashlib.sha256(''.join(p.read_text() for p in sorted(work.rglob('*.thy'))).encode()).hexdigest()[:14]
    session='I2R_Reference_'+identity;quoted=lambda s:'"'+s+'"'
    root=f'session {session} = Rust +\n  options [document=false, skip_proofs=false, timeout=1200]\n'
    if sessions:root+='  sessions\n    '+'\n    '.join(map(quoted,sessions))+'\n'
    root+='  theories\n    '+'\n    '.join(theories)+'\n  export_files (in "exported") [2]\n'+''.join(f'    "{session}.{t}:code/**"\n' for t in theories)
    (work/'ROOT').write_text(root)
    record=executor.run(isabelle_command(cfg,'build','-e','-j','1','-o','threads=2','-o','parallel_proofs=0','-o','document=false','-d',ROOT/'isabelle','-d',tool_sources.repository('Isabelle2Rust'),'-d',cfg['tools']['afp'],'-d',work,session),timeout=cfg['budgets']['build_seconds'])
    tool_sources.verify(tools);save(work/'build.json',{'target':target,'tool_sources':tools,'session':session,'record':record,'source_hashes':{str(p.relative_to(work)):digest(p) for p in work.rglob('*.thy')}})
    return work/'exported'


def setup_rust(crate_source,project,cfg,work,executor):
    crates=[Path(crate_source)/'Cargo.toml']
    stage1=work/'stage1'; shutil.copytree(crates[0].parent,stage1)
    manifest=stage1/'Cargo.toml'
    original_manifest=manifest.read_text()
    pinned=re.sub(r'(num-bigint\s*=\s*)"[^"]+"',r'\1"=0.4.6"',original_manifest)
    pinned=re.sub(r'(num-traits\s*=\s*)"[^"]+"',r'\1"=0.2.19"',pinned)
    if not re.search(r'^dashu-int\s*=',pinned,re.M):pinned=pinned.replace('[dependencies]','[dependencies]\ndashu-int = { version = "=0.6.2", default-features = false, features = ["std"] }',1)
    manifest.write_text(pinned)
    save(work/'reference-dependency-pinning.json',{'original':original_manifest,'pinned':pinned,
        'reason':'Pin reference numeric libraries and UBig test transport; candidate internals are independent'})
    if cfg.get('testing',{}).get('reference_numeric_profile')=='dashu':return stage1
    stage2=work/'stage2'
    # The product's nat -> BigInt printing can erase the concrete dictionary
    # while generic exported operations still require Equal/Ord. This explicit
    # observation-boundary adapter supplies only native numeric comparisons.
    # It is recorded separately and never patched into the original compiler.
    bridges={}
    metadata=read(Path(project)/'case.json') if (Path(project)/'case.json').exists() else {}
    for path in (stage1/'src').glob('*.rs'):
        source=path.read_text(); additions=[]
        if 'pub trait Equal' in source and not re.search(r'impl\s+Equal\s+for\s+BigInt',source):
            additions.append('impl Equal for BigInt { fn equal(a: Self,b: Self)->bool { a==b } }')
        if 'pub trait Ord {' in source and not re.search(r'impl\s+Ord\s+for\s+BigInt',source):
            additions.append('impl Ord for BigInt { fn less_eq(a: Self,b: Self)->bool { a<=b } fn less(a: Self,b: Self)->bool { a<b } }')
        if metadata.get('id')=='list-interleaving':
            # This observation uses nat only. Do not apply saturating nat
            # subtraction to a program with generic int operations.
            methods={'Times':'fn times(a:Self,b:Self)->Self { a*b }',
                'One':'fn one()->Self { BigInt::from(1u8) }',
                'Plus':'fn plus(a:Self,b:Self)->Self { a+b }',
                'Zero':'fn zero()->Self { BigInt::ZERO }',
                'Minus':'fn minus(a:Self,b:Self)->Self { if a<=b { BigInt::ZERO } else { a-b } }',
                'Divide':'fn divide(a:Self,b:Self)->Self { if b==BigInt::ZERO { BigInt::ZERO } else { a/b } }',
                'Modulo':'fn modulo(a:Self,b:Self)->Self { if b==BigInt::ZERO { a } else { a%b } }'}
            for trait,body in methods.items():
                if re.search(r'pub trait '+trait+r'\b',source) and not re.search(r'impl\s+'+trait+r'\s+for\s+BigInt',source):
                    additions.append(f'impl {trait} for BigInt {{ {body} }}')
        if additions:
            bridge='\n'.join(additions)+'\n'
            bridges[path.name]=bridge
            path.write_text(source+'\n// Explicit numeric observation adapter.\n'+bridge)
    save(work/'numeric-observation-adapters.json',bridges)
    return stage1


def compile_rust_reference(label,crate,cfg,executor):
    timing=not cfg.get('translation',{}).get('correctness_only')
    candidates=[p for p in (crate/'src').glob('*.rs') if re.search(r'pub fn observe\s*\(',p.read_text())]
    if len(candidates)!=1:raise Failure('missing_observer','Expected one public observe function')
    code=candidates[0].read_text()
    signature=re.search(r'pub fn observe\s*\(([^)]*)\)',code)[1]
    kernel_modules={}
    for name in ['kernel_prepare','kernel_run','kernel_encode']:
        matches=[p for p in (crate/'src').glob('*.rs') if re.search(r'pub fn '+name+r'\s*[<(]',p.read_text())]
        if len(matches)!=1:raise Failure('missing_kernel_entry',name)
        args=re.search(r'pub fn '+name+r'(?:<[^\n]*?>)?\s*\(([^)]*)\)',matches[0].read_text())
        if not args:raise Failure('missing_kernel_signature',name)
        kernel_modules[name]=(matches[0].stem,':' in args[1] and args[1].split(':',1)[1].strip().startswith('&'))
    (crate/'src/main.rs').write_text(rust_driver(candidates[0].stem,True,':' in signature and '&' in signature.split(':',1)[1],kernel=True,kernel_modules=kernel_modules,timing=timing,reference_numeric=cfg.get('testing',{}).get('reference_numeric_profile','bigint')))
    check=compile_rust(crate,cfg,executor)
    result={**check,'crate':str(crate),'source':str(candidates[0]),'sha256':digest(candidates[0]),'kernel_modules':kernel_modules,'timing_protocol':'kernel-v1','kernel_behavior_argument':'--i2r-kernel-check','timing_enabled':timing}
    return result


def compile_ocaml_reference(source_file,cfg,work,executor):
    timing=not cfg.get('translation',{}).get('correctness_only');ocamls=[source_file]
    directory=work/'ocaml';directory.mkdir()
    source=directory/'reference.ml';shutil.copy2(ocamls[0],source)
    text=source.read_text()
    modules=[name for name,signature in re.findall(r'module\s+(\w+)\s*:\s*sig(.*?)end\s*=',text,re.S)
             if all(re.search(r'\bval\s+'+symbol+r'\s*:',signature) for symbol in ['observe','nat_of_integer','integer_of_nat'])]
    if len(modules)!=1:raise Failure('unsupported_reference_layout','Expected one OCaml module exporting the observation and conversion API')
    module=modules[0]
    main=directory/'main.ml'
    main.write_text(ocaml_driver(module,timing=timing))
    (directory/'kernel_clock.c').write_text('''#include <time.h>
#include <stdint.h>
#include <caml/mlvalues.h>
#include <caml/alloc.h>
static struct timespec started;
CAMLprim value i2r_timer_start(value unit) {
  clock_gettime(CLOCK_MONOTONIC, &started); return Val_unit;
}
CAMLprim value i2r_timer_stop(value unit) {
  struct timespec ended; clock_gettime(CLOCK_MONOTONIC, &ended);
  int64_t ns=(int64_t)(ended.tv_sec-started.tv_sec)*1000000000LL+ended.tv_nsec-started.tv_nsec;
  return caml_copy_int64(ns);
}
''')
    binary=directory/'reference'
    check=executor.run([cfg['tools']['ocamlfind'],'ocamlopt','-package','zarith','-linkpkg','-o',binary,*(['kernel_clock.c'] if timing else []),source.name,main.name],cwd=directory,
        env={'PATH':str(Path(cfg['tools']['ocamlfind']).parent)+os.pathsep+os.environ.get('PATH','')})
    result={'status':'passed','checks':{'build':check},'binary':str(binary),'source':str(source),'sha256':digest(source),'timing_protocol':'kernel-v1','kernel_behavior_argument':'--i2r-kernel-check','timing_enabled':timing}
    return result


def failure(error,phase,dependencies):
    if error.code in {'tool_sources_changed','unreaped_isabelle_writer','isabelle_export_infrastructure_error','isabelle_lock_timeout'}:raise error
    return {'status':'reference_failed','phase':phase,'failure':{'code':error.code,'message':str(error),'evidence':error.evidence},'depends_on':dependencies,'availability_policy':POLICY}


def prepare(project,cfg,work,executor,numeric_proof=None):
    work=Path(work);work.mkdir(parents=True,exist_ok=True);result={};stage1=None
    try:
        exported=export_target(project,cfg,work/'rust-export',executor,'Rust');crates=list(exported.rglob('Cargo.toml'))
        if len(crates)!=1:raise Failure('unsupported_reference_layout','Expected one Rust export crate')
        stage1=setup_rust(crates[0].parent,project,cfg,work,executor)
    except Failure as error:
        result['stage1']=failure(error,'rust_export',[])
        result['stage2']={'status':'blocked_dependency','phase':'rust_export','depends_on':['rust_export','stage1_source','optimizer'],'failure':result['stage1']['failure'],'availability_policy':POLICY}
    if stage1 is not None:
        try:result['stage1']={**compile_rust_reference('stage1',stage1,cfg,executor),'depends_on':['rust_export']}
        except Failure as error:result['stage1']=failure(error,'stage1_compile',['rust_export'])
        before=result['stage1']
        diagnostic=before.get('checks',{}).get('build',{}).get('stderr')
        if before.get('status')=='compile_failed' and diagnostic:
            from . import reference_repairs
            text=Path(diagnostic).read_text()
            if reference_repairs.supports(text):
                save(work/'stage1-before-reference-repair.json',before)
                try:
                    receipt=reference_repairs.apply(stage1,text,numeric_proof or {})
                except ValueError as error:
                    # Fail closed, retain the original compiler evidence and source.
                    before['reference_repair_rejected']=str(error)
                else:
                    save(work/'reference-repair.json',receipt)
                    after=compile_rust_reference('stage1',stage1,cfg,executor)
                    result['stage1']={**after,'depends_on':['rust_export'],
                        'reference_repair':{'before':before,'receipt':receipt}}
        # A failed stage1 compilation does not imply that optimizer parsing/build
        # failed. Stage2 consumes its source, not the stage1 executable.
        try:
            target=Path(cfg['tools'].get('optimizer_target',ROOT/'cache/optimizer-target'));stage2=work/'stage2'
            executor.run(cargo(cfg,'build','--locked','--manifest-path',tool_sources.repository('Isabelle2Rust')/'optimize/Cargo.toml','--target-dir',target),timeout=cfg['budgets']['build_seconds'])
            executor.run([target/'debug/cargo-opt',stage1,'--out-dir',stage2])
            result['stage2']={**compile_rust_reference('stage2',stage2,cfg,executor),'depends_on':['rust_export','stage1_source','optimizer']}
        except Failure as error:result['stage2']=failure(error,'stage2_optimize_or_compile',['rust_export','stage1_source','optimizer'])
    # Independent export: neither Rust serialization, optimization nor compilation
    # can prevent the OCaml tool from being attempted.
    try:
        exported=export_target(project,cfg,work/'ocaml-export',executor,'OCaml');files=list(exported.rglob('*.ocaml'))
        if len(files)!=1:raise Failure('unsupported_reference_layout','Expected one OCaml export')
        result['ocaml']={**compile_ocaml_reference(files[0],cfg,work,executor),'depends_on':['ocaml_export']}
    except Failure as error:result['ocaml']=failure(error,'ocaml_export_or_compile',[])
    for name,row in result.items():
        row['availability_policy']=POLICY
        row.setdefault('phase',name+'_compile')
    save(work/'references.json',result);return result
