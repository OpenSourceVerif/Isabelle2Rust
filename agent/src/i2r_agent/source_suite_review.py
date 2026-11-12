"""One isolated, complete source-test semantic judgment before test execution."""
from copy import deepcopy
from pathlib import Path
import re,time
from . import source_check_citations as citations
from .common import Failure,read,save,digest
from .task_context import fingerprint,Conversation
from .segmented_contract import items,interfaces
from .segmented_context import pages
from .support_scope import needed

POLICY='whole-source-suite-independent-check-targets-v4'
CHECKER_MAX_OUTPUT_TOKENS=65536
SYSTEM='''Independently check the semantics of the COMPLETE source-test suite before execution. This is not candidate program review. Candidate function/macro bodies, execution outputs, author reasoning and generation history are unavailable. Source equations and task numeric policy alone determine validity. Author obligation case/expected_basis and mapping rationale are untrusted claims, not evidence. After a protected expectation correction, unchanged obligation prose can retain the old claim; evaluate its required responsibility against the current actual test code and source, and mention stale prose in reason rather than treating it as the oracle. Inspect all actual injected test/framework/template code, inputs/preconditions, expected values, assertion strength, generic/numeric/private-helper responsibilities and every declared test/obligation. Return one complete compact JSON checklist, not a bare accept. Check all actual tests, not all possible inputs or a proof of program equivalence. Finite coverage alone is not a test defect. A test need not cover every source operation. Evaluate generic/non-Clone/branch-instrumentation tests against their legitimate source-interface and declared adaptation contracts. Do not call a suite wrong or uncertain merely because whole-program correctness is unproved. Same-model independent roles do not establish proof. If uncertain, return inconclusive; never guess an expectation to fit a candidate. Only precisely source-proven second assert_eq/assert_ne arguments may be corrected; retain inputs, actual calls, test names, unaffected assertions and all obligations. Broader input/precondition changes are needs_revision and remain unresolved. No candidate edits, no whole-suite replacement.'''
PROTOCOL={
 'action':'accept | test_wrong | needs_revision | inconclusive',
 'source_evidence':[{'id':'e1','source':'exact source ID','quote':'exact source excerpt'}],
 'tests':[{'id':'exact inventory test ID','verdict':'correct | wrong | uncertain','basis':['e1'],'premise':'input/precondition validity','expectation':'source-derived expected result or property','assertion':'assertion meaning and strength','reason':'brief overall conclusion'}],
 'obligations':[{'id':'o:0','verdict':'covered | not_applicable | inaccessible | wrong | uncertain','tests':['exact inventory test ID'],'basis':['e1'],'reason':'brief responsibility and source basis'}],
 'derivation':'For test_wrong only: precise source derivation of every replacement.',
 'edits':[{'target_id':'exact expectation_targets slot ID; required for repeated expected text', 'kind':'integration | unit','index':0,'test_id':'exact test marked wrong','old':'complete original second assert_eq/ne argument','new':'closed source-derived expected expression'}]}
SYSTEM+=''' Decide the action in this order, once per complete checklist. First check each actual input and assertion against the supplied source and numeric policy. Then separate a wrong expected value that can be repaired solely in the protected expected argument from an input/precondition/required-coverage defect. The obligation category and required responsibility are not waived by correcting stale case/expected_basis prose: for example, retained non-extreme integer inputs cannot be called checked-representation boundary coverage merely by changing their expected values. If fulfilling any required responsibility needs changed inputs, fixtures, helpers or assertions outside the protected expected arguments, choose needs_revision for the whole response, mark the affected responsibility wrong (or uncertain if unproved), and give the short source-grounded reason; do not also design expectation edits. If a necessary source fact is missing, choose inconclusive and identify that fact, rather than inferring it from a datatype shape or an implementation convention. Otherwise choose test_wrong only when every proposed correction is source-proven and preserves all required responsibilities; choose accept only when all actual tests and responsibilities are correct. A finite test suite need not establish program equivalence, but this does not excuse a specifically declared required responsibility that the actual inputs do not exercise. When action requirements cannot be established, return the complete uncertain checklist with inconclusive; do not speculate about which answer a validator or grader prefers. For needs_revision/inconclusive, omit edits and replacement derivations. Reuse short exact evidence citations and concise checklist fields rather than repeating their source text or drafting alternative repairs.'''
SYSTEM+=' Use expectation_targets slots to identify a protected expected argument, especially repeated literals in one test. Copy target_id, test_id, kind, index and old exactly; propose only new. Slot IDs do not authorize any change to calls, inputs, helpers or obligations. Never invent offsets, choose the first textual match, or alter every equal literal. If no protected slot can express the proven repair, use needs_revision. '
SYSTEM+=' Mapping contains canonical source/item identifiers and type-parameter bindings only, without implementation text or generator rationale. '+citations.GUIDANCE
PROTOCOL['source_evidence']=[citations.PROTOCOL]
from .native_numeric_contracts import context as native_contracts,GUIDANCE as NATIVE_GUIDANCE
SYSTEM+=' '+NATIVE_GUIDANCE
MAX_COMPLETED=2

