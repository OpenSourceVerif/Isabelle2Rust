from __future__ import annotations

import re
import os
import shutil
import tomllib
from pathlib import Path

from .common import ROOT, Failure, digest, save, read
from .preprocessing import build_project
from . import tool_sources


def cargo(cfg, *args):
    return [cfg["tools"]["cargo"], "+"+cfg["tools"]["rust_toolchain"], *map(str,args)]


def rust_driver(module, reference=False, borrowed=False, transport='dashu-ubig',kernel=False,kernel_modules=None,timing=True):
    numeric={'dashu-ubig':'dashu_int::UBig','dashu-ibig':'dashu_int::IBig','bigint':'num_bigint::BigInt'}[transport]
    setup=f'use {numeric} as WireInt;\n'
    if reference:
        setup+=f'use isabelle_exported::{module}::{{observe,List}};\nuse num_bigint::BigInt;\n'
        convert='let input=values.iter().rev().fold(List::Nil, |tail,x|List::Cons(x.to_string().parse::<BigInt>().unwrap(),Box::new(tail)));'
        normal='observe('+('&' if borrowed else '')+'input)'
        encode='let mut words=Vec::new(); let mut rest=output; while let List::Cons(x,tail)=rest { words.push(x.to_string()); rest=*tail; }'
        calls={}
        if kernel:
            for name,(namespace,by_ref) in kernel_modules.items():
                setup+=f'use isabelle_exported::{namespace}::{name};\n'
                argument={'kernel_prepare':'input','kernel_run':'prepared','kernel_encode':'result'}[name]
                calls[name]=name+'('+('&' if by_ref else '')+argument+')'
    else:
        setup+='use i2r_candidate::observe;\n'
        convert='';normal='observe(&values)'
        encode='let words=output.iter().map(ToString::to_string).collect::<Vec<_>>();'
        if kernel:
            setup+='use i2r_candidate::{benchmark_prepare,benchmark_run,benchmark_encode};\n'
            calls={'kernel_prepare':'benchmark_prepare(&values)','kernel_run':'benchmark_run(prepared)','kernel_encode':'benchmark_encode(result)'}
    if kernel:
        timed='if measuring {\n    let prepared = std::hint::black_box(PREPARE);\n    let started = std::time::Instant::now();\n    let result = std::hint::black_box(RUN);\n    let elapsed = started.elapsed().as_nanos();\n    eprintln!("I2R_KERNEL_NS {}",elapsed);\n    ENCODE\n} else '.replace('PREPARE',calls['kernel_prepare']).replace('RUN',calls['kernel_run']).replace('ENCODE',calls['kernel_encode']).replace('NORMAL',normal)
        behavior='if kernel_check { let prepared=PREPARE; let result=RUN; ENCODE } else { NORMAL };'.replace('PREPARE',calls['kernel_prepare']).replace('RUN',calls['kernel_run']).replace('ENCODE',calls['kernel_encode']).replace('NORMAL',normal)
        invoke='let output = '+(timed if timing else '')+behavior
    else:invoke='let output='+normal+';'
    source=(setup+'use std::io::{self, BufRead};\nfn main() {\n    let measuring=TIMING_ENABLED && std::env::args().any(|x|x=="--i2r-benchmark");\n    let kernel_check=std::env::args().any(|x|x=="--i2r-kernel-check");\n    for line in io::stdin().lock().lines() {\n        let line=line.expect("input read failed");\n        let values:Vec<WireInt>=line.split_whitespace().map(|s|s.parse().expect("invalid integer")).collect();\n'+convert+invoke+encode+'\n        println!("{}",words.join(" "));\n    }\n}\n').replace('TIMING_ENABLED','true' if timing else 'false')
    if not timing:source='\n'.join(line for line in source.splitlines() if 'let measuring=' not in line)+'\n'
    return source


def compile_rust(crate, cfg, executor, candidate=False):
    crate=Path(crate)
    from .storage import cargo_cache
    package=tomllib.loads((crate/'Cargo.toml').read_text())['package']['name']
    binary=crate/'target/release'/package
    with cargo_cache(executor,cfg) as target:
        # Exported crates share a package name and may retain copied timestamps.
        # Cargo can then reuse the preceding crate's library while rebuilding
        # only main.rs. Rebuild this package; keep third-party dependencies.
        clean=executor.run(cargo(cfg,'clean','--release','--package',package,
            '--manifest-path',crate/'Cargo.toml','--target-dir',target),
            timeout=cfg['budgets']['build_seconds'])
        build=executor.run(cargo(cfg,'build','--release','--manifest-path',crate/'Cargo.toml','--target-dir',target),
                           timeout=cfg['budgets']['build_seconds'],check=False)
        checks={'package_cache_reset':clean,'build':build}
        if candidate and build['status']=='passed' and cfg['testing'].get('clippy') not in {None,'off'}:
            checks['clippy']=executor.run(cargo(cfg,'clippy','--locked','--all-targets','--manifest-path',crate/'Cargo.toml',
                '--target-dir',target,'--', '-D' if cfg['testing'].get('clippy')=='deny_warnings' else '-W','warnings'), timeout=cfg['budgets']['build_seconds'],check=False)
        status='passed' if all(x['status']=='passed' for x in checks.values()) else 'compile_failed'
        if build['status']=='passed':
            binary.parent.mkdir(parents=True,exist_ok=True)
            # Retain each attempt's executable independently of the reusable cache.
            temporary=binary.with_suffix('.copy-tmp')
            shutil.copy2(target/'release'/package,temporary)
            temporary.replace(binary)
    return {'status':status,'checks':checks,'binary':str(binary),'build_cache':str(target)}


