"""Development-only measured hotspots and paired acceptance on uninstrumented code."""
from copy import deepcopy
from pathlib import Path
import json
import statistics
from .common import Failure, save
from .task_context import fingerprint
from .suites import domain, in_numeric_domain, input_bits, scoped_performance_input
from .validation import reference_outputs, check_suite
from .performance import benchmark
from .segmented_config import materialize
from .segmented_run import compile_crate, connection


def workloads(case,cfg):
    bits=input_bits(cfg)
    rows=[scoped_performance_input(case,cfg['performance'].get('input_bits',128))]
    from . import afp20_suites
    if case in afp20_suites.KINDS:rows+=afp20_suites.additional_workloads(case)
    if case=='karatsuba-sqrt':
        sizes=[32,128] if bits else [32,128,1024,1025,2048,4096]
        rows += [[(1<<n)-1] for n in sizes if not bits or n<=bits]
    elif case=='ackermann':rows += [[2,6],[3,4]]
    elif case in {'list-index','skew-heap','splay-tree'}:
        rows += [[n//2]+list(range(n-1,-1,-1)) for n in [32,256]]
    elif case=='shear-sort':rows += [[n]+list(range(n*n-1,-1,-1)) for n in [4,8]]
    elif case=='transitive-closure':
        rows += [[n,0]+[int(j==(i+1)%n or (i+j)%5==0) for i in range(n) for j in range(n)] for n in [8,24]]
    elif case=='list-interleaving':
        for n in [16,256]:
            for mode in [1,2]:
                xs=list(range(n));ys=[];zs=[]
                for i,x in enumerate(xs):
                    select=(n-i-1)%2==0 if mode==1 else x<=sum(xs[i+1:])
                    (ys if select else zs).append(x)
                rows.append([n,len(ys),mode]+xs+ys+zs)
    unique=[]
    for row in rows:
        if row not in unique and domain(case,row) and in_numeric_domain(row,bits):unique.append(row)
    return unique


RUNTIME=r'''
#[doc(hidden)] pub mod __i2r_v8_profile {
 use std::cell::RefCell;
 use std::collections::BTreeMap;
 use std::time::Instant;
 #[derive(Default)] struct State { active:bool, stack:Vec<u128>, rows:BTreeMap<&'static str,(u64,u128,u128)> }
 thread_local! { static STATE:RefCell<State> = RefCell::new(State::default()); }
 pub struct Guard { key:&'static str, start:Instant, active:bool }
 pub fn enter(key:&'static str)->Guard {
  let active=STATE.with(|s| {let mut s=s.borrow_mut();if s.active {s.stack.push(0);true}else{false}});
  Guard{key,start:Instant::now(),active}
 }
 impl Drop for Guard {fn drop(&mut self){if !self.active{return}let elapsed=self.start.elapsed().as_nanos();
  STATE.with(|s|{let mut s=s.borrow_mut();let children=s.stack.pop().unwrap_or(0);
   if let Some(parent)=s.stack.last_mut(){*parent+=elapsed;}
   let r=s.rows.entry(self.key).or_default();r.0+=1;r.1+=elapsed;r.2+=elapsed.saturating_sub(children);
  });
 }}
 pub fn begin(){STATE.with(|s|{let mut s=s.borrow_mut();s.rows.clear();s.stack.clear();s.active=true;});}
 pub fn end(){STATE.with(|s|{let mut s=s.borrow_mut();s.active=false;
  for (k,(n,total,own)) in &s.rows {eprintln!("I2R_PROFILE\t{}\t{}\t{}\t{}",k,n,total,own);}
 });}
}
'''


def instrument(files):
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()));out=deepcopy(files);catalog=[];skipped=[]
    if any('__i2r_v8_profile' in s for s in files.values()):raise Failure('profile_name_collision','Reserved diagnostic module already exists')
    for name,text in files.items():
        if not name.endswith('.rs'):continue
        data=text.encode();tree=parser.parse(data);insertions=[]
        if tree.root_node.has_error:raise Failure('profile_parse_failed',name)
        stack=[tree.root_node]
        while stack:
            node=stack.pop();stack.extend(reversed(node.named_children))
            if node.type!='function_item':continue
            body=node.child_by_field_name('body');ident=node.child_by_field_name('name')
            if body is None:continue
            key=f'{name}:{node.start_point.row+1}:{data[ident.start_byte:ident.end_byte].decode()}'
            signature=data[node.start_byte:body.start_byte].decode()
            if any(x in signature.split() for x in ['const','async','extern']):
                skipped.append({'location':key,'reason':'const/async/extern function not instrumented'});continue
            insertions.append((body.start_byte+1,('\nlet __i2r_profile_guard = crate::__i2r_v8_profile::enter('+json.dumps(key)+');\n').encode()))
            catalog.append({'location':key,'file':name,'line':node.start_point.row+1,'signature':signature})
        for at,fragment in sorted(insertions,reverse=True):data=data[:at]+fragment+data[at:]
        out[name]=data.decode()
    out['src/lib.rs']+=RUNTIME
    return out,catalog,skipped