def inventory(frozen):
    result=[]
    groups=[('integration',i,code,[f'__i2r_source_contract_{i}']) for i,code in enumerate(frozen['tests'])]
    groups += [('unit',i,row['source'],row.get('module',[])+[f'__i2r_contract_{i}']) for i,row in enumerate(frozen.get('unit_tests',[]))]
    for kind,index,code,prefix in groups:
        for rows in items({'src/lib.rs':code}).values():
            for row in rows:
                if row['kind']=='function_item' and any(re.fullmatch(r'#\s*\[\s*test\s*\]',a) for a in row.get('attributes',[])):
                    result.append({'id':'::'.join(prefix+row['module_scope']+[row['name']]),'kind':kind,'index':index,'relative_name':'::'.join(row['module_scope']+[row['name']]),'attributes':row.get('attributes',[])})
    if not result or len({r['id'] for r in result})!=len(result):raise Failure('source_suite_review_unresolved','Full source suite needs unique declared test IDs')
    return result

from .source_test_context import bodyless_interfaces as checker_interfaces,canonical_mapping as checker_mapping


def scope(frozen,state,cfg):
    from .source_suite_batches import POLICY as batch_policy,SYSTEM as batch_system
    model=state['bundle']['source_model'];ids=needed(model,set(model['entries'])|{o['source'] for o in frozen['obligations']})
    fields={'native_numeric_contracts':native_contracts(state),'length_fallback':{'policy':batch_policy,'system':batch_system},'policy':POLICY,'system':SYSTEM,'protocol':PROTOCOL,'source':{k:state['bundle'].get(k) for k in ['source_model','original_source_model','source_hashes','numeric_policy']},
        'source_pages_identity':fingerprint(pages(model,ids,cfg['segmented']['source_page_characters'])),
        'suite':{k:frozen.get(k) for k in ['tests','unit_tests','obligations','source_contract_templates','test_framework','author_group_plan']},
        'interfaces':checker_interfaces(state),'mapping':checker_mapping(state),'rust_config':state['rust_config'],
        'model':{k:cfg['model'].get(k) for k in ['name','endpoint']},'generation':cfg['generation'],'checker_max_output_tokens':CHECKER_MAX_OUTPUT_TOKENS,'max_completed':MAX_COMPLETED}
    return fingerprint(fields)

def payload(frozen,state,cfg):
    model=state['bundle']['source_model'];ids=needed(model,set(model['entries'])|{o['source'] for o in frozen['obligations']})
    material={'native_numeric_contracts':native_contracts(state),'task':'Check this entire suite, including actual framework/template code; every test and obligation needs one checklist record.',
        'policy':POLICY,'response_protocol':PROTOCOL,'inventory':inventory(frozen),
        'tests':frozen['tests'],'unit_tests':frozen.get('unit_tests',[]),
        'obligations':[{'id':f'o:{i}','claim':o} for i,o in enumerate(frozen['obligations'])],
        'framework_and_template_provenance':{k:frozen.get(k) for k in ['test_framework','source_contract_templates','author_group_plan']},
        'source':pages(model,ids,cfg['segmented']['source_page_characters']),
        'interfaces':checker_interfaces(state),'mapping':checker_mapping(state),'numeric_policy':state['bundle']['numeric_policy'],'rust_config':state['rust_config']}
    from .expectation_targets import attach
    return attach(frozen,state,material)

