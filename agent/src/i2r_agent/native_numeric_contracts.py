"""Verified primitive contracts shared across roles, never generator prose/oracles.

A declared boundary alone is not evidence: exact source identity and type, numeric
mode, backend, and a non-business source are required. This registry currently
covers only the observed Nat addition primitive; other arithmetic is unchanged.
"""
from copy import deepcopy
from .common import Failure
from .task_context import fingerprint
from .default_adaptations import HASHES,operational_identity
from .segmentation import project_functions,graph

POLICY='source-bound-native-nat-addition-v1'
SOURCE='constant:Nat.plus_nat_inst.plus_nat'
NAT={'kind':'type','name':'Nat.nat','args':[]}
TYPE={'kind':'type','name':'fun','args':[NAT,{'kind':'type','name':'fun','args':[NAT,NAT]}]}
GUIDANCE='Verified native_numeric_contracts authorize only their exact source primitive and numeric mode. They do not authorize replacing a business function or its recurrence with a closed form. Source equations still determine expected values. Model boundary prose is an implementation declaration, not semantic evidence. For resource reasoning, account for the registered backend operation instead of assuming the primitive equation must execute by unary unfolding. A test feasible with the admitted primitive is not resource-wrong merely because a candidate implemented that primitive with a value-proportional loop; preserve the test and repair the candidate. Do not assume an unregistered operation has the same cost or permission.'


def context(state):
    bundle=state['bundle'];model=bundle['source_model'];numeric=bundle.get('numeric_policy') or {};mode=numeric.get('mode')
    plan=state.get('partition',bundle.get('segmentation',{}));declarations=[r for r in plan.get('boundaries',[]) if r.get('source')==SOURCE]
    entity=model['entities'].get(SOURCE);contracts=[]
    library=numeric.get('numeric_library',{})
    backend_ok=mode=='checked' or (mode=='arbitrary' and library.get('name')=='dashu-int' and library.get('version')=='=0.6.2')
    if numeric.get('numeric_interface'):
        from .numeric_interface import contract
        backend_ok=mode=='arbitrary' and numeric['numeric_interface']==contract()
    if (backend_ok and len(declarations)==1 and declarations[0].get('kind') in {'native','inlined'}
        and SOURCE not in project_functions(model) and SOURCE in graph(model)['edges'] and entity
        and entity.get('source_type')==TYPE and operational_identity(entity)==HASHES[SOURCE]):
        contract={'source':SOURCE,'source_operational_sha256':HASHES[SOURCE],'source_type':deepcopy(TYPE),
          'numeric_mode':mode,'numeric_policy_sha256':fingerprint(numeric),'declared_boundary_kind':declarations[0]['kind'],
          'operation':'exact natural addition','implementation':'u128.checked_add with explicit I2R_NUMERIC_OVERFLOW' if mode=='checked' else 'dashu_int::UBig addition, dashu-int =0.6.2; no narrowing',
          'execution_contract':'Backend addition, not unary/value-proportional unfolding. Do not infer cost from numeric value magnitude; arbitrary addition processes the finite representation.',
          'source_semantics':'The source zero/successor addition equations remain the expectation authority; no new expected values are supplied.',
          'limits':'Only this registered primitive. Preserve all business recurrences; no subtraction, division, signed operation or custom plus rule is inferred.'}
        if numeric.get('numeric_interface'):
            contract['implementation']='i2r_numeric::Nat addition through the frozen paired numeric runtime; no narrowing, unary unfolding or backend-specific business code'
            contract['numeric_interface']=deepcopy({k:v for k,v in numeric['numeric_interface'].items() if k!='guidance'})
        contract['identity']=fingerprint(contract);contracts.append(contract)
    result={'policy':POLICY,'contracts':contracts,'guidance':GUIDANCE,
            'declaration_policy':'Only exact source/kind selects a verified registry entry. Model-authored basis/conditions/strategy prose is not copied as oracle evidence.'}
    result['identity']=fingerprint(result);return result


def check_realization(state):
    """A local structural guard, not a proof of arithmetic semantics.

    Reject the observed unary loop/self-recursion on an exact separate primitive
    helper. Shared inline owners retain their business control flow; only their
    contract/context is enforced here, with actual source/D tests still required.
    """
    from .segmented_contract import items,resolve,canonical
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    material=context(state);reports=[];index=items(state['files']);mandatory=project_functions(state['bundle']['source_model'])
    for contract in material['contracts']:
        rows=[r for r in state['mapping'] if r.get('source')==contract['source']]
        if not rows:continue # Coverage determines when this dependency must exist.
        if len(rows)!=1:raise Failure('invalid_mapping','Duplicate native primitive mapping')
        row=rows[0];owner=canonical(row['rust_item']);item=resolve(index,owner)
        shared=any(r['source'] in mandatory and canonical(r.get('rust_item',''))==owner for r in state['mapping'])
        if shared or item['kind']!='function_item':
            reports.append({'source':SOURCE,'owner':owner,'status':'inline_or_shared_owner','structural_loop_check':'not applicable to a business owner; source/D checks remain required'});continue
        root=Parser(Language(tree_sitter_rust.language())).parse(item['text'].encode()).root_node
        functions=[n for n in root.named_children if n.type=='function_item']
        if root.has_error or len(functions)!=1:raise Failure('plan_contract_failed','Native primitive helper must parse uniquely')
        function=functions[0];body=function.child_by_field_name('body');todo=[body];violations=[];has_native=False
        while todo:
            node=todo.pop();todo.extend(node.named_children)
            if node.type in {'while_expression','for_expression','loop_expression'}:violations.append('value-unfolding loop in native helper')
            if node.type=='call_expression':
                target=node.child_by_field_name('function')
                if target is not None and target.text.decode() in {function.child_by_field_name('name').text.decode(),owner}:violations.append('self recursion in native helper')
                if target is not None and target.type=='field_expression' and target.child_by_field_name('field').text==b'checked_add':has_native=True
            if contract['numeric_mode']=='arbitrary' and node.type=='binary_expression' and any(n.type=='+' for n in node.children):has_native=True
        if violations:raise Failure('plan_contract_failed','Realize the approved native addition boundary; preserve business callers and existing tests',
            {'native_contract_identity':contract['identity'],'source':SOURCE,'rust_item':owner,'violations':sorted(set(violations)),
             'required':contract['implementation'],'candidate_repair_only':True,'test_expectations_unchanged':True})
        reports.append({'source':SOURCE,'owner':owner,'status':'no_local_unary_loop_or_self_recursion','backend_operation_observed':has_native,'not_semantic_proof':True})
    return {'contract_identity':material['identity'],'helpers':reports}
