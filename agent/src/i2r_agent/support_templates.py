"""Small source-verified foundational contracts; unknown APIs remain model-owned."""
import re
from .segmented_contract import interfaces
from .task_context import fingerprint
from .v8_support import requirements
POLICY='source-boolean-constructor-and-lazy-if-contracts-v1'

def build(state):
    model=state['bundle']['source_model'];api=interfaces(state['files']);mapping={r['source']:r for r in state['mapping']};tests=[];rows=[];covered=[];proofs=[]
    boolean=model['entities'].get('type:HOL.bool',{})
    constructors={r['id'] for r in boolean.get('constructors',[])}
    for source,value in [('constant:HOL.True','true'),('constant:HOL.False','false')]:
        row=mapping.get(source,{});path=row.get('rust_item','');facts=api.get(path,[])
        if source not in constructors or len(facts)!=1 or facts[0]['kind']!='const_item':continue
        if not re.fullmatch(r'pub\s+const\s+\w+\s*:\s*bool\s*=.*;',facts[0]['signature'],re.S):continue
        name='basic_'+value;tests.append(f'#[test] fn {name}(){{assert_eq!({path.replace("crate::","i2r_candidate::",1)}, {value});}}')
        covered.append(source);proofs.append({'source':source,'basis':'HOL.bool datatype constructor','source_fact':fingerprint(boolean)})
        required=requirements(state,[source]) or [{'source':source,'category':'constructor_value'}]
        rows.extend({**r,'case':value,'expected_basis':source+' is the corresponding HOL.bool constructor','test_name':name} for r in required)
    source='constant:HOL.If';entity=model['entities'].get(source,{});row=mapping.get(source,{});path=row.get('rust_item','');facts=api.get(path,[]);eqs=entity.get('execution_equations') or []
    simple=[]
    for e in eqs:
        args=[x.get('text') for x in e.get('arguments',[])];simple.append((args,e.get('rhs',{}).get('text')))
    exact=len(simple)==2 and any(len(a)==3 and a[0]=='True' and r==a[1] for a,r in simple) and any(len(a)==3 and a[0]=='False' and r==a[2] for a,r in simple)
    if exact and len(facts)==1 and facts[0]['kind']=='macro_definition' and '#[macro_export]' in facts[0].get('attributes',[]) and len(re.findall(r'\$\w+\s*:\s*expr',facts[0]['signature']))==3:
        call=path.replace('crate::','i2r_candidate::',1);name='basic_lazy_if_nonclone'
        tests.append(f'#[test] fn {name}(){{struct Token(u8); let a={call}!(true, Token(7), panic!("unselected false branch")); assert_eq!(a.0,7); let b={call}!(false, panic!("unselected true branch"), Token(9)); assert_eq!(b.0,9);}}')
        covered.append(source);proofs.append({'source':source,'basis':'Exact True/False selection equations','source_fact':fingerprint(eqs)})
        required=requirements(state,[source]) or [{'source':source,'category':'lazy_branch_nonclone'}]
        rows.extend({**r,'case':'both branches; non-Clone/non-Ord payload; unselected panic','expected_basis':'HOL.If True x y = x; HOL.If False x y = y','test_name':name} for r in required)
    proposal={'test_source':'\n'.join(tests),'unit_tests':[],'obligations':rows}
    return {'policy':POLICY,'covered_sources':covered,'proofs':proofs,'proposal':proposal,'identity':fingerprint([POLICY,proofs,proposal,api,state['mapping']])}