def validate(proposal,frozen,state,material=None):
    if not isinstance(proposal,dict):raise Failure('source_suite_review_unresolved','Checker must return a complete object')
    inv={r['id']:r for r in inventory(frozen)};obligations={f'o:{i}':o for i,o in enumerate(frozen['obligations'])}
    material=material or payload(frozen,state,{'segmented':{'source_page_characters':16000}})
    if material.get('check_scope'):
        from .source_suite_batches import validation_scope
        inv,obligations=validation_scope(frozen,material)
    if material.get('failure_scope'):
        from .source_failure_review import validation_scope
        inv,obligations=validation_scope(frozen,material,state)
    normalized,_=citations.normalize(proposal,material);cited={r['id']:r for r in normalized['source_evidence']}
    if proposal.get('action') not in {'accept','test_wrong','needs_revision','inconclusive'}:raise Failure('source_suite_review_unresolved','Unknown checker verdict')
    if proposal.get('action')=='accept' and proposal.get('edits'):raise Failure('source_suite_review_unresolved','Acceptance cannot also propose changes')
    checks={}
    for field,expected,allowed in [('tests',inv,{'correct','wrong','uncertain'}),('obligations',obligations,{'covered','not_applicable','inaccessible','wrong','uncertain'})]:
        rows=proposal.get(field)
        if not isinstance(rows,list) or any(not isinstance(r,dict) or not isinstance(r.get('id'),str) for r in rows) or len(rows)!=len(expected) or {r.get('id') for r in rows}!=set(expected):
            raise Failure('source_suite_review_unresolved','Checker must cover every exact '+field+' item once',{'expected_ids':sorted(expected)})
        for row in rows:
            if row.get('verdict') not in allowed or not isinstance(row.get('reason'),str) or not row['reason'].strip() or not isinstance(row.get('basis'),list) or not row['basis'] or any(not isinstance(k,str) or k not in cited for k in row['basis']):
                raise Failure('source_suite_review_unresolved','Incomplete source-grounded checklist record',row)
            if field=='tests' and any(not isinstance(row.get(k),str) or not row[k].strip() for k in ['premise','expectation','assertion']):
                raise Failure('source_suite_review_unresolved','Each test requires explicit premise, expectation and assertion checks',row)
            if field=='obligations':
                claim=obligations[row['id']];names=row.get('tests',[])
                if not isinstance(names,list) or any(not isinstance(n,str) or n not in inv for n in names):raise Failure('source_suite_review_unresolved','Unknown test in obligation checklist',row)
                if row['verdict'] in {'not_applicable','inaccessible'} and claim.get('disposition')!=row['verdict']:raise Failure('source_suite_review_unresolved','Checker cannot waive a required executing obligation',row)
                if row['verdict']=='covered' and (not names or claim.get('test_name') not in names):raise Failure('source_suite_review_unresolved','Covered obligation must identify its exact bound test',row)
        checks[field]={r['id']:r for r in rows}
    if proposal.get('action')=='accept' and (any(r['verdict']!='correct' for r in checks['tests'].values()) or any(r['verdict'] not in {'covered','not_applicable','inaccessible'} for r in checks['obligations'].values())):
        raise Failure('source_suite_review_unresolved','Acceptance conflicts with incomplete/wrong checklist')
    return checks

def revise(frozen,proposal,state,material=None):
    material=material or payload(frozen,state,{'segmented':{'source_page_characters':16000}})
    proposal,_=citations.normalize(proposal,material)
    checks=validate(proposal,frozen,state,material);inv={r['id']:r for r in inventory(frozen)}
    if proposal.get('action')!='test_wrong':raise Failure('source_suite_review_unresolved','Only a source-proven wrong expectation admits protected correction')
    from .source_failure_check import revise as expectation_revision
    from .expectation_targets import resolve
    edits=proposal.get('edits',[])
    if not isinstance(edits,list) or not edits or any(not isinstance(e,dict) for e in edits):raise Failure('source_suite_review_unresolved','No precise expectation correction')
    for edit in edits:
        if not isinstance(edit.get('test_id'),str) or 'file' in edit:raise Failure('source_suite_review_unresolved','Exact test ID required; no production files')
        test=inv.get(edit.get('test_id'));old=edit.get('old')
        if not test or checks['tests'][test['id']]['verdict']!='wrong' or (edit.get('kind'),edit.get('index'))!=(test['kind'],test['index']):raise Failure('source_suite_review_unresolved','Edit must identify an exact test marked wrong',edit)
        resolve(frozen,state,material,edit)
    if any(k in proposal for k in ['files','mapping','rust_config','remove_files','remove_mapping','strategy_updates']):raise Failure('source_suite_review_unresolved','Checker cannot modify production artifacts')
    source_only=[row for row in proposal['source_evidence'] if row['kind']=='source']
    converted={**proposal,'obligations':frozen['obligations'],'source_evidence':source_only}
    updated=expectation_revision(frozen,converted,state,citation_material=material)
    from .oracle_metadata import synchronize
    return synchronize(frozen,updated,proposal,checks)


