"""Independently adjudicate test bindings; algorithm repairs cannot rewrite oracles."""
from copy import deepcopy
from pathlib import Path
import re
from tree_sitter import Language, Parser
import tree_sitter_rust
from .common import Failure, save
from .segmented_context import pages
from .segmented_contract import interfaces
from .segmented_support import source_review, insert_tests
from .task_context import fingerprint

AUDIT_SYSTEM='Independently audit source-contract test failures. The source equations and frozen expectations are authoritative. Candidate bodies are withheld. Follow the JSON action schema in task. Never change source cases, expected values, generic strength or algorithm code to obtain a passing result. For paged source reads return request_pages with source-based notes before final adjudication.'


AUDIT_SYSTEM+=''' Distinguish the exact assertion invocation from setup statements in the same test: a let initializer before an assertion is not part of that assertion. Read the supplied test code and source types before claiming a type argument is frozen assertion text. A narrow source-backed binding_fix may correct only the explicit generic type_arguments of a nullary source datatype constructor call in setup, outside every assertion invocation, when all of these facts are supplied and established: the source datatype identifies that constructor with no fields; the actual mapped Rust constructor has no value arguments and returns that datatype at its type parameter; existing parent-constructor payload and/or root type annotations uniquely require the same type substitution in the recursive children; and the correction preserves the source nullary value and all existing generic-test strength. Explain the source constructor, shared type variable and unique surrounding constraint. Retain the callee, value arguments, parent/root types, all literals, every assertion byte, obligations and non-Clone/non-Ord test types; change only the proven setup type_arguments. If generic type_arguments would occur inside an assertion, the existing assertion-preservation rule still applies. This permission does not apply to default<T>, Default::default, arbitrary functions or helpers, constructors with payload fields, ambiguous type constraints, or changes to runtime data, trait bounds or candidate code. Do not add a special overload, alias or adapter that changes the datatype's homogeneous recursive-child semantics. If these source/type facts are absent or do not uniquely establish the correction, do not guess or propose this repair; retain the existing adjudication paths. A proven setup-instantiation mismatch with source-faithful candidate signatures is a binding defect, not evidence that the algorithm must change. Existing mechanical test protections and subsequent full compilation/execution remain mandatory.'''


def invariants(code):
    data=code.encode();tree=Parser(Language(tree_sitter_rust.language())).parse(data)
    assertions=[];literals=[];stack=[tree.root_node]
    while stack:
        node=stack.pop();text=data[node.start_byte:node.end_byte].decode()
        if node.type=='macro_invocation' and re.match(r'(?:\w+::)*(?:assert|assert_eq|assert_ne)!',text):assertions.append(text)
        # Rust parses a tuple selector as integer_literal, but its AST role is a field, not a value.
        field=node.parent.child_by_field_name('field') if node.parent is not None and node.parent.type=='field_expression' else None
        selector=field is not None and field.id==node.id and node.type=='integer_literal'
        # A negative expression has a unary AST wrapper outside a macro, but
        # only '-' and literal tokens inside token_tree. Count actual value
        # tokens and every minus token once, not the unary wrapper plus child.
        # This preserves signs (including macro inputs), spelling/suffix/count
        # and order across array/vec! binding adaptation; selector fields stay
        # excluded exactly as before. Removing/changing '-' still rejects.
        if not selector and (node.type.endswith('_literal') or node.type=='-'):literals.append(text)
        stack.extend(reversed(node.children))
    return {'assertions':assertions,'literals':literals,'tests':code.count('#[test]'),
            'ignored':len(re.findall(r'#\s*\[\s*ignore\b',code)),
            'bounds':{b:len(re.findall(r'\b'+b+r'\b',code)) for b in ['Clone','Copy','Ord','PartialOrd']}}



