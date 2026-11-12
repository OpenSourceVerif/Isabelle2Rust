from pathlib import Path
import pytest
import i2r_agent
from i2r_agent.reference_repairs import apply,numeric_domains
from i2r_agent import available_references as ar

DIAG='error[E0277]: the trait `Candidate::Minus` is not implemented for `num_bigint::BigInt`'
def crate(tmp_path,code):
 p=tmp_path/'src/Candidate.rs';p.parent.mkdir();p.write_text(code);return p

def test_nat_minus_requires_unambiguous_domain_and_leaves_rejection_unchanged(tmp_path):
 p=crate(tmp_path,'pub trait Minus { fn minus(a: Self, b: Self) -> Self; }')
 original=p.read_bytes()
 for domains in [[],['Nat.nat','Int.int']]:
  with pytest.raises(ValueError):apply(tmp_path,DIAG,{'domains':domains})
  assert p.read_bytes()==original
 apply(tmp_path,DIAG,{'domains':['Nat.nat']})
 assert 'if a <= b { BigInt::ZERO } else { a - b }' in p.read_text()

def test_int_minus_remains_signed(tmp_path):
 p=crate(tmp_path,'pub trait Minus { fn minus(a: Self, b: Self) -> Self; }')
 apply(tmp_path,DIAG,{'domains':['Int.int']})
 assert 'a - b' in p.read_text() and 'if a <=' not in p.read_text()

def test_exact_comparison_stub_only_and_existing_method_retained(tmp_path):
 p=crate(tmp_path,'''pub trait Plus { fn plus(a: Self,b: Self)->Self; }
 pub trait Ord { fn less(a: Self,b: Self)->bool; fn less_eq(a: Self,b: Self)->bool; }
 impl Ord for BigInt { fn less(a: Self,b: Self)->bool { a < b }
 fn less_eq(a: Self,b: Self)->bool { panic!("unimplemented instance method: less_eq") } }''')
 apply(tmp_path,DIAG.replace('Minus','Plus'),{})
 assert 'fn less(a: Self,b: Self)->bool { a < b }' in p.read_text()
 assert 'a <= b' in p.read_text() and 'panic!' not in p.read_text()

def test_addition_parenthesizes_only_if_operand(tmp_path):
 p=crate(tmp_path,'fn a(x: bool)->i32 { if x {1} else {2} + 1 }\nfn b(x:bool)->i32 { if x {1} else {2} }')
 apply(tmp_path,'expected expression, found `+`',{})
 assert '(if x {1} else {2}) + 1' in p.read_text()
 assert 'fn b(x:bool)->i32 { if x {1} else {2} }' in p.read_text()

def test_compile_success_never_invokes_repair(tmp_path,monkeypatch):
 from unittest.mock import Mock
 export=tmp_path/'export';export.mkdir();(export/'Cargo.toml').write_text('');(export/'x.ocaml').write_text('')
 monkeypatch.setattr(ar,'export_target',lambda *a:export)
 monkeypatch.setattr(ar,'setup_rust',lambda *a:tmp_path/'stage1')
 monkeypatch.setattr(ar,'compile_rust_reference',lambda *a:{'status':'passed'})
 monkeypatch.setattr(ar,'compile_ocaml_reference',lambda *a:{'status':'passed'})
 monkeypatch.setattr(ar.tool_sources,'repository',lambda *a:tmp_path)
 monkeypatch.setattr(ar,'cargo',lambda *a:['cargo'])
 repair=Mock(side_effect=AssertionError('must not repair successful build'));monkeypatch.setattr(i2r_agent.reference_repairs,'apply',repair)
 result=ar.prepare(tmp_path,{'tools':{},'budgets':{'build_seconds':30}},tmp_path/'prepare',Mock())
 assert result['stage1']['status']=='passed';repair.assert_not_called()

def test_actual_type_unification_requires_matching_wrapper_root():
 variable={'kind':'free','name':'a'};nat={'kind':'type','name':'Nat.nat','args':[]}
 source={'entries':['constant:T.f'],'entities':{'constant:T.f':{'source_type':variable}}}
 wrapper={'entities':{'constant:Model.observe':{'instance_resolutions':[{'constant':'T.f','type':nat}]}}}
 assert numeric_domains(source,wrapper)['domains']==['Nat.nat']
 wrapper['entities']['constant:Model.observe']['instance_resolutions'][0]['constant']='Other.f'
 assert numeric_domains(source,wrapper)['domains']==[]

def test_failed_build_repairs_once_and_retains_original_evidence(tmp_path,monkeypatch):
 from unittest.mock import Mock
 export=tmp_path/'export';export.mkdir();(export/'Cargo.toml').write_text('');(export/'x.ocaml').write_text('')
 source=tmp_path/'stage1';source.mkdir();crate(source,'pub trait Zero { fn zero()->Self; }')
 stderr=tmp_path/'compiler.stderr';stderr.write_text(DIAG.replace('Minus','Zero'))
 before={'status':'compile_failed','checks':{'build':{'stderr':str(stderr)}}}
 compile=Mock(side_effect=[before,{'status':'passed'},{'status':'passed'}])
 monkeypatch.setattr(ar,'export_target',lambda *a:export);monkeypatch.setattr(ar,'setup_rust',lambda *a:source)
 monkeypatch.setattr(ar,'compile_rust_reference',compile);monkeypatch.setattr(ar,'compile_ocaml_reference',lambda *a:{'status':'passed'})
 monkeypatch.setattr(ar.tool_sources,'repository',lambda *a:tmp_path);monkeypatch.setattr(ar,'cargo',lambda *a:['cargo'])
 result=ar.prepare(tmp_path,{'tools':{},'budgets':{'build_seconds':30}},tmp_path/'prepare',Mock())
 assert compile.call_count==3 and result['stage1']['status']=='passed'
 assert result['stage1']['reference_repair']['before']=={**before,'depends_on':['rust_export']}
 assert (tmp_path/'prepare/stage1-before-reference-repair.json').exists()
 assert (tmp_path/'prepare/reference-repair.json').exists()