def provider_receipt(provider):
    directory=Path(provider.directory)/f'{provider.calls:03d}'
    record={k:str(directory/name) for k,name in [('request','request.json'),('response','response.json'),('call_state','call-state.json')]}
    for key in ['request','response','call_state']:record[key+'_sha256']=digest(Path(record[key]))
    verify_receipt(record);return record

def call_record(provider,cfg,system,material,path,row,ledger,ledger_path):
    start=time.monotonic();before_calls=provider.calls;before_usage=deepcopy(provider.usage)
    conversation=Conversation(path/'isolated-conversation.json',cfg);conversation.enter('whole-source-suite-check')
    try:proposal=conversation.call(provider,system,material,path/'request',phase='source_test_check',options={'max_output_tokens':CHECKER_MAX_OUTPUT_TOKENS})
    except Failure as error:
        row.update(status='interrupted' if error.code in {'provider_error','provider_protocol_error'} else 'unresolved_response',error={'code':error.code,'message':str(error),'evidence':error.evidence});save(ledger_path,ledger)
        if error.code in {'provider_error','provider_protocol_error','budget_exhausted'}:raise
        raise Failure('source_suite_review_unresolved','Checker did not produce a complete response',row) from error
    finally:
        row['resources']={'seconds':time.monotonic()-start,'calls':provider.calls-before_calls,'usage_before':before_usage,'usage_after':deepcopy(provider.usage)};save(ledger_path,ledger)
    save(path/'verdict.json',proposal);row.update(status='completed',action=proposal.get('action'),verdict_sha256=digest(path/'verdict.json'),provider_receipt=provider_receipt(provider));save(ledger_path,ledger)
    return proposal

def inventory_protocol(proposal,material):
    expected={'tests':{r['id'] for r in material['inventory']},'obligations':{r['id'] for r in material['obligations']}}
    issues={}
    for field,ids in expected.items():
        rows=proposal.get(field);counts={}
        if not isinstance(rows,list) or any(not isinstance(r,dict) or not isinstance(r.get('id'),str) for r in rows):
            issues[field]={'malformed':True,'expected_ids':sorted(ids)};continue
        for r in rows:counts[r['id']]=counts.get(r['id'],0)+1
        if set(counts)!=ids or any(n!=1 for n in counts.values()):
            issues[field]={'missing_ids':sorted(ids-set(counts)),'unknown_ids':sorted(set(counts)-ids),
                           'duplicate_ids':sorted(k for k,n in counts.items() if n>1),'expected_ids':sorted(ids)}
    return issues

def preserve_inventory_judgments(original,corrected,material):
    if set(corrected)-{'action','tests','obligations','reason'} or corrected.get('action')!='repair_inventory':
        raise Failure('source_suite_review_unresolved','Inventory correction cannot change the semantic action, evidence or edits')
    merged={**original,**{f:corrected.get(f) for f in ['tests','obligations']}}
    if inventory_protocol(merged,material):raise Failure('source_suite_review_unresolved','One inventory correction remains incomplete or duplicated')
    for field in ['tests','obligations']:
        rows=original.get(field)
        if not isinstance(rows,list):raise Failure('source_suite_review_unresolved','Original checklist is not a recoverable row list')
        actual={r['id']:r for r in merged[field]}
        for old in rows:
            if not isinstance(old,dict) or old.get('id') not in actual or actual[old['id']]!=old:
                raise Failure('source_suite_review_unresolved','Inventory correction changed, dropped or chose among conflicting existing judgments',old)
    return merged

