from i2r_agent.source_failure_check import nonliteral_tokens, protected_expected_pair
import pytest

@pytest.mark.parametrize('literal', ['"second"', '"unsafe; return {}"', 'r#"third"#', "'x'"])
def test_literal_contents_are_data(literal):
    assert not nonliteral_tokens(literal).strip()
    assert protected_expected_pair('"first"', literal, 'fn test() {}', 'integration')

@pytest.mark.parametrize('expression', ['candidate()', 'other_value', 'include!("third")', '{return "third"}', '"third".to_owned()'])
def test_open_oracle_still_rejected(expression):
    assert not protected_expected_pair('"first"', expression, 'fn test() {}', 'integration')
    assert nonliteral_tokens(expression).strip()

from i2r_agent.source_failure_check import revise
from i2r_agent.common import Failure

def fixture():
    frozen={'identity':'fixture','tests':['#[test] fn label() { assert_eq!(candidate(), "first"); }'],'unit_tests':[],'obligations':[]}
    state={'bundle':{'source_model':{'entities':{'constant:Label':{'equation':'label = third'}}}},'files':{}}
    proposal={'action':'test_wrong','derivation':'The source labels this value third.','source_evidence':[{'source':'constant:Label','quote':'label = third'}],'edits':[{'kind':'integration','index':0,'old':'"first"','new':'"third"'}]}
    return frozen,state,proposal

def test_actual_revision_accepts_string_and_preserves_call():
    frozen,state,proposal=fixture()
    revised=revise(frozen,proposal,state)
    assert revised['tests']==['#[test] fn label() { assert_eq!(candidate(), "third"); }']
    assert frozen['tests']==['#[test] fn label() { assert_eq!(candidate(), "first"); }']

@pytest.mark.parametrize('replacement',['third','candidate()','format!("third")'])
def test_actual_revision_rejects_nonliteral_oracle(replacement):
    frozen,state,proposal=fixture();proposal['edits'][0]['new']=replacement
    with pytest.raises(Failure):revise(frozen,proposal,state)