def prepare_references(project,cfg,work,executor):
    work=Path(work)
    export=build_project(project,cfg,work/'isabelle',executor,reference=True)
    crates=list(export.rglob('Cargo.toml')); ocamls=list(export.rglob('*.ocaml'))
    if len(crates)!=1 or len(ocamls)!=1:
        raise Failure('unsupported_reference_layout','Study observation binding currently requires one export statement')
    stage1=work/'stage1'; shutil.copytree(crates[0].parent,stage1)
    manifest=stage1/'Cargo.toml'
    original_manifest=manifest.read_text()
    pinned=re.sub(r'(num-bigint\s*=\s*)"[^"]+"',r'\1"=0.4.6"',original_manifest)
    pinned=re.sub(r'(num-traits\s*=\s*)"[^"]+"',r'\1"=0.2.19"',pinned)
    pinned=pinned.replace('[dependencies]','[dependencies]\ndashu-int = { version = "=0.6.2", default-features = false, features = ["std"] }',1)
    manifest.write_text(pinned)
    save(work/'reference-dependency-pinning.json',{'original':original_manifest,'pinned':pinned,
        'reason':'Pin reference numeric libraries and UBig test transport; candidate internals are independent'})
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
    optimizer_target=Path(cfg['tools'].get('optimizer_target',ROOT/'cache/optimizer-target'))
    optimizer=optimizer_target/'debug/cargo-opt'
    # Cargo checks source and path-dependency changes even if the binary exists.
    executor.run(cargo(cfg,'build','--locked','--manifest-path',tool_sources.repository('Isabelle2Rust')/'optimize/Cargo.toml',
        '--target-dir',optimizer_target),timeout=cfg['budgets']['build_seconds'])
    executor.run([optimizer,stage1,'--out-dir',stage2])
    timing=not cfg.get('v8',{}).get('correctness_only')
    result={}
    for label,crate in [('stage1',stage1),('stage2',stage2)]:
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
        (crate/'src/main.rs').write_text(rust_driver(candidates[0].stem,True,':' in signature and '&' in signature.split(':',1)[1],kernel=True,kernel_modules=kernel_modules,timing=timing))
        check=compile_rust(crate,cfg,executor)
        result[label]={**check,'crate':str(crate),'source':str(candidates[0]),'sha256':digest(candidates[0]),'kernel_modules':kernel_modules,'timing_protocol':'kernel-v1','kernel_behavior_argument':'--i2r-kernel-check','timing_enabled':timing}
        if check['status']!='passed':raise Failure('reference_compile_failed',label,check)
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
    result['ocaml']={'status':'passed','checks':{'build':check},'binary':str(binary),'source':str(source),'sha256':digest(source),'timing_protocol':'kernel-v1','kernel_behavior_argument':'--i2r-kernel-check','timing_enabled':timing}
    save(work/'references.json',result)
    return result


def ocaml_driver(module,timing=True):
    source=f'''external timer_start : unit -> unit = "i2r_timer_start"
external timer_stop : unit -> int64 = "i2r_timer_stop"
let () =
  let measuring = TIMING_ENABLED && Array.exists ((=) "--i2r-benchmark") Sys.argv in
  let kernel_check = Array.exists ((=) "--i2r-kernel-check") Sys.argv in
  try while true do
    let line = read_line () in
    let words = List.filter (fun s -> s <> "") (String.split_on_char ' ' line) in
    let input = List.map (fun s -> Reference.{module}.nat_of_integer (Z.of_string s)) words in
    let result = if measuring then (
      let prepared = Sys.opaque_identity (Reference.{module}.kernel_prepare input) in
      timer_start ();
      let result = Sys.opaque_identity (Reference.{module}.kernel_run prepared) in
      let elapsed = timer_stop () in
      Printf.eprintf "I2R_KERNEL_NS %Ld\\n%!" elapsed;
      Reference.{module}.kernel_encode result
    ) else if kernel_check then Reference.{module}.kernel_encode (Reference.{module}.kernel_run (Reference.{module}.kernel_prepare input))
      else Reference.{module}.observe input in
    print_endline (String.concat " " (List.map (fun n -> Z.to_string (Reference.{module}.integer_of_nat n)) result))
  done with End_of_file -> ()
'''
    source=source.replace('TIMING_ENABLED','true' if timing else 'false')
    if not timing:
        start=source.index('    let result = if measuring then (')
        end=source.index(' else if kernel_check then',start)
        source=source[:start]+'    let result = if kernel_check then'+source[end+len(' else if kernel_check then'):]
        source='\n'.join(line for line in source.splitlines() if not line.startswith('external timer_') and 'let measuring =' not in line)+'\n'
    return source
