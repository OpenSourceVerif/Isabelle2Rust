"""Same business bytes, feature-only builds, legacy no-op and numeric contracts."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import pytest
from i2r_agent import experiment_config as experiment, numeric_interface as numeric
from i2r_agent.common import ROOT, Failure, Executor, read, save
from i2r_agent.segmented_config import rust_config, cargo_text, materialize, cargo_command
from i2r_agent.source_input import numeric_contract
from i2r_agent.translation_workflow import connection, compile_crate


def config():
    return read(ROOT.parent/'artifact/config.json')


def paired():
    return experiment.apply_selection(config(), {'numeric':'paired','optimization':'off'})


def test_off_is_exact_config_and_prompt_noop(tmp_path):
    cfg=config(); before=deepcopy(cfg)
    parser=argparse.ArgumentParser();experiment.arguments(parser)
    for args in [[],['--off']]:
        assert experiment.initialize(tmp_path,parser.parse_args(args)) is None
        assert not (tmp_path/'experiment.json').exists()
        assert experiment.apply(cfg,tmp_path) is cfg
        assert cfg==before
    for path in (ROOT/'prompts').glob('*.txt'):
        text=path.read_text();assert numeric.prompt(text,cfg)==text
    assert 'numeric_interface' not in numeric_contract(cfg)
    assert 'numeric_interface' not in rust_config({},cfg)
    assert 'i2r-numeric' not in cargo_text(rust_config({},cfg))


def test_switch_groups_are_independent_and_persistent(tmp_path):
    parser=argparse.ArgumentParser();experiment.arguments(parser)
    args=parser.parse_args(['--paired-numerics','--off'])
    value=experiment.initialize(tmp_path,args)
    assert value=={'schema':1,'numeric':'paired','optimization':'off'}
    assert experiment.initialize(tmp_path,parser.parse_args([]))==value
    assert numeric.enabled(experiment.apply(config(),tmp_path))
    with pytest.raises(Failure,match='frozen'):
        experiment.initialize(tmp_path,parser.parse_args(['--checked']))
    with pytest.raises(SystemExit):parser.parse_args(['--arbitrary','--checked'])
    with pytest.raises(SystemExit):parser.parse_args(['--off','--full'])


def test_cannot_reconfigure_original_run(tmp_path):
    save(tmp_path/'release.json',{})
    parser=argparse.ArgumentParser();experiment.arguments(parser)
    with pytest.raises(Failure):experiment.initialize(tmp_path,parser.parse_args(['--paired-numerics']))
    assert not (tmp_path/'experiment.json').exists()


def test_policy_and_cargo_have_one_immutable_interface():
    cfg=paired();policy=numeric_contract(cfg);rc=rust_config({},cfg)
    assert policy['mode']=='arbitrary'
    assert policy['numeric_library']['nat']=='i2r_numeric::Nat'
    assert policy['numeric_interface']['copy'] is False
    assert rust_config(rc,cfg)==rc
    other=numeric.backend_config(rc,'checked')
    assert {k:v for k,v in rc.items() if k!='enabled_features'}=={k:v for k,v in other.items() if k!='enabled_features'}
    assert cargo_text(rc)==cargo_text(other)
    bad=deepcopy(rc);bad['numeric_interface']['runtime_sha256']='tampered'
    with pytest.raises(Failure):numeric.managed_runtime(bad)
    with pytest.raises(Failure):rust_config({'dependencies':{'dashu-int':'=0.6.2'}},cfg)
    assert 'Checked uses u128/i128' not in numeric.prompt((ROOT/'prompts/translation-correctness-analysis.txt').read_text(),cfg)


def test_reject_backend_specific_candidate_without_rewriting():
    rc=rust_config({},paired())
    for code in ['use dashu_int::UBig;','#[cfg(feature="i2r-checked")] pub fn f(){}','pub fn f(){if cfg!(feature="i2r-checked") {}}']:
        files={'src/lib.rs':code};before=deepcopy(files)
        with pytest.raises(Failure):numeric.validate_candidate(files,rc)
        assert files==before
    numeric.validate_candidate({'src/lib.rs':'// dashu_int::UBig is only a comment\npub type Nat=i2r_numeric::Nat;'},rc)


def test_one_business_and_connector_compile_both_backends(tmp_path):
    cfg=paired();cfg['testing']['transport']='dashu-ubig';rc=rust_config({},cfg)
    # Exercise generic containers, borrowed arithmetic, signed payloads and
    # source-clamped native indices in a single unchanged library.
    files={'src/lib.rs':'''use i2r_numeric::{Nat,Int};
pub fn map<T,U,F:Fn(T)->U>(xs:Vec<T>,f:F)->Vec<U>{xs.into_iter().map(f).collect()}
pub fn sum(xs:Vec<Nat>)->Nat{xs.into_iter().fold(Nat::zero(),|a,b|a+b)}
pub fn prefix<T>(xs:Vec<T>,n:&Nat)->Vec<T>{let k=n.clamped_len(xs.len());xs.into_iter().take(k).collect()}
pub fn signed(x:Int)->Int{&x/&Int::from(-3)}
'''}
    connector={'src/lib.rs':'''use i2r_numeric::Nat;
pub type WireInt=dashu_int::UBig;
pub type Prepared=Vec<Nat>; pub type KernelResult=Nat;
pub fn benchmark_prepare(xs:&[WireInt])->Prepared{xs.iter().map(|x|x.to_string().parse().unwrap()).collect()}
pub fn benchmark_run(xs:Prepared)->KernelResult{i2r_candidate::sum(xs)}
pub fn benchmark_encode(x:KernelResult)->Vec<WireInt>{vec![x.to_string().parse().unwrap()]}
pub fn observe(xs:&[WireInt])->Vec<WireInt>{benchmark_encode(benchmark_run(benchmark_prepare(xs)))}
'''}
    snapshots=[]
    for backend in ['arbitrary','checked']:
        current=numeric.backend_config(rc,backend);crate=tmp_path/backend
        materialize(crate,files,current)
        harness=connection(crate,connector,current,cfg)
        built=compile_crate(harness,current,cfg,Executor(tmp_path/(backend+'-commands')),False)
        assert built['status']=='passed',built
        completed=subprocess.run([built['binary'],'--i2r-kernel-check'],input='1 2 3\n10 20\n',text=True,capture_output=True,check=True)
        assert completed.stdout=='6\n30\n'
        snapshots.append([(crate/'src/lib.rs').read_bytes(),(harness/'src/lib.rs').read_bytes()])
    assert snapshots[0]==snapshots[1]
    # A checked intermediate overflow fails rather than becoming a measurement.
    completed=subprocess.run([str(tmp_path/'checked/harness/target/release/i2r_harness')],input=f'{2**128-1} 1\n',text=True,capture_output=True)
    assert completed.returncode!=0 and 'I2R_NUMERIC_OVERFLOW' in completed.stderr
    completed=subprocess.run([str(tmp_path/'arbitrary/harness/target/release/i2r_harness')],input=f'{2**128-1} 1\n',text=True,capture_output=True,check=True)
    assert completed.stdout==f'{2**128}\n'