def profile(state,cfg,executor,refs,inputs,directory):
    path=Path(directory);path.mkdir(parents=True,exist_ok=True)
    result={'status':'pending','version':fingerprint([state['files'],state['connector'],state['rust_config']]),
            'method':'safe Rust RAII function instrumentation; kernel boundary only',
            'limitations':['Instrumentation distorts short functions and inlining; times are diagnostic, not production speed.',
                          'Exclusive time includes uninstrumented library calls and instrumentation overhead.',
                          'Closures/macros, dependency bodies and other threads are not independently profiled; no allocation counts.'],
            'workloads':[]}
    try:
        files,catalog,skipped=instrument(state['files']);result.update(catalog=catalog,skipped=skipped)
        crate=materialize(path/'candidate',files,state['rust_config'])
        harness=connection(crate,state['connector'],state['rust_config'],cfg)
        main=harness/'src/main.rs';text=main.read_text()
        text=text.replace('let start=std::time::Instant::now();','i2r_candidate::__i2r_v8_profile::begin();\n   let start=std::time::Instant::now();')
        text=text.replace('let elapsed=start.elapsed().as_nanos();','let elapsed=start.elapsed().as_nanos();\n   i2r_candidate::__i2r_v8_profile::end();')
        main.write_text(text)
        built=compile_crate(harness,state['rust_config'],cfg,executor,False);result['compilation']=built
        if built['status']!='passed':raise Failure('profile_compile_failed','Instrumentation could not compile',built)
        for x in inputs:
            checked=check_suite(state['bundle']['case'],[x]*cfg['v8']['profile_repetitions'],built['binary'],refs,executor,cfg['v8']['profile_timeout'],'profile',arguments=('--i2r-benchmark',))
            if checked['status']!='passed':raise Failure('profile_behavior_failed','Instrumented execution failed; production semantics not inferred',checked)
            rows={}
            for line in Path(checked['candidate']['stderr']).read_text().splitlines():
                if not line.startswith('I2R_PROFILE\t'):continue
                _,key,count,total,own=line.split('\t');r=rows.setdefault(key,{'location':key,'calls':0,'inclusive_ns':0,'exclusive_ns':0})
                for field,v in [('calls',count),('inclusive_ns',total),('exclusive_ns',own)]:r[field]+=int(v)
            total=sum(r['exclusive_ns'] for r in rows.values())
            for r in rows.values():r['exclusive_share']=r['exclusive_ns']/total if total else 0
            result['workloads'].append({'input':x,'execution':checked,'hotspots':sorted(rows.values(),key=lambda r:-r['exclusive_ns'])})
        result['status']='measured' if any(w['hotspots'] for w in result['workloads']) else 'no_observable_functions'
    except Failure as error:result.update(status='unavailable',error=error.code,reason=str(error),evidence=error.evidence)
    save(path/'profile.json',result);return result


def snapshot(state,path):
    crate=materialize(Path(path)/'candidate',state['files'],state['rust_config'])
    # benchmark() locates sources from this harness. Copy the executable too,
    # so later candidate writes never mutate the parent measurement identity.
    import shutil
    harness=connection(crate,state['connector'],state['rust_config'],{'testing':{'transport':state['transport']}})
    if state.get('harness'):
        for original,destination in [(Path(state['harness'])/'Cargo.lock',harness/'Cargo.lock'),(Path(state['harness']).parent/'Cargo.lock',crate/'Cargo.lock')]:
            if original.exists():shutil.copy2(original,destination)
    target=harness/'target'
    if state['rust_config']['target']:target/=state['rust_config']['target']
    binary=target/'release/i2r_harness';binary.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(state['binary'],binary)
    from .v8_identity import VERIFIED_STATE_FIELDS
    from .implementation_strategy import current
    return {'implementation_strategy':deepcopy(current(state)), 'harness':str(harness),'verification_state':{k:deepcopy(state[k]) for k in VERIFIED_STATE_FIELDS if k in state},
            'files':deepcopy(state['files']),'mapping':deepcopy(state['mapping']),
            'rust_config':deepcopy(state['rust_config']),'partition':deepcopy(state['partition']),
            'connector':deepcopy(state['connector']),'completed':deepcopy(state['completed']),
            'reviews':deepcopy(state['reviews']),'binary':str(binary),'path':str(path)}