def rejecting_match_sites(code):
    """Exact original byte locations; no panic-accepting test can use this route."""
    data=code.encode();root=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
    if root.has_error or any(name in code for name in ['catch_unwind','should_panic']):return []
    stack=[root];result=[]
    while stack:
        node=stack.pop();stack.extend(node.named_children)
        if node.type!='match_expression':continue
        body=node.child_by_field_name('body')
        if body is None:continue
        arms=[c for c in body.named_children if c.type=='match_arm']
        if not arms:continue
        if any(data[a.start_byte:a.end_byte].lstrip().startswith(b'_ =>') for a in arms):continue
        tail=data[arms[-1].end_byte:body.end_byte-1]
        comma=b'' if data[arms[-1].start_byte:arms[-1].end_byte].rstrip().endswith(b',') or b',' in tail else b','
        value=node.child_by_field_name('value')
        if value is not None:result.append({'row':value.start_point.row+1,'column':value.start_point.column+1,
            'point':body.end_byte-1,'tail_start':arms[-1].end_byte,'match_start':node.start_byte,
            'insertion':comma+b'\n_ => ::core::panic!(),\n'})
    return result


def rejecting_match_extensions(code):
    data=code.encode()
    return [(s['row'],s['column'],(data[:s['point']]+s['insertion']+data[s['point']:]).decode()) for s in rejecting_match_sites(code)]


def exhaustiveness_plan(frozen,result):
    """Bind the complete diagnostic to exact frozen integration-test AST nodes."""
    if result.get('status')!='support_test_compile_failed' or result.get('frozen_identity')!=frozen['identity']:return None
    if result.get('immutable_test_sources')!=frozen['tests']:return None
    diagnostic=result.get('diagnostic','')
    errors=re.findall(r'^error(?:\[([^\]]+)\])?: (.*)$',diagnostic,re.M)
    actual=[(code,text) for code,text in errors if not (not code and text.startswith(('could not compile ', 'aborting due to ')))]
    if not actual or any(code!='E0004' for code,_ in actual):return None
    locations=re.findall(r'^error\[E0004\]:[^\n]*\n\s*--> tests/source_contract_(\d+)\.rs:(\d+):(\d+)',diagnostic,re.M)
    if len(locations)!=len(actual):return None # Reject unbound/non-test errors, not only the subset we understand.
    plan={}
    for index,line,column in sorted({tuple(map(int,location)) for location in locations}):
        if index>=len(frozen['tests']):return None
        sites=[s for s in rejecting_match_sites(frozen['tests'][index]) if s['row']+2==line and s['column']==column]
        if len(sites)!=1:return None
        plan.setdefault(index,[]).append(sites[0])
    return plan


def canonical_exhaustiveness(frozen,plan):
    changed={}
    for index,sites in plan.items():
        data=frozen['tests'][index].encode()
        for site in sorted(sites,key=lambda s:s['point'],reverse=True):
            point=site['point'];data=data[:point]+site['insertion']+data[point:]
        changed[index]=data.decode()
    return changed


