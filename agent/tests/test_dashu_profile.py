"""The arbitrary profile changes representation, not the locked observations."""
from pathlib import Path
import pytest
from i2r_agent import dataset_artifact as art
from i2r_agent.common import Failure
from i2r_agent.source_input import numeric_contract
from i2r_agent.references import rust_driver
from i2r_agent.suites import input_bits
from test_translation_workflow import cfg


def test_all_fpp_effective_configs_select_unbounded_dashu(tmp_path):
    rows=art.manifest()['cases']
    assert len(rows)==313
    for row in rows:
        c=art.configuration(row,tmp_path)
        assert c['preprocessing']['numeric_mode']=='arbitrary'
        assert c['testing']['reference_numeric_profile']=='dashu'
        assert c['testing']['transport']=='auto' and input_bits(c)==0
        assert c['translation']['correctness_only'] and c['budgets']['max_model_calls']==48
        policy=numeric_contract(c)
        assert policy['numeric_library']=={'name':'dashu-int','version':'=0.6.2','nat':'dashu_int::UBig','int':'dashu_int::IBig','integer':'dashu_int::IBig'}
        assert 'do not substitute num-bigint' in policy['representation_selection']


def test_dashu_contract_is_cache_distinct_and_rejects_checked():
    c=cfg();c['preprocessing']['numeric_mode']='arbitrary'
    before=numeric_contract(c)
    c['preprocessing']['numeric_library']='dashu-int'
    assert numeric_contract(c)!=before
    c['preprocessing']['numeric_mode']='checked'
    with pytest.raises(Failure):numeric_contract(c)


def test_reference_driver_uses_selected_nat_without_narrowing():
    for profile,ty in [('dashu','dashu_int::UBig'),('bigint','num_bigint::BigInt')]:
        text=rust_driver('Candidate',reference=True,reference_numeric=profile,timing=False)
        assert f'use {ty} as ReferenceNat;' in text
        assert 'parse::<ReferenceNat>()' in text and 'u128' not in text
    assert 'num_bigint' not in rust_driver('Candidate',reference=True,reference_numeric='dashu')


@pytest.mark.parametrize("mode",["checked","arbitrary"])
def test_real_analysis_and_generation_payloads_share_numeric_contract(tmp_path,mode):
    from unittest.mock import Mock,patch
    from i2r_agent import segmented_context as context,translation_workflow as generation
    from i2r_agent.common import Executor,save
    from test_segmented_workflow import source
    c=cfg();c['preprocessing']['numeric_mode']=mode
    if mode=='arbitrary':c['preprocessing']['numeric_library']='dashu-int'
    c['testing'].update(transport='dashu-ubig' if mode=='arbitrary' else 'native-u128',max_input_bits='auto')
    b=source();b.update(workflow='source-translation',numeric_policy=numeric_contract(c))
    class Boundary(BaseException):pass
    seen=[]
    def stop(*args,**kwargs):
        seen.append(args[3]);raise Boundary()
    provider=Mock();provider.calls=0;provider.usage={}
    with patch.object(context,'ask',side_effect=stop),pytest.raises(Boundary):
        context.analyze(b,c,provider,tmp_path/'analysis')
    assert seen[-1]['numeric_policy']==numeric_contract(c)
    save(tmp_path/'regressions.json',[])
    with patch.object(generation,'ask',side_effect=stop),pytest.raises(Boundary):
        generation.search(b,None,c,provider,tmp_path/'generation',Executor(tmp_path/'commands'),{},[],[],tmp_path/'regressions.json',lambda _:None)
    assert seen[-1]['program']['numeric_policy']==numeric_contract(c)
    provider.call.assert_not_called()
    from i2r_agent.common import read
    from i2r_agent import segmented_support as support,source_suite_review as checker,test_connector
    from test_segmented_workflow import mapping
    state=read(tmp_path/'generation/segmented-checkpoint.json')
    state['phase']='repair'
    assert generation.payload(state,c,tmp_path/'repair')[0]['program']['numeric_policy']==numeric_contract(c)
    state['files']={'src/lib.rs':'pub fn h()->u128 {1} pub fn f()->u128 {2}'}
    state['mapping']=[mapping('h'),mapping('f')]
    def author_stop(payload,*args,**kwargs):
        seen.append(payload);raise Boundary()
    with patch.object(support,'source_review',side_effect=author_stop),pytest.raises(Boundary):
        support.prepare(state,c,provider,tmp_path/'author')
    assert seen[-1]['numeric_policy']==numeric_contract(c)
    frozen={'tests':['#[test] fn source_value(){assert_eq!(i2r_candidate::f(),2);}'],'unit_tests':[],
        'obligations':[{'source':'constant:A.f','test_name':'source_value'}]}
    assert checker.payload(frozen,state,c)['numeric_policy']==numeric_contract(c)
    project=tmp_path/'testing';project.mkdir()
    (project/'Model.thy').write_text('source fixture');(project/'Kernel.thy').write_text('source fixture')
    c['testing']['connector_templates']=False
    def connector_stop(system,text,**kwargs):
        import json
        seen.append(json.loads(text));raise Boundary()
    with patch.object(provider,'call',side_effect=connector_stop),pytest.raises(Boundary):
        test_connector.connect(project,tmp_path,state['files'],state['mapping'],{},c,provider,tmp_path/'connector')
    assert seen[-1]['numeric_policy']==numeric_contract(c)
    policy=numeric_contract(c)
    if mode=='checked':
        assert 'u128' in policy['representation_selection'] and 'explicit checked error' in policy['overflow']
    else:
        assert policy['numeric_library']['version']=='=0.6.2' and 'no u128/i128 overflow boundary' in policy['overflow']