def resolve_inventory(proposal,material,cfg,provider,path,row,ledger,ledger_path):
    if proposal.get('action') not in {'accept','test_wrong','needs_revision','inconclusive'}:return proposal,None
    issues=inventory_protocol(proposal,material)
    if not issues:return proposal,None
    for field in ['tests','obligations']:
        seen={}
        for entry in proposal.get(field,[]) if isinstance(proposal.get(field),list) else []:
            if not isinstance(entry,dict) or not isinstance(entry.get('id'),str):continue
            if entry['id'] in seen and seen[entry['id']]!=entry:
                raise Failure('source_suite_review_unresolved','Conflicting duplicate checklist rows cannot be repaired as formatting; preserve every judgment',{'field':field,'id':entry['id']})
            seen[entry['id']]=entry
    attempts=row.setdefault('inventory_protocol_attempts',[])
    complete=next((r for r in attempts if r.get('status')=='completed'),None)
    if complete:
        correction=complete;directory=Path(correction['directory']);fix=read(directory/'verdict.json')
        verify_receipt(correction['provider_receipt'])
        if digest(directory/'verdict.json')!=correction['verdict_sha256']:raise Failure('source_suite_review_unresolved','Inventory correction archive changed')
    else:
        if attempts:raise Failure('source_suite_review_unresolved','Inventory correction already attempted; no automatic repeat')
        directory=path/'inventory-protocol-001';directory.mkdir()
        correction={'directory':str(directory),'status':'reserved','kind':'inventory_protocol_only'};attempts.append(correction);save(ledger_path,ledger)
        request={'task':'Return {action:"repair_inventory",tests:[...],obligations:[...]}, each exact required ID once. Explicitly remove identical duplicate rows; never silently select between conflicting judgments. Preserve EVERY existing row exactly. Supply source-grounded checklist rows for missing IDs using the existing citation labels; no omitted responsibility. Do not change the original semantic action, citations, edits or inputs. If preservation is impossible return action:unresolved. One correction only.',
                 'diagnostic':issues,'original_judgment':proposal,'actual_material':material}
        save(directory/'input.json',request)
        fix=call_record(provider,cfg,'Correct checklist inventory only; preserve judgments and every required responsibility.',request,directory,correction,ledger,ledger_path)
    amended=preserve_inventory_judgments(proposal,fix,material)
    return amended,{'original_judgment_sha256':fingerprint(proposal),'corrected_judgment_sha256':fingerprint(amended),'diagnostic':issues,'provider_receipt':correction['provider_receipt']}

def resolve_citations(proposal,material,frozen,state,cfg,provider,path,row,ledger,ledger_path):
    proposal,inventory_proof=resolve_inventory(proposal,material,cfg,provider,path,row,ledger,ledger_path)
    try:
        normalized,proof=citations.normalize(proposal,material)
    except Failure as error:
        if error.code!='source_suite_citation_protocol':raise
        save(path/'citation-protocol-failure.json',{'code':error.code,'message':str(error),'evidence':error.evidence,'original_verdict_sha256':row['verdict_sha256']})
        corrections=row.setdefault('citation_protocol_attempts',[]);complete=next((x for x in corrections if x['status']=='completed'),None)
        if complete:
            correction_path=Path(complete['directory']);fix=read(correction_path/'verdict.json')
            if digest(correction_path/'verdict.json')!=complete['verdict_sha256']:raise Failure('source_suite_review_unresolved','Citation correction archive changed')
            verify_receipt(complete['provider_receipt'])
        else:
            correction_path=path/f'citation-protocol-{len(corrections)+1:03d}';correction_path.mkdir()
            correction={'directory':str(correction_path),'status':'reserved','kind':'citation_protocol_only','not_additional_semantic_judgment':True};corrections.append(correction);save(ledger_path,ledger)
            request={'task':'Repair ONLY the citation reference table of the completed original judgment. Do not return or change action/tests/obligations/edits or any semantic conclusion. Return {"action":"repair_citations","source_evidence":[...]} with explicitly named unique local IDs matching the existing basis labels. Never infer labels by array position; establish each link from the actual original judgment and quoted source material. If unable, return {"action":"unresolved","reason":"..."}. One completed protocol correction only; no semantic re-review.', 'citation_protocol':citations.PROTOCOL,'diagnostic':{'message':str(error),'evidence':error.evidence},'original_judgment':proposal,'original_judgment_sha256':fingerprint(proposal),'actual_material':material}
            save(correction_path/'input.json',request)
            fix=call_record(provider,cfg,'Correct exact citation provenance only. '+citations.GUIDANCE,request,correction_path,correction,ledger,ledger_path)
        if fix.get('action')!='repair_citations' or set(fix)-{'action','source_evidence','reason'}:raise Failure('source_suite_review_unresolved','One citation-only correction failed or tried to alter semantic judgment',fix)
        amended={**proposal,'source_evidence':fix.get('source_evidence')}
        try:normalized,proof=citations.normalize(amended,material)
        except Failure as unresolved:raise Failure('source_suite_review_unresolved','One completed citation correction remains unresolved',{'message':str(unresolved),'evidence':unresolved.evidence}) from unresolved
        proof.update(original_judgment_sha256=fingerprint(proposal),original_citations=proposal.get('source_evidence'),corrected_citations=fix['source_evidence'],protocol_receipt=complete['provider_receipt'] if complete else correction['provider_receipt'])
    validate(normalized,frozen,state,material)
    assert all(normalized.get(k)==proposal.get(k) for k in proposal if k!='source_evidence'),'Protocol normalization changed semantic manifest'
    if inventory_proof:proof['inventory_protocol']=inventory_proof
    save(path/'citation-verification.json',proof);save(path/'validated-verdict.json',normalized);row['resolved_verdict_sha256']=digest(path/'validated-verdict.json');save(ledger_path,ledger)
    return normalized,proof

