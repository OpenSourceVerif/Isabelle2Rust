"""Use kernel-v2 for future benchmark calls without changing algorithm libraries."""
from pathlib import Path
import fcntl
from .common import ROOT,read,save,Failure,digest
from .baselines import fingerprint
from .kernel_build import build
from .kernel_timing import DEFAULTS,measure_group


def descriptor(name,binary,directory):
    binary=Path(binary).resolve();parent=binary.parent
    item={'id':name,'case':'benchmark','kind':'baseline','source_record':str(binary),
          'work':str(Path(directory)/'builds'/name),'numeric_profile':'shared','round_id':'baseline','baseline_id':None,'reference':None}
    # Read registry metadata for the stable copied OCaml/Rust executables.
    for ancestor in binary.parents:
        record=ancestor/'baseline.json'
        if not record.exists():continue
        b=read(record)
        for lang,ref in b['references'].items():
            if Path(ref['binary']).resolve()==binary:
                if digest(binary)!=ref['binary_sha256'] or digest(ref['source'])!=ref['sha256']:raise Failure('reference_changed',str(binary))
                return {**item,'language':lang,'source':ref['source'],'reference':ref,'source_record':str(record),'baseline_id':b['id'],'case':b['case']}
    # Newly generated Rust executables have their Cargo manifest above target/.
    for ancestor in binary.parents:
        if (ancestor/'Cargo.toml').exists() and (ancestor/'src/main.rs').exists():
            harness=ancestor.name=='harness'
            return {**item,'language':'rust' if harness else 'rust-crate','kind':'llm',
                    'source':str(ancestor.parent if harness else ancestor)}
    for lang,file in [('ocaml','reference.ml'),('haskell','Candidate.raw.hs'),('scala','Candidate.scala'),('sml','Candidate.ML')]:
        if (parent/file).exists():return {**item,'language':lang,'source':str(parent/file)}
    go=next(parent.glob('isabelle/exported/**/Candidate/exported.go'),None)
    if go:return {**item,'language':'go','source':str(go)}
    raise Failure('kernel_timing_artifacts_missing','Cannot locate original algorithm sources for '+str(binary))


def benchmark(implementations,workload,expected,cfg,executor,directory):
    directory=Path(directory);options={**DEFAULTS,**{k:v for k,v in cfg['performance'].items() if k in DEFAULTS},**cfg['performance'].get('v2',{}),'protocol':'kernel-v2'}
    lockpath=ROOT/'cache/timing-v2.lock';lockpath.parent.mkdir(parents=True,exist_ok=True)
    with lockpath.open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        builds=[build(descriptor(name,binary,directory/'kernel-v2'),cfg) for name,binary in implementations.items()]
        result=measure_group('benchmark',builds,workload,expected,options,directory/'kernel-v2')
    save(directory/'performance.json',result)
    return result