def normalize_rejecting_proposal(frozen,proposal,plan):
    """Recognize only compiler-bound last-arm insertions; diagnostic strings are
    allowed solely in those new direct panic invocations, then discarded. All
    original bytes remain, including every old literal and nested match arm.
    """
    if not isinstance(proposal,dict):return False
    if set(proposal)-{'action','reason','edits','reading_notes','request_pages'}:return False
    if proposal.get('action','binding_fix')!='binding_fix' or not isinstance(proposal.get('edits'),list):return False
    texts={};seen=set()
    for edit in proposal['edits']:
        if not isinstance(edit,dict) or set(edit)!={'kind','index','old','new'} or edit['kind']!='integration' or type(edit['index']) is not int or edit['index'] not in plan:return False
        index=edit['index'];text=texts.get(index,frozen['tests'][index]);old=edit['old'];new=edit['new']
        if not isinstance(old,str) or not old or not isinstance(new,str) or text.count(old)!=1:return False
        texts[index]=text.replace(old,new,1);seen.add(index)
    if seen!=set(plan):return False
    def matches(data):
        root=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
        if root.has_error:return None
        stack=[root];found=[]
        while stack:
            node=stack.pop();stack.extend(node.named_children)
            if node.type=='match_expression':found.append(node)
        return sorted(found,key=lambda n:n.start_byte)
    for index,text in texts.items():
        before=frozen['tests'][index].encode();after=text.encode()
        oldmatches=matches(before);newmatches=matches(after)
        if oldmatches is None or newmatches is None or len(oldmatches)!=len(newmatches):return False
        targets={s['match_start'] for s in plan[index]};removals=[]
        for old,node in zip(oldmatches,newmatches):
            if old.start_byte not in targets:continue
            oldbody=old.child_by_field_name('body');body=node.child_by_field_name('body')
            oldarms=[n for n in oldbody.named_children if n.type=='match_arm'];arms=[n for n in body.named_children if n.type=='match_arm']
            if len(arms)!=len(oldarms)+1:return False
            arm=arms[-1];pattern=arm.child_by_field_name('pattern');value=arm.child_by_field_name('value')
            if pattern is None or pattern.child_by_field_name('condition') is not None:return False
            if value is None or value.type!='macro_invocation':return False
            macro=value.child_by_field_name('macro');token_tree=next((n for n in value.named_children if n.type=='token_tree'),None)
            if macro is None or macro.text not in {b'panic',b'::core::panic',b'::std::panic'} or token_tree is None:return False
            args=[n for n in token_tree.named_children if n.type not in {'line_comment','block_comment'}]
            if len(args)>1 or (args and args[0].type not in {'string_literal','raw_string_literal'}):return False
            tokens=[n for n in token_tree.children if n.type not in {'(',')','[',']','{','}',',','line_comment','block_comment'}]
            if tokens!=args:return False
            # Strip only the added arm and its separator/spacing. A comma newly
            # attached to a formerly comma-less block arm belongs to the insertion.
            start=arms[-2].end_byte
            if not oldarms[-1].text.endswith(b',') and arms[-2].text.endswith(b','):start-=1
            removals.append((start,body.end_byte-1,before[oldarms[-1].end_byte:oldbody.end_byte-1]))
        restored=after
        for start,end,tail in sorted(removals,reverse=True):restored=restored[:start]+tail+restored[end:]
        if restored!=before:return False
    return True


def exhaustiveness_revision(frozen,result,state,proposal=None):
    plan=exhaustiveness_plan(frozen,result)
    if not plan:return None
    if proposal is not None and not normalize_rejecting_proposal(frozen,proposal,plan):
        raise Failure('support_oracle_change','Compiler-bound completion may only append direct rejecting last arms; original tests must remain byte-identical')
    changed=canonical_exhaustiveness(frozen,plan)
    # The ordinary invariants still check the canonical result: no new literal,
    # assertion, input, expectation, obligation, bound or test-count permission.
    return revise(frozen,{'reason':'Compiler E0004 at the frozen match: preserve every original arm and append only an unconditional failing wildcard.',
        'edits':[{'kind':'integration','index':i,'old':frozen['tests'][i],'new':text} for i,text in sorted(changed.items())]},state)


def trailing_macro_separators(code):
    """Remove only a final argument comma directly owned by a macro invocation."""
    data=code.encode();root=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
    if root.has_error:return []
    result=[];stack=[root]
    while stack:
        node=stack.pop();stack.extend(node.children)
        if node.type!=',' or node.parent is None or node.parent.type!='token_tree':continue
        parent=node.parent
        if parent.parent is None or parent.parent.type!='macro_invocation':continue
        following=[c for c in parent.children if c.start_byte>=node.end_byte and c.type not in {'line_comment','block_comment'}]
        if len(following)!=1 or following[0].type not in {')',']','}'}:continue
        changed=(data[:node.start_byte]+data[node.end_byte:]).decode()
        if invariants(code)==invariants(changed):result.append((node.start_point.row+1,node.start_point.column+1,changed))
    return result