def check(frozen,state,cfg,provider,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if cfg['model']['name']!='deepseek-flash':raise Failure('source_suite_review_unresolved','Whole-suite checker requires Flash')
    mapping_audit=directory/'mapping-provenance'/(fingerprint(state['mapping'])+'.json');save(mapping_audit,state['mapping'])
    key=scope(frozen,state,cfg);ledger_path=directory/'ledger.json';ledger=read(ledger_path) if ledger_path.exists() else {'policy':POLICY,'attempts':[]}
    if ledger.get('policy')!=POLICY:raise Failure('source_suite_review_unresolved','Checker ledger policy changed without explicit compatibility admission')
    from . import source_suite_batches as batches
    if any(r.get('kind')=='batch_round' and r['scope']==key for r in ledger['attempts']):return batches.run(frozen,state,cfg,provider,directory,key,ledger)
    for previous in ledger['attempts']:
        trigger=batches.length_trigger(previous,key)
        if trigger:return batches.run(frozen,state,cfg,provider,directory,key,ledger,trigger)
    complete=[r for r in ledger['attempts'] if r['status']=='completed'];cached=next((r for r in complete if r['scope']==key),None)
    if cached:
        row=cached;path=Path(row['directory']);proposal=read(path/'verdict.json');material=read(path/'input.json')
        if digest(path/'verdict.json')!=row['verdict_sha256']:raise Failure('source_suite_review_unresolved','Checker verdict artifact changed')
        verify_receipt(row['provider_receipt'])
    else:
        if len(complete)>=MAX_COMPLETED:raise Failure('source_suite_review_unresolved','Two completed whole-suite judgments exhausted; never waive checking')
        path=directory/f'judgment-{len(ledger["attempts"])+1:03d}';path.mkdir();material=payload(frozen,state,cfg);save(path/'input.json',material);save(path/'original-suite.json',frozen)
        row={'scope':key,'suite_identity':frozen['identity'],'directory':str(path),'status':'reserved','completed_before':len(complete)};ledger['attempts'].append(row);save(ledger_path,ledger)
        try:proposal=call_record(provider,cfg,SYSTEM,material,path,row,ledger,ledger_path)
        except Failure:
            trigger=batches.length_trigger(row,key)
            if trigger:return batches.run(frozen,state,cfg,provider,directory,key,ledger,trigger)
            raise
    proposal,proof=resolve_citations(proposal,material,frozen,state,cfg,provider,path,row,ledger,ledger_path)
    if proposal.get('action')=='accept':
        return {'action':'accept','status':'accepted','scope':key,'suite_identity':frozen['identity'],'evidence':str(path),'verdict_file':'validated-verdict.json','verdict_sha256':row['resolved_verdict_sha256'],'ledger':str(ledger_path),'cache_hit':cached is not None,'complete_tests':len(inventory(frozen)),'complete_obligations':len(frozen['obligations']),'policy':POLICY,'provider_receipt':row['provider_receipt'],'protocol_receipt':proof.get('protocol_receipt'),'citation_proof_sha256':digest(path/'citation-verification.json'),'compatibility_admission':row.get('compatibility_admission'),'mapping_provenance':{'path':str(mapping_audit),'sha256':digest(mapping_audit),'not_checker_input_or_cache_key':True}}
    if proposal.get('action')=='test_wrong':
        updated=revise(frozen,proposal,state,material);save(path/'diagnosis.json',updated['source_check']);updated['binding_audit']={'method':'source-expectation-check-v1','path':str(path),'second_model_review':True};return {'action':'binding_fix','frozen':updated,'evidence':str(path)}
    raise Failure('source_suite_review_unresolved','Whole-suite checker did not accept; preserve original tests and stop',{'evidence':str(path),'action':proposal.get('action')})

def verify_receipt(receipt):
    if not isinstance(receipt,dict) or any(not Path(receipt.get(k,'')).is_file() or digest(Path(receipt[k]))!=receipt.get(k+'_sha256') for k in ['request','response','call_state']):
        raise Failure('source_suite_review_unresolved','Checker acceptance lacks intact request/response/phase archives')
    request=read(Path(receipt['request']));response=read(Path(receipt['response']));call_state=read(Path(receipt['call_state']))
    if request.get('model')!='deepseek-flash' or call_state.get('phase')!='source_test_check' or not isinstance(response,dict) or not response.get('choices') or response['choices'][0].get('finish_reason')!='stop':
        raise Failure('source_suite_review_unresolved','Checker archive is not a completed Flash source_test_check response')

def require(frozen,state,cfg):
    from . import source_suite_batches as batches
    if (state.get('support_review_evidence') or {}).get('method')==batches.POLICY:return batches.require(frozen,state,cfg,state['support_review_evidence'])
    record=state.get('support_review_evidence') or {};path=Path(record.get('evidence',''))/record.get('verdict_file','validated-verdict.json')
    if record.get('status')!='accepted' or record.get('scope')!=scope(frozen,state,cfg) or not path.is_file() or digest(path)!=record.get('verdict_sha256'):
        raise Failure('source_suite_review_unresolved','No current complete independent checker acceptance for this source suite')
    verify_receipt(record.get('provider_receipt'))
    if record.get('protocol_receipt'):verify_receipt(record['protocol_receipt'])
    proof_path=Path(record['evidence'])/'citation-verification.json'
    if not proof_path.is_file() or digest(proof_path)!=record.get('citation_proof_sha256'):raise Failure('source_suite_review_unresolved','Citation provenance archive changed')
    ledger=read(record['ledger'])
    if not any(r['status']=='completed' and r['scope']==record['scope'] and r.get('resolved_verdict_sha256')==record['verdict_sha256'] and r.get('action')=='accept' for r in ledger['attempts']):raise Failure('source_suite_review_unresolved','Acceptance lacks a completed real checker ledger record')
    origin=Path(record['evidence'])/'verdict.json'
    rows=[r for r in ledger['attempts'] if r['status']=='completed' and r['scope']==record['scope'] and r.get('resolved_verdict_sha256')==record['verdict_sha256']]
    if len(rows)!=1 or digest(origin)!=rows[0]['verdict_sha256']:raise Failure('source_suite_review_unresolved','Original completed semantic verdict changed')
    original=read(origin);proposal=read(path)
    repairs=rows[0].get('inventory_protocol_attempts',[])
    if repairs:
        if len(repairs)!=1 or repairs[0].get('status')!='completed':raise Failure('source_suite_review_unresolved','Inventory correction is incomplete or repeated')
        repair=repairs[0];verify_receipt(repair['provider_receipt']);repair_path=Path(repair['directory'])/'verdict.json'
        if digest(repair_path)!=repair['verdict_sha256']:raise Failure('source_suite_review_unresolved','Inventory correction archive changed')
        original=preserve_inventory_judgments(original,read(repair_path),read(Path(record['evidence'])/'input.json'))
    if any(proposal.get(k)!=original.get(k) for k in original if k!='source_evidence'):raise Failure('source_suite_review_unresolved','Citation protocol changed semantic verdict/checklist')
    validate(proposal,frozen,state,read(Path(record['evidence'])/'input.json'))
    if proposal.get('action')!='accept':raise Failure('source_suite_review_unresolved','Checker did not accept')
    return record

def require_state(state,cfg,work):
    fid=state.get('support_evidence',{}).get('frozen_identity');path=Path(work)/'support-tests'/(str(fid)+'.json')
    if not fid or not path.is_file():raise Failure('source_suite_review_unresolved','Missing reviewed full source artifact')
    return require(read(path),state,cfg)
