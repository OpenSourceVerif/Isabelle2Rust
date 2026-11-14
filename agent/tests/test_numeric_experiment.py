"""No repeated oracle execution, no overflow samples, no source substitution."""
from copy import deepcopy
from pathlib import Path
import pytest
from i2r_agent import numeric_experiment as experiment, numeric_interface as numeric
from i2r_agent import fpp_artifact as artifact
from i2r_agent.common import Failure, digest
from i2r_agent.segmented_config import rust_config
from test_paired_numerics import paired


def state():
    return {'differential_suites':[{'kind':lane,'status':'passed',
        'reproducer':{'inputs':[[1],[2]],'arguments':args},
        'reference_coverage':{'matrix':[{'input':[x],'expected':[x+1],'available':['ocaml']} for x in [1,2]]}}
        for lane,args in [('ordinary',[]),('kernel',['--i2r-kernel-check'])]]}


def test_cached_observations_are_exact_executed_evidence():
    data=state();observations=experiment.cached_observations(data)
    assert observations[('kernel',(2,))]==[3]
    data['differential_suites'][0]['reference_coverage']['matrix'][0]['available']=[]
    with pytest.raises(Failure):experiment.cached_observations(data)
    data=state();data['differential_suites'][1]['status']='differential_unavailable'
    with pytest.raises(Failure):experiment.cached_observations(data)


def test_checked_failure_is_isolated_and_excluded_never_a_successful_sample(monkeypatch):
    calls=[]
    def execute(binary,inputs,executor,timeout,arguments=()):
        calls.append(inputs)
        return {'status':'numeric_range_exceeded' if len(inputs)>1 or inputs==[[2]] else 'passed',
                'outputs':[[2]] if inputs==[[1]] else None,'record':{}}
    monkeypatch.setattr(experiment,'execute',execute)
    result=experiment.validate_lane('binary',experiment.cached_observations(state()),'kernel','checked',None,1)
    assert result['range_exclusions']==[[2]] and result['compared']==1
    assert calls==[[[1],[2]],[[1]],[[2]]]
    with pytest.raises(Failure):experiment.validate_lane('binary',experiment.cached_observations(state()),'kernel','arbitrary',None,1)


def test_output_mismatch_is_not_an_overflow_exclusion(monkeypatch):
    monkeypatch.setattr(experiment,'execute',lambda *a,**kw:{'status':'passed','outputs':[[999],[3]],'record':{}})
    with pytest.raises(Failure) as error:experiment.validate_lane('b',experiment.cached_observations(state()),'kernel','checked',None,1)
    assert error.value.code=='paired_output_mismatch'


def test_connector_cannot_measure_wire_conversion_or_unpaired_generic_numbers():
    rc=rust_config({},paired())
    examples=[
        'pub type Prepared=Vec<WireInt>;pub type KernelResult=Vec<WireInt>;pub fn benchmark_run(p:Prepared)->KernelResult{p}',
        'pub fn helper(x:Nat)->String{x.to_string()} pub fn benchmark_run(p:Nat)->String{helper(p)}',
        'pub fn benchmark_run(p:Vec<Nat>)->Vec<Nat>{observe(&p)}',
    ]
    for code in examples:
        with pytest.raises(Failure):numeric.validate_connector({'src/lib.rs':code},rc)
    numeric.validate_connector({'src/lib.rs':'pub type Prepared=Vec<i2r_numeric::Nat>;pub type KernelResult=i2r_numeric::Nat;pub fn benchmark_run(p:Prepared)->KernelResult{i2r_candidate::sum(p)}'},rc)


def test_performance_cohort_preserves_ten_entries_and_inputs(monkeypatch):
    monkeypatch.setenv('I2R_DATASET','performance');data=artifact.manifest()
    assert len(data['cases'])==10
    for row in data['cases']:
        for name,sha in row['files'].items():assert digest(artifact.ARTIFACT/row['project']/name)==sha
        assert row['primary_workload'] in {w['id'] for w in row['performance_workloads']}
        for workload in row['performance_workloads']:
            assert workload['input'] in row['inputs']['ordinary_generated']
            assert workload['input'] in row['inputs']['kernel_generated']
    avl=next(r for r in data['cases'] if r['id']=='fpp-avl-updates')
    assert set(avl['roots'])=={'constant:AVL_Set_Code_Test.insert','constant:AVL_Set_Code_Test.delete'}


def test_process_interval_has_expected_orientation():
    assert experiment.interval({'process_medians_ns':[20]*5},{'process_medians_ns':[10]*5})==[2.0,2.0]