def macro_separator_revision(frozen,result,state):
    if result.get('status')!='support_test_compile_failed' or result.get('frozen_identity')!=frozen['identity'] or result.get('immutable_test_sources')!=frozen['tests']:return None
    diagnostic=result.get('diagnostic','')
    locations=re.findall(r'error: no rules expected `,`\n\s*--> tests/source_contract_(\d+)\.rs:(\d+):(\d+)',diagnostic)
    if len(locations)!=1 or re.search(r'error\[E\d+\]',diagnostic):return None
    index,line,column=map(int,locations[0])
    if index>=len(frozen['tests']):return None
    old=frozen['tests'][index];matches=[new for row,col,new in trailing_macro_separators(old) if row+2==line and col==column]
    if len(matches)!=1:return None
    return revise(frozen,{'reason':'Compiler rejected the final macro argument comma; remove only that token, preserving all argument expressions and assertions.',
        'repair_kind':'trailing_macro_separator','edits':[{'kind':'integration','index':index,'old':old,'new':matches[0]}]},state)

def revise(frozen,proposal,state,*,compiler_failure=None):
    if proposal.get('obligations',frozen['obligations'])!=frozen['obligations']:
        raise Failure('support_oracle_change','Binding repairs must preserve every frozen source case and expectation')
    updated=deepcopy(frozen)
    for edit in proposal.get('edits',[]):
        kind=edit.get('kind');index=edit.get('index')
        seq=updated['tests'] if kind=='integration' else updated.get('unit_tests',[]) if kind=='unit' else None
        if seq is None or not isinstance(index,int) or not 0<=index<len(seq):raise Failure('invalid_support_binding_patch','Unknown test index',edit)
        code=seq[index] if kind=='integration' else seq[index]['source']
        old=edit.get('old');new=edit.get('new')
        if not isinstance(old,str) or not old or not isinstance(new,str) or code.count(old)!=1:raise Failure('invalid_support_binding_patch','Use one exact original test-text match',edit)
        changed=code.replace(old,new,1)
        if proposal.get('repair_kind')=='rejecting_exhaustiveness' and changed not in [v for _,_,v in rejecting_match_extensions(code)]:
            raise Failure('support_oracle_change','Exhaustiveness repair must only append an unconditional failing last arm; preserve every original byte')
        if proposal.get('repair_kind')=='trailing_macro_separator' and changed not in [v for _,_,v in trailing_macro_separators(code)]:
            raise Failure('support_oracle_change','Macro binding repair may remove only the compiler-located final comma, preserving every argument and assertion')
        if kind=='integration':seq[index]=changed
        else:seq[index]['source']=changed
    if compiler_failure and re.search(r'^error\[E0004\]:',compiler_failure.get('diagnostic',''),re.M):
        def match_code(code):
            root=Parser(Language(tree_sitter_rust.language())).parse(code.encode()).root_node
            if root.has_error:return None
            stack=[root];found=[]
            while stack:
                node=stack.pop();stack.extend(node.named_children)
                if node.type=='match_expression':found.append((node.start_byte,node.text))
            return [text for _,text in sorted(found)]
        originals=frozen['tests']+[t['source'] for t in frozen.get('unit_tests',[])]
        proposed=updated['tests']+[t['source'] for t in updated.get('unit_tests',[])]
        if any(match_code(a)!=match_code(b) for a,b in zip(originals,proposed)):
            revised=exhaustiveness_revision(frozen,compiler_failure,state,proposal)
            if revised is None:raise Failure('support_oracle_change','Incomplete or mixed compiler evidence cannot authorize match completion')
            return revised
        # Unchanged matches keep ordinary import/type binding repairs available,
        # even when an unrelated E0004 accompanies the compiler binding error.
    for old,new in zip(frozen['tests']+[t['source'] for t in frozen.get('unit_tests',[])],updated['tests']+[t['source'] for t in updated.get('unit_tests',[])]):
        before=invariants(old);after=invariants(new)
        if before!=after:
            raise Failure('support_oracle_change','Binding patch changed protected source-test invariants',{'invariant_differences':{key:{'before':before[key],'after':after[key]} for key in before if before[key]!=after[key]}})
    for location in proposal.get('unit_locations',[]):
        index=location.get('index');file=location.get('file');scope=location.get('module',[])
        if not isinstance(index,int) or not 0<=index<len(updated.get('unit_tests',[])) or file not in state['files']:raise Failure('invalid_support_binding_patch','Choose an existing unit test and source file')
        insert_tests(state['files'][file],scope,'')
        updated['unit_tests'][index].update(file=file,module=scope)
    relocations=proposal.get('relocations',[])
    indices=[r.get('integration_index') for r in relocations]
    if any(not isinstance(i,int) or not 0<=i<len(updated['tests']) for i in indices) or len(set(indices))!=len(indices):raise Failure('invalid_support_binding_patch','Invalid integration-test relocation indices')
    for row in sorted(relocations,key=lambda r:r['integration_index'],reverse=True):
        if row.get('file') not in state['files']:raise Failure('invalid_support_binding_patch','Relocate only into an existing source module')
        insert_tests(state['files'][row['file']],row.get('module',[]),'')
        updated.setdefault('unit_tests',[]).append({'file':row['file'],'module':row.get('module',[]),'source':updated['tests'].pop(row['integration_index'])})
    if updated==frozen:raise Failure('invalid_support_binding_patch','No actual test binding change')
    updated['oracle_identity']=frozen.get('oracle_identity',frozen['identity'])
    updated['parent_identity']=frozen['identity']
    updated['binding_reason']=proposal['reason']
    updated['identity']=fingerprint({'parent':frozen['identity'],'tests':updated['tests'],'unit_tests':updated.get('unit_tests',[]),'interfaces':interfaces(state['files'])})
    updated['status']='independently_reviewed_binding_revision'
    return updated