def boundaries(state,cfg,executor,refs,inputs,directory):
    """Separate preparation/encoding overhead from kernel; no function instrumentation."""
    path=Path(directory);crate=materialize(path/'candidate',state['files'],state['rust_config'])
    harness=connection(crate,state['connector'],state['rust_config'],cfg)
    main=harness/'src/main.rs';text=main.read_text()
    text=text.replace('let values:Vec<','let __pipeline=std::time::Instant::now();\n  let values:Vec<')
    text=text.replace('let prepared=std::hint::black_box(benchmark_prepare(&values));','let __prepare=std::time::Instant::now();\n   let prepared=std::hint::black_box(benchmark_prepare(&values));\n   eprintln!("I2R_PREPARE_NS {}",__prepare.elapsed().as_nanos());')
    text=text.replace('benchmark_encode(result)','{let __encode=std::time::Instant::now();let output=benchmark_encode(result);eprintln!("I2R_ENCODE_NS {}",__encode.elapsed().as_nanos());output}')
    text=text.replace('println!("{}",output.iter().map(ToString::to_string).collect::<Vec<_>>().join(" "));','let encoded=output.iter().map(ToString::to_string).collect::<Vec<_>>().join(" ");\n  eprintln!("I2R_PIPELINE_NS {}",__pipeline.elapsed().as_nanos());\n  println!("{}",encoded);')
    main.write_text(text);built=compile_crate(harness,state['rust_config'],cfg,executor,False)
    result={'scope':'Uninstrumented functions; stage timers include timer/logging perturbation. Pipeline covers parse/prepare/run/encode/format, excludes input/output IO. Diagnostic only, not throughput comparison.','build':built,'workloads':[]}
    if built['status']=='passed':
        import re
        for x in inputs:
            checked=check_suite(state['bundle']['case'],[x]*cfg['v8']['profile_repetitions'],built['binary'],refs,executor,cfg['v8']['profile_timeout'],'boundaries',arguments=('--i2r-benchmark',))
            text=Path(checked['candidate']['stderr']).read_text()
            timings={key:[int(n) for n in re.findall('I2R_'+key+'_NS ([0-9]+)',text)] for key in ['PREPARE','KERNEL','ENCODE','PIPELINE']}
            result['workloads'].append({'input':x,'validation':checked,'timings_ns':timings})
    result['status']='measured' if built['status']=='passed' and all(r['validation']['status']=='passed' for r in result['workloads']) else 'unavailable'
    save(path/'boundaries.json',result);return result


def measure(state,cfg,executor,refs,inputs,path,parent=None):
    rows=[]
    for i,x in enumerate(inputs):
        expected=reference_outputs(state['bundle']['case'],[x],refs,executor,cfg['testing']['process_timeout'])['ocaml']['outputs'][0]
        binaries={'candidate':state['binary']}
        if parent:binaries={'parent':parent['binary'],**binaries}
        rows.append(benchmark(binaries,x,expected,cfg,executor,Path(path)/str(i)))
    return rows


def compare(measurements,cfg):
    rows=[]
    for m in measurements:
        a=m['summary']['parent'];b=m['summary']['candidate']
        # Require separation of the observed process-level timing ranges, not a
        # single lucky median. Conservative inconclusive results are rolled back.
        def values(r):return r.get('process_medians_ns') or r.get('samples') or [r['median_ns']]
        av=values(a);bv=values(b)
        speedup=a['median_ns']/b['median_ns']
        rows.append({'speedup':speedup,'clear_gain':speedup>=cfg['v8']['minimum_speedup'] and max(bv)<min(av),
                     'regression':b['median_ns']/a['median_ns']>cfg['v8']['maximum_regression'],
                     'parent_ns':a['median_ns'],'candidate_ns':b['median_ns']})
    return {'accept':any(r['clear_gain'] for r in rows) and not any(r['regression'] for r in rows),
            'workloads':rows,'rule':'At least one gain above threshold with separated observed ranges; no material workload regression.'}