def adjudicate(frozen,result,state,cfg,provider,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    deterministic=exhaustiveness_revision(frozen,result,state)
    method='compiler-span-exhaustiveness-v2'
    if deterministic is None:
        deterministic=macro_separator_revision(frozen,result,state);method='compiler-span-final-macro-separator-v1'
    if deterministic is not None:
        deterministic['status']='mechanically_verified_binding_revision'
        deterministic['binding_audit']={'path':str(directory),'method':method,'review':deterministic['binding_reason']+' Original expectations and obligations unchanged.'}
        save(directory/'mechanical-revision.json',deterministic)
        return {'action':'binding_fix','frozen':deterministic,'evidence':str(directory)}
    ids={o['source'] for o in frozen['obligations'] if o.get('source') in state['bundle']['source_model']['entities']}
    source_pages=pages(state['bundle']['source_model'],ids,cfg['segmented']['source_page_characters'])
    payload={'task':'''Independently classify a failed source-contract test. Candidate bodies are withheld.
Return action:algorithm_issue with a specific source-based reason when the implementation API or behavior violates the source (including unsupported Clone/Ord bounds).
For a test-only import, scope, or stale interface binding defect return action:binding_fix, reason, edits:[{kind:"integration|unit",index:0,old:"one exact match",new:"replacement"}]. Do NOT change any source case, expectation, literal, assertion text, test count, ignore attribute or generic-test bound. Preserve assertion invocations verbatim; use imports/aliases or source-faithful adapters to correct bindings. For missing type inference on an empty input, add a local typed function binding or adapter before the original assertion; do not insert turbofish syntax inside the frozen assertion. Read prior_binding_rejection and avoid repeating its rejected edit. No production edits. Tests remain frozen except for independently reviewed bindings.
If an integration test incorrectly needs access to private support, it may be relocated unchanged after edits using relocations:[{integration_index:0,file:"src/lib.rs",module:[]}]. For an existing unit test, correct its target with unit_locations:[{index:0,file:"src/lib.rs",module:["numeric"]}]. module is the inline module_scope relative to the actual file. It executes as an internal test module without making production helpers public. For original qualified calls, an alias such as use crate as i2r_candidate can preserve assertions verbatim.
For a wrong mathematical expectation or disputed source domain, return action:oracle_dispute with concrete source evidence; do not weaken the oracle or force algorithm changes. If evidence does not establish a test defect, return algorithm_issue, never invent a patch.''',
        'prior_binding_rejection':state.get('feedback') if (state.get('feedback') or {}).get('status') in {'support_oracle_change','invalid_support_binding_patch','support_binding_review_failed'} else None,
        'frozen':frozen,'failure':result,'numeric_policy':state['bundle']['numeric_policy'],'mapping':state['mapping'],
        'interfaces':interfaces(state['files']),
        'rust_config':state['rust_config']}
    from .support_binding_context import prepare as binding_context,restrict
    if cfg.get('translation',{}).get('correctness_only'):
        focused,source_pages=binding_context(frozen,result,state,cfg,directory)
        payload.update(focused)
        payload['task']+=' Compiler-localized artifact indices are original global indices, not positions in the selected list. Read required source pages; use exact optional dependency/test/obligation pages when needed. All interfaces include generic constraints. Do not edit another group. Full original assertions and obligations remain mechanically enforced and all groups execute after any repair.'
    proposal=source_review(payload,source_pages,cfg,provider,directory/'diagnosis',system=AUDIT_SYSTEM);save(directory/'diagnosis.json',proposal)
    action=proposal.get('action')
    if action=='algorithm_issue' and proposal.get('reason'):return {'action':action,'reason':proposal['reason'],'evidence':str(directory)}
    if action=='oracle_dispute':raise Failure('support_oracle_dispute','Independent source expectations require adjudication; do not repair the algorithm to fit them',proposal)
    if action!='binding_fix' or not proposal.get('reason'):raise Failure('invalid_support_audit','Return a justified classification',proposal)
    if payload.get('focused_binding_scope'):restrict(proposal,payload['focused_binding_scope'])
    try:updated=revise(frozen,proposal,state,compiler_failure=result)
    except Failure as error:
        if error.code=='support_oracle_change':
            # Persist across audit attempts, but never transfer rejection counts to another suite/API.
            rejection_key=fingerprint({'policy':'binding-invariant-rejection-bound-v1','frozen':frozen['identity'],'interfaces':interfaces(state['files']),'reason':str(error),'evidence':error.evidence})
            ledger=state.setdefault('support_binding_rejections',{})
            count=ledger.get(rejection_key,0)+1;ledger[rejection_key]=count
            evidence={**(error.evidence or {}),'rejection_key':rejection_key,'same_rejection_count':count,'limit':2,'proposal':str(directory/'diagnosis.json')}
            if count>=2:raise Failure('support_binding_stalled','Same protected binding rejection repeated twice without suite/API progress; original test remains unchanged',evidence) from error
            raise Failure(error.code,str(error),evidence) from error
        raise
    if cfg.get('translation',{}).get('correctness_only'):
        updated['status']='mechanically_validated_binding_revision_pending_execution'
        updated['binding_audit']={'path':str(directory),'method':'compiler-group-diagnosis-mechanical-invariants-v1','second_model_review':False,'validation':'Assertions, literals, bounds, test count and obligations preserved; original full suite must execute next.'}
        return {'action':'binding_fix','frozen':updated,'evidence':str(directory)}
    review_payload={**payload,'task':'Independently review this binding-only correction. Verify original source cases, expected values, assertion logic, generic strength and scope all remain unchanged. Return action:accept with detailed review, or action:reject with reason. Candidate implementation is still withheld.', 'proposal':proposal,'revised_tests':updated}
    reviewed=source_review(review_payload,source_pages,cfg,provider,directory/'review',system=AUDIT_SYSTEM);save(directory/'review.json',reviewed)
    if reviewed.get('action')!='accept' or not reviewed.get('review'):raise Failure('support_binding_review_failed','Independent binding review did not accept',reviewed)
    updated['binding_audit']={'path':str(directory),'review':reviewed['review']}
    return {'action':'binding_fix','frozen':updated,'evidence':str(directory)}
