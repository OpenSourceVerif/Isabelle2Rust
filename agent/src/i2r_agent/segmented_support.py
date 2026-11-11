"""Source-grounded contract tests, authored/reviewed independently of candidate bodies."""
from pathlib import Path
import json
from .common import Failure, save, read, digest
from .context import audit_request
from .program_model import readable
from .segmented_contract import items, interfaces
from .segmented_config import cargo_command
from .task_context import fingerprint, Conversation
from .segmented_context import pages, read_pages, reading_notes

SYSTEM='''Author independent source-contract tests for a translated Rust library. Candidate implementation bodies are intentionally withheld; use source equations plus actual Rust signatures and mapping. Return JSON {test_source:"Rust integration test code", obligations:[{source,case,expected_basis,test_name}], notes:"..."}. Integration tests use i2r_candidate and its actual dependencies. Exercise meaningful numeric sign/zero/conversion/overflow edges and generic/data-structure behavior where source APIs permit. For unconstrained source type variables, include non-Clone/non-Ord instances where operations do not require copying or ordering, so accidental stronger API bounds are exposed. Do not test outside the source precondition; checked necessary overflow must be explicitly recognized as I2R_NUMERIC_OVERFLOW, not accepted as a mathematical result. Never compute expected values by calling the candidate under test. Use independently evaluated small source cases or source laws. Mark source-internal operations unreachable from any public API as inaccessible with source reason; do not invent a callable API or silently claim coverage. At least one #[test] must actually execute a public export. Return no implementation edits. Tests will be frozen before candidate execution and cannot be modified by algorithm repair.'''
SYSTEM+=''' Mechanical mapping gives exact source/item/type-parameter bindings only. Generator implementation prose and bodies are not provided; use actual bodyless Rust interfaces and source equations. Private support operations can also be tested without changing their visibility: optionally return unit_tests:[{file:"src/lib.rs",module:[],source:"use super::*; #[test] fn ..."}]. Each source is wrapped in its own cfg(test) child module with use super::* already supplied. For helpers in inline private modules, set module to the item's module_scope, e.g. ["numeric","internal"], relative to its actual file. The test wrapper is inserted inside that module. Struct/enum/type declarations and cfg attributes are provided as interface facts; algorithm bodies remain withheld. Use this mechanism for private numeric helpers, large arbitrary integers and checked overflows instead of declaring them inaccessible merely because they are not public. Supply the same source-grounded obligations for unit tests. Public-export tests are still required across the complete test set; groups containing only private support can supply only unit_tests. Any correction must return the complete test_source/unit_tests/obligations set.'''
SYSTEM+=''' The user requires preservation of the source business algorithm. Choose tests feasible under that source computation, not tests that require a closed form or alternate algorithm to finish. For Ackermann, test deep recursion with manageable arguments; test arbitrary large n and checked u128 overflow through ack(0,n), whose source equation does constant work, or through private arithmetic helpers. Do not run ack(2,u128::MAX) expecting quick overflow. Finite resource-aware test selection does not narrow the algorithm's specified input domain; record untested expensive regions and never count timeout as equivalent output.'''

SYSTEM+=''' In every obligation, source MUST equal exactly ONE entity ID from available_source_ids. Do not append equation numbers, prose, semicolons or multiple IDs. Put those details in expected_basis. For a test covering several entities, emit separate obligation objects with the same test_name and one source ID each. Check this schema before returning tests; source-grounded expectations do not waive it.'''


SYSTEM+=''' For numeric bit-operation helpers, include feasible large-count cases when their source API permits them: a count larger than usize with zero or small finite operands; signed drop_bit must produce 0 or -1, nonnegative take_bit can return the original operand, and push_bit of zero remains zero. Derive these expectations from the source equations before narrowing the count. Distinguish these small-output cases from a nonzero left shift or negative take_bit whose output itself would be infeasibly large. Under checked policy also distinguish shift-count validity from shifted-value overflow (checked_shl alone does not detect discarded value bits), and test signed minimum/maximum boundaries where the result remains representable. Do not invent APIs or violate source preconditions.'''

SYSTEM+='''The large-count requirement is per applicable operation AND numeric instance, not satisfied by testing one representative method. For numeric bit-operation tests, enumerate this checklist in notes and point to an executing test for every available row: (1) Nat drop with count greater than usize::MAX and small nonzero operand -> 0; (2) signed Int drop with that count and small positive operand -> 0 AND negative operand -> -1; (3) Nat take with that count and small nonzero operand -> unchanged operand; (4) signed Int take with that count and small positive operand -> unchanged operand; (5) Nat push and Int push of zero with that count -> zero. These are all feasible small-output source cases. A merely100-bit OPERAND or a count of100 does not satisfy this count requirement; in arbitrary mode a COUNT such as2^200 does on the supported machine; in checked mode choose a count above usize::MAX that still fits u128 (for example2^100 on a64-bit target). Do not use a huge negative take or nonzero huge push: their output is infeasible. Skip a row only with an explicit source/type-bound reason. Use the actual trait instance if no standalone helper exists. If any applicable row is missing, return a corrected complete test set, not action accept. Construct independent input/expected integer literals via actual Rust primitive literals or the numeric type's library parsing/construction API; do not compute expected results, or the mathematical test data, through functions of i2r_candidate such as candidate addition, conversion, or numeral helpers. Calls to candidate functions belong on the actual-under-test side. This avoids correlated constructor/arithmetic defects masking failures.'''


SYSTEM+=''' For fixed literals or constructor-valued data embedded in a source operation, include an independent concrete-content assertion derived from that source: check the literal values/fields or their source-defined numeric/string observation, not only length, prefix shape, equality between repeated halves, or another relational property. Derive positional/bit-field weights from the source selectors and conversion equations. Never use candidate literal builders, conversions, or other candidate helpers to compute the expected side; construct expected content independently. This applies only where the exact source contains such fixed data and preserves the original source input domain.'''

AUTHOR_GUIDANCE_POLICY='source-operation-applicable-batched-compact-obligations-v2'
COMPACT_AUTHOR_GUIDANCE="""Return the smallest complete test artifact covering every required row and this group's source-operation obligations. Reuse one concrete executing test for multiple obligation records only when it checks each claimed fact; retain distinct required edge cases. Numeric, generic, non-Clone/non-Ord and overflow requirements in the applicable instructions remain mandatory. Derive explicit expected values from source equations; never from candidate output. Use the supplied matching fixture framework instead of duplicating builders. Avoid redundant whole-program suites for other groups or optional variants before the complete required artifact. Concision never removes a required source page, case, assertion, obligation or actual execution. Return complete JSON, with brief source-basis notes."""
# Preserve the original specialist guidance verbatim; select it from the exact
# source operation/dependency identities rather than the case label or Rust code.
_ack_start=SYSTEM.index('For Ackermann,')
_ack_end=SYSTEM.index('Finite resource-aware test selection',_ack_start)
_bit_start=SYSTEM.index(' For numeric bit-operation helpers,')
_ACK_GUIDANCE=SYSTEM[_ack_start:_ack_end]
_bit_end=SYSTEM.index('Construct independent input/expected integer literals',_bit_start)
_BIT_GUIDANCE=SYSTEM[_bit_start:_bit_end]
_BASE_AUTHOR_SYSTEM=SYSTEM[:_ack_start]+SYSTEM[_ack_end:_bit_start]+' '+SYSTEM[_bit_end:]


def author_system(model,source_ids):
    import re
    entities=model.get('entities') if isinstance(model,dict) else None
    pending=list(source_ids or []);seen=set();unknown=not pending or not isinstance(entities,dict)
    while pending and not unknown:
        name=pending.pop()
        if not isinstance(name,str):unknown=True;break
        if name in seen:continue
        seen.add(name);entity=entities.get(name)
        if not isinstance(entity,dict):unknown=True;break
        dependencies=entity.get('dependencies',[])
        if not isinstance(dependencies,list) or (name.startswith('constant:') and 'dependencies' not in entity):unknown=True;break
        for dep in dependencies:
            if not isinstance(dep,str):unknown=True;break
            # Executable dependencies determine applicability. Missing builtin
            # type declarations (e.g. prop) are not unknown operations.
            if dep.startswith('constant:'):pending.append(dep)
    names=[n.lower() for n in seen]
    ack=unknown or any(re.search(r'(?:[.:])ack(?:ermann)?$',n) for n in names)
    bits=unknown or any(any(op in n for op in ('take_bit','drop_bit','push_bit')) for n in names)
    system=_BASE_AUTHOR_SYSTEM
    if ack:system+='\n'+_ACK_GUIDANCE
    if bits:system+='\n'+_BIT_GUIDANCE
    system+='\n'+COMPACT_AUTHOR_GUIDANCE+' Keep each obligation concise and traceable: one exact source ID, category, executing test name, compact concrete case and short equation/source-basis reference. Reuse one test across records only when it actually checks all claimed facts; never omit generic, non-Clone, private-helper or numeric cases to shorten output.'
    return system,{'policy':AUTHOR_GUIDANCE_POLICY,'specialist_guidance':(['ackermann'] if ack else [])+(['bit_operations'] if bits else []),
                   'fallback_all_guidance':unknown,'source_operation_closure_count':len(seen)}

def insert_tests(source,scope,wrapper):
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    if not isinstance(scope,list) or any(not isinstance(n,str) for n in scope):raise Failure('invalid_support_test','module must be an array of inline module names')
    data=source.encode();node=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
    for name in scope:
        matching=[c for c in node.named_children if c.type=='mod_item' and c.child_by_field_name('name') is not None and data[c.child_by_field_name('name').start_byte:c.child_by_field_name('name').end_byte].decode()==name]
        if len(matching)!=1 or matching[0].child_by_field_name('body') is None:raise Failure('invalid_support_test','Choose an existing inline module or the actual file of an external module',scope)
        node=matching[0].child_by_field_name('body')
    at=node.end_byte-1 if scope else len(data)
    return (data[:at]+wrapper.encode()+data[at:]).decode()


READING_REPLY_SCHEMA = 'Reply fields: reading_notes:{"EXACT_CURRENT_PAGE_ID":"specific source observation"}; request_pages:["EXACT_PAGE_ID"] only when requesting pages. source_reading_notes in this request is retained history, not the canonical reply field. Keep action/reason separate. Never change or shorten page IDs, hashes or part numbers.'


def normalize_source_reading_reply(reply, supplied, existing, path):
    """Recognize an exact history-field echo without inventing reading evidence."""
    if 'source_reading_notes' not in reply:return reply
    alias=reply['source_reading_notes']
    if 'reading_notes' in reply and reply['reading_notes']!=alias:
        raise Failure('invalid_reading_notes','Conflicting reading_notes and source_reading_notes; return one canonical exact-page observation map')
    if not isinstance(alias,dict):
        raise Failure('invalid_reading_notes','source_reading_notes alias must be an exact-page observation object')
    unexpected=set(alias)-(set(supplied)|set(existing))
    if unexpected:
        raise Failure('invalid_reading_notes','History-field alias contains pages outside the current supplied batch or verified prior notes; no identity is corrected',{'unexpected_page_ids':sorted(unexpected),'required_current_page_ids':sorted(supplied)})
    normalized={k:v for k,v in reply.items() if k!='source_reading_notes'}
    normalized['reading_notes']=alias
    save(path/'reading-reply-normalization.json',{'policy':'exact-current-or-verified-history-field-alias-v1','original_reply':reply,'normalized_reply':normalized,'current_page_ids':sorted(supplied),'verified_prior_page_ids':sorted(existing),'semantic_fields_unchanged':all(normalized.get(k)==v for k,v in reply.items() if k not in {'source_reading_notes','reading_notes'}),'not_semantic_acceptance':True})
    return normalized


def source_review(payload, source_pages, cfg, provider, directory, system=SYSTEM, failure_ledger=None):
    """Read exact pages independently for author and oracle reviewer."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    catalog={p['id']:p for p in source_pages};seen=set();stalled=0;turn=0;notes={}
    required={n for n,p in catalog.items() if p.get('required_for_group',True)}
    initial_limit=(sum(len(p['text']) for p in source_pages)+1 if payload.get('author_group',{}).get('policy')=='component-owned-batched-author-groups-scoped-context-v2' else cfg['segmented']['initial_source_characters'])
    material=read_pages(catalog,[n for n in catalog if n in required],initial_limit)
    conversation=Conversation(directory/'conversation.json',cfg)
    conversation.enter('source-contract')
    while True:
        turn+=1;step=directory/f'turn-{turn:04d}';step.mkdir(exist_ok=True)
        seen.update(p['id'] for p in material['pages'])
        request={**payload,'source_material':material,'read_pages':sorted(seen),'source_reading_notes':notes,
                 'page_catalog':[{k:v for k,v in p.items() if k!='text'} for p in source_pages],
                 'reading_protocol':'Read ALL exact source pages before returning tests or accepting. request_pages:[id,...] fetches bounded batches. Before moving to another batch, supply reading_notes:{page_id:"specific source facts/conditions/test expectations or unfinished fragment details"} for every current page. These notes persist across bounded conversations. Join ordered text parts for each entity.'}
        if payload.get('authoring_policy')=='source-author-only-v1':
            request['reading_protocol']=request['reading_protocol'].replace('returning tests or accepting','returning complete tests')
        if payload.get('author_group'):
            request['reading_protocol']='Read ALL required_for_group source pages before returning complete tests. Other exact dependency/type source pages are available through request_pages; read them whenever needed to determine source behavior or expectations. Dependency reading adds context, not test ownership. Supply reading_notes for current pages before requesting another batch. Join ordered text parts of an entity.'
        if payload.get('focused_binding_scope'):
            request['reading_protocol']='Read all required_for_group source pages before classification or binding repair. Exact other dependency/type, frozen-test and obligation pages are available via request_pages. Preserve specific reading_notes before changing pages. Compiler-selected artifact indices are global indices; optional reads do not grant edit permission.'
        request['reading_protocol']+=' '+READING_REPLY_SCHEMA
        text=audit_request(step/'audit.json',system,request)
        if not cfg.get('v8',{}).get('correctness_only') and len(text)+len(system)>cfg['segmented']['max_request_characters']:
            raise Failure('support_context_exceeded','Source-test interface/proposal exceeds context; explicit further partition is required',{'characters':len(text)+len(system),'limit':cfg['segmented']['max_request_characters'],'audit':str(step/'audit.json'),'scope':payload.get('focused_binding_scope',{}).get('policy')})
        ledger_path=Path(failure_ledger) if failure_ledger else directory/'length-failures.json'
        ledger=read(ledger_path) if ledger_path.exists() else {'limit':2,'states':{}}
        options=cfg['segmented'].get('support_author_model',{})
        effective_generation={**cfg['generation'],**options}
        request_state=fingerprint({'payload':{k:v for k,v in payload.items() if k!='prior_authoring_failure'},
            'system':system,'source_pages':source_pages,'supplied_pages':material['pages'],'read_pages':sorted(seen),
            'model':cfg['model'],'generation':effective_generation})
        failures=ledger['states'].get(request_state,[])
        if len(failures)>=2:
            raise Failure('support_output_budget_exhausted','Two length failures for unchanged source-test material; preserved partial responses are not executable tests',{'request_state':request_state,'failures':failures})
        group_state=fingerprint({'payload':{k:v for k,v in payload.items() if k!='prior_authoring_failure'},
            'system':system,'source_pages':source_pages,'model':cfg['model'],'generation':effective_generation})
        used=ledger.setdefault('group_attempts',{}).get(group_state,0)
        limit=cfg['segmented'].get('support_author_max_calls_per_group',0)
        if limit and used>=limit:
            raise Failure('support_author_budget_exhausted','Explicit author-group attempt limit reached',{'group_state':group_state,'attempted_calls':used,'limit':limit})
        ledger['group_attempts'][group_state]=used+1;save(ledger_path,ledger)
        try:reply=conversation.call(provider,system,request,step,phase='generation',options=options or None)
        except Failure as error:
            if error.code=='incomplete_response' and (error.evidence or {}).get('finish_reason')=='length':
                failures=failures+[{'step':str(step),'evidence':error.evidence}]
                ledger['states'][request_state]=failures;save(ledger_path,ledger)
                if len(failures)>=2:
                    raise Failure('support_output_budget_exhausted','Two length failures for unchanged source-test material; stop repeated full-budget authoring',{'request_state':request_state,'failures':failures}) from error
            raise
        save(step/'reply.json',reply)
        try:
            reply=normalize_source_reading_reply(reply,{p['id'] for p in material['pages']},notes,step)
            if reply.get('request_pages') or required-seen or 'reading_notes' in reply:
                notes=reading_notes(notes,reply,{p['id'] for p in material['pages']},catalog)
        except Failure as error:
            material['feedback']={'status':error.code,'message':str(error),'evidence':error.evidence};stalled+=1
            if stalled>=cfg['segmented']['no_progress_limit']:raise
            continue
        if reply.get('request_pages'):
            material=read_pages(catalog,reply['request_pages'],cfg['segmented']['initial_source_characters'])
            stalled=0 if {p['id'] for p in material['pages']}-seen else stalled+1
        elif required-seen:
            material=read_pages(catalog,[n for n in catalog if n in required-seen],cfg['segmented']['initial_source_characters'])
            material['feedback']='Previous completion was premature. Review the remaining exact source material.'
            stalled=0
        else:return reply
        if stalled>=cfg['segmented']['no_progress_limit']:raise Failure('support_no_progress','Repeated test-authoring reads without new source material')


def prepare(state,cfg,provider,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    from .source_test_context import bodyless_interfaces,canonical_mapping
    api=bodyless_interfaces(state)
    from .support_framework import build as build_framework,inject
    framework=build_framework(state) if cfg.get('v8',{}).get('correctness_only') else None
    author_only=bool(cfg.get('v8',{}).get('correctness_only'))
    v8=cfg['generation']['workflow']=='segmented-v8'
    implemented_exports=set(state['bundle']['source_model']['entries']) & {r['source'] for r in state['mapping'] if r.get('rust_item')}
    cache_api=api
    if cfg['generation']['workflow']=='segmented-v8':
        from .v8_identity import interfaces_for_cache
        cache_api=interfaces_for_cache(state['files'])
    identity_data={'prompt_policy':fingerprint({'system':SYSTEM,'protocol':'whole-program-source-contract-v2','author_only':author_only}),'authoring_policy':'source-author-only-v1' if author_only else 'source-author-reviewed-v1','test_binding_policy':'author-group-qualified-v1','author_guidance_policy':fingerprint([AUTHOR_GUIDANCE_POLICY,COMPACT_AUTHOR_GUIDANCE]),'author_model_options':cfg['segmented'].get('support_author_model',{}),'verified_groups':cfg['segmented'].get('verified_support_groups',[]),'source':state['bundle']['source_model'],'interfaces':cache_api,'config':state['rust_config'],'numeric_policy':state['bundle']['numeric_policy'],'test_framework':framework}
    if v8:identity_data['mapping']=canonical_mapping(state)
    identity_data['source_test_context_policy']='canonical-mapping-bodyless-api-v1'
    from .implementation_strategy import project,test_identity
    if v8:identity_data['strategy_conditions']=test_identity(state)
    from . import support_scope
    from . import support_batching
    author_plan=support_batching.apply(support_scope.plan(state,cfg),directory) if author_only else None
    if author_plan:identity_data['author_group_plan']=author_plan
    from .support_templates import build as build_templates
    templates=build_templates(state) if author_only else {'covered_sources':[],'identity':None}
    identity_data['source_contract_templates']=templates
    identity=fingerprint(identity_data)
    frozen=directory/(identity+'.json')
    if frozen.exists():return read(frozen)
    generation=max([int(p.name.rsplit('-',1)[-1]) for p in directory.glob(identity+'-generation-*') if p.is_dir()] or [0])+1
    stage=directory/f'{identity}-generation-{generation:04d}';stage.mkdir()
    ids=set(state['bundle']['source_model']['entries'])|{r['source'] for r in state['mapping']}
    if author_plan:groups=author_plan['groups']
    else:
        # Entity text is never cut; oversized requests are split into source groups.
        entities=[(n,readable(state['bundle']['source_model']['entities'][n])) for n in sorted(ids)]
        groups=[];group=[];size=0;limit=cfg['segmented']['initial_source_characters']
        for n,e in entities:
            length=len(json.dumps(e,ensure_ascii=False))
            if group and size+length>limit:groups.append(group);group=[];size=0
            group.append(n);size+=length
        if group:groups.append(group)
    tests=[];unit_tests=[];obligations=[];inherited_groups=[]
    if templates['covered_sources']:
        from .v8_support import validate_records,validate_obligations,requirements
        proposal=templates['proposal'];validate_records(proposal,state['bundle']['source_model']['entities']);validate_obligations(proposal,requirements(state,templates['covered_sources']))
        tests=[inject(proposal['test_source'],framework)];obligations=group_obligations(tests,[],proposal['obligations'])
    signatures={n:[r['signature'] for r in rs] for n,rs in api.items()}
    for i,group in enumerate(groups):
        planned_group=list(group)
        group=[n for n in group if n not in templates['covered_sources']]
        if not group:continue
        test_system,guidance=author_system(state['bundle']['source_model'],group)
        if not author_only:
            test_system+=' For review, return {action:"accept",review:"source-grounded checks of each expectation",obligations:[...]} or a corrected complete test_source with reasons.'
        payload={'task':'Generate independent tests','author_guidance':guidance,'all_exports':state['bundle']['source_model']['entries'],
            'rust_signatures':signatures,'mapping':canonical_mapping(state),'numeric_policy':state['bundle']['numeric_policy'],
            'available_source_ids':sorted(state['bundle']['source_model']['entities']),
            'rust_interfaces':api,'rust_config':state['rust_config'],'algorithm_policy':cfg['segmented']['algorithm_policy'],
            'prior_authoring_failure':state.get('feedback') if (state.get('feedback') or {}).get('status') in {'missing_support_verification','invalid_support_test','invalid_model_response','incomplete_response'} else None,
            'item_locations':{n:[{'file':r['file'],'scope':r['scope']} for r in rs] for n,rs in items(state['files']).items()},
            'dependencies':state['rust_config']['dependencies']}
        if cfg['generation']['workflow']=='segmented-v8':
            payload['strategy_test_focus']=project(state,group,testing=True)
            payload['expectation_rule']='Strategy conditions are untrusted test focus only. Derive expectations exclusively from source equations and numeric task constraints; never weaken frozen counterexamples or coverage requirements.'
            from .v8_support import requirements
            payload['coverage_requirements']=requirements(state,group)
            payload['obligation_protocol']={
                'executed_case_fields':['source','category','test_name','case','expected_basis'],
                'omission_fields':['source','category','disposition','source_basis','api_basis','expected_basis'],
                'omission_dispositions':{'not_applicable':'Independently justified exception to an applicable coverage row; never an executed success.', 'inaccessible':'Informational lack of a callable API; does not satisfy a required coverage row.'},
                'correction':'Return complete test_source/unit_tests/obligations when correcting any field. action:accept freezes the original proposal unchanged; fields attached to acceptance do not edit it.'}
            payload['test_scope']={'kind':'whole_program',
                'source_ids':group,'implemented_exports':sorted(implemented_exports),
                'pending_exports':sorted(set(state['bundle']['source_model']['entries'])-implemented_exports),
                'instruction':'Use provided source equations for expected values. Missing export implementations are incomplete coverage, never passing tests; retain exact source/API evidence.'}
            test_system+='\nV8 SOURCE-TEST CONTRACT: Preserve obligation_protocol and every coverage_requirements row. Every executing coverage row needs exact source, category, actual enabled test_name, case and independent expected_basis. category must match the required row, including when correcting tests. Explicit not_applicable omissions require source_basis, api_basis and expected_basis with exact source/API justification. Correcting code OR obligation metadata requires a complete replacement test_source/unit_tests/obligations object, not action:accept. Accept means the original proposal satisfies this same protocol unchanged. Never remove categories while improving test expectations. Explicit omission records need source/category/disposition/source_basis/api_basis/expected_basis, not a fabricated executing case or test_name. inaccessible records do not satisfy required coverage rows.\n'
            payload['task']+='; for every coverage_requirements row provide an executing test and obligation with exact source, category, test_name, case and expected_basis. category must match the row. If a row cannot apply under actual source/API conditions, explicitly use disposition:not_applicable, source_basis and api_basis; provide exact source/API facts for this omission; the controller validates the omission record and coverage obligations. Private visibility alone is not a valid omission. Do not invent tests for source types with no operation. Public-export coverage is required across the complete whole-program suite.'
        if author_only and framework:
            payload['test_framework']={k:v for k,v in framework.items() if k not in {'integration_source','unit_source'}}
            test_system+='\nThe controller supplies i2r_test_support scaffolding from test_framework.api to every test module. Use these functions for matching representations instead of reprinting builders/traversals. Do not redeclare i2r_test_support; author source-derived cases, fixed expected values and actual candidate calls. Scaffolding is not a test and does not satisfy any coverage obligation.\n'
        if author_only:
            test_system=test_system.replace(' Accept means the original proposal satisfies this same protocol unchanged.', '')
            test_system=test_system.replace('Correcting code OR obligation metadata requires a complete replacement test_source/unit_tests/obligations object, not action:accept.', 'Return the complete test_source/unit_tests/obligations object when correcting code or obligation metadata.')
            payload['authoring_policy']='source-author-only-v1'
            if 'obligation_protocol' in payload:
                payload['obligation_protocol']['correction']='Return complete test_source/unit_tests/obligations when correcting any field; all source cases and expected values remain source-derived.'
            test_system+='\nCORRECTNESS-ONLY SOURCE AUTHOR: derive fixed expected values from source equations only. Candidate bodies are withheld. Mechanical coverage/binding checks and real execution follow. Never change an expectation to match candidate output. Return complete tests and obligation metadata.\n'
        source_pages=support_scope.material(state['bundle']['source_model'],group,cfg['segmented']['source_page_characters']) if author_plan else pages(state['bundle']['source_model'],group,cfg['segmented']['source_page_characters'])
        if author_plan:
            test_system=test_system.replace('At least one #[test] must actually execute a public export.', 'Across the combined group suite, at least one #[test] must execute a public export; this group tests only its assigned operations.')
            test_system+='\nAUTHOR RESPONSIBILITY: this is one disjoint source-operation group, not a request to author the whole-program suite. Test assigned operations only, using other source pages and interfaces as dependencies. Do not retest other groups to satisfy a global public-export statement. Every required row assigned here remains mandatory.\n'
            payload['available_source_ids']=group
            payload['author_group']={'policy':author_plan['policy'],'plan_identity':author_plan['identity'],'index':i,'count':len(groups),
                'owned_source_ids':group,'instruction':'Author tests ONLY for assigned source operations and every assigned required row. Dependency definitions and full Rust interfaces remain available for context. Other groups own other operations; do not duplicate their test suites. Preserve numeric/generic requirements for this group. A source requirement is complete only after every group has authored and the combined immutable tests actually execute.'}
            payload['test_scope']['kind']='disjoint_source_operations'
            payload=support_scope.scope_payload(state,group,payload,api)
            payload['framework_executed_contracts']={'sources':templates['covered_sources'],'proofs':templates.get('proofs',[]),'instruction':'These immutable source-verified template tests are part of the final suite and will execute; do not duplicate them. All remaining owned operations and required rows remain your responsibility.'}
        original_scope=author_group_scope(state,payload,source_pages,test_system)
        inherited=verified_author_group(cfg,original_scope) if author_only else None
        if cfg['segmented'].get('support_author_model'):
            payload['author_model_options']=cfg['segmented']['support_author_model']
        scope=author_group_scope(state,payload,source_pages,test_system)
        cached=directory/'author-groups'/(scope+'.json')
        reply=inherited['chosen'] if inherited else read_author_group(cached,scope) if author_only else None
        if reply is None:
            try:
                reply=source_review(payload,source_pages,cfg,provider,stage/f'{i}-author',system=test_system,
                                    failure_ledger=directory/(identity+'-length-failures.json'))
            except Failure as error:
                if author_plan and support_batching.size_failure(error):
                    if support_batching.split(author_plan,planned_group,state,error,directory):
                        return prepare(state,cfg,provider,directory)
                    if error.code=='incomplete_response':
                        # Preserve the inherited two-length-attempt ledger for a
                        # genuine indivisible responsibility: accuracy first.
                        evidence={**(error.evidence or {}),'author_retry_instruction':
                            'One bounded author retry remains for this indivisible group. Emit the minimum complete test_source/unit_tests/obligations object; omit optional prose and repeated explanation. Reuse a test for multiple source obligations only where its actual assertions justify each claim. Preserve every required source/category, exact test binding, source-derived expectation, generic/numeric edge case and private-helper responsibility. Do not reduce coverage, change model/output limits, or return partial tests.'}
                        raise Failure(error.code,str(error),evidence) from error
                raise
        save(stage/f'{i}-proposal.json',reply)
        if author_only:
            chosen=reply
        else:
            payload.update(task='Review independent source expectations BEFORE candidate execution',proposal=reply)
            reviewed=source_review(payload,source_pages,cfg,provider,stage/f'{i}-reviewer',system=test_system)
            save(stage/f'{i}-review.json',reviewed)
            chosen=reply if reviewed.get('action')=='accept' and reviewed.get('review') else reviewed
        if cfg['generation']['workflow']=='segmented-v8':
            payload['strategy_test_focus']=project(state,group,testing=True)
            payload['expectation_rule']='Strategy conditions are untrusted test focus only. Derive expectations exclusively from source equations and numeric task constraints; never weaken frozen counterexamples or coverage requirements.'
            from .v8_support import validate_obligations,validate_records
            validate_records(chosen,state['bundle']['source_model']['entities'])
            if author_plan:support_scope.validate_owned(chosen,group)
            validate_obligations(chosen,payload['coverage_requirements'])
        code=chosen.get('test_source','')
        units=chosen.get('unit_tests',[])
        if not isinstance(units,list) or any(not isinstance(t,dict) or t.get('file') not in state['files'] or not isinstance(t.get('source'),str) or '#[test]' not in t['source'] for t in units):
            raise Failure('invalid_support_test','Unit tests must target existing Rust source files')
        if ('#[test]' not in code and not units) or not chosen.get('obligations'):
            raise Failure('missing_support_verification','Independent tests require executable tests and source-based obligations',chosen)
        if not v8 and any(not isinstance(o,dict) or o.get('source') not in state['bundle']['source_model']['entities'] or not o.get('case') or not o.get('expected_basis') for o in chosen['obligations']):
            raise Failure('missing_support_verification',
                'Every obligation needs source equal to EXACTLY ONE available_source_ids entry, a concrete case and independent expected_basis. '
                'Do not append equation indices, prose, semicolons or other IDs to source. Put related entities/equations in expected_basis, '
                'or emit separate obligation objects for each source ID. Preserve the independently derived expectations.',
                {'obligations':chosen['obligations'],'valid_source_ids':sorted(state['bundle']['source_model']['entities']),
                 'example':{'source':group[0],'case':'concrete input/branch','expected_basis':'source equation details and related IDs go here','test_name':'actual Rust test name'}})
        generated=[inject(code,framework)] if code else []
        units=[{**t,'source':inject(t['source'],framework,unit=True)} for t in units]
        bound=group_obligations(generated,units,chosen['obligations'],len(tests),len(unit_tests))
        if inherited:
            artifact=inherited['artifact']
            if generated!=artifact['tests'] or units!=artifact['unit_tests'] or bound!=artifact['obligations']:
                raise Failure('inherited_support_changed','Executed source-test artifact bytes/obligations changed')
            inherited_groups.append({'group':i,'source_artifact_identity':artifact['identity'],
                                     'verified_packet':inherited['packet_path'],'new_strategy_cache_hit':False})
        if author_only and not inherited and not cached.exists():
            save(cached,{'scope':scope,'chosen':chosen,'chosen_sha256':fingerprint(chosen),
                         'validated_origin':str(stage/f'{i}-proposal.json'),
                         'validated_origin_sha256':digest(stage/f'{i}-proposal.json')})
        tests+=generated;unit_tests+=units;obligations+=bound
    result={'identity':identity,'tests':tests,'unit_tests':unit_tests,'obligations':obligations,'interfaces':api,'authoring_evidence':str(stage),
        'inherited_executed_groups':inherited_groups,
        'test_framework':{k:v for k,v in framework.items() if k not in {'integration_source','unit_source'}} if framework else None,
        'status':'frozen_before_execution','authoring_policy':identity_data['authoring_policy'],
        'source_contract_templates':templates,'scope':'Source-grounded finite tests with mechanical obligations and actual execution; not a formal proof or all internal-operation coverage.'}
    if author_plan:result['author_group_plan']=author_plan
    save(frozen,result);return result


def passed_test_names(output):
    """Exact libtest pretty successes, including its expected-panic annotation."""
    import re
    return set(re.findall(r'^test ([\w:]+)(?: - should panic)? \.\.\. ok$',output,re.M))


def execute(frozen,crate,rc,cfg,executor,*,compile_only=False):
    directory=Path(crate)/'tests';directory.mkdir(exist_ok=True)
    for p in directory.glob('source_contract_*.rs'):p.unlink()
    for i,code in enumerate(frozen['tests']):
        (directory/f'source_contract_{i}.rs').write_text('#![forbid(unsafe_code)]\nmod __i2r_source_contract_'+str(i)+' {\n'+code+'\n}\n')
    originals={};binding_error=None
    try:
        for i,test in enumerate(frozen.get('unit_tests',[])):
            target=Path(crate)/test['file']
            if not target.is_file():raise Failure('support_interface_changed','Frozen test target no longer exists',test['file'])
            if target not in originals:originals[target]=target.read_text()
            wrapper='\n#[cfg(test)]\nmod __i2r_contract_'+str(i)+' {\n#![forbid(unsafe_code)]\n'+test['source']+'\n#[allow(unused_imports)]\nuse super::*;\n}\n'
            target.write_text(insert_tests(target.read_text(),test.get('module',[]),wrapper))
        compiled=executor.run(cargo_command(rc,cfg,'test',crate,'--release','--tests','--no-run'),timeout=cfg['budgets']['build_seconds'],check=False)
        record=executor.run(cargo_command(rc,cfg,'test',crate,'--release','--tests','--','--format=pretty'),timeout=cfg['testing']['process_timeout'],check=False) if compiled['status']=='passed' and not compile_only else compiled
    except Failure as error:
        if error.code not in {'invalid_support_test','support_interface_changed'}:raise
        binding_error=error
    finally:
        for target,text in originals.items():target.write_text(text)
    if binding_error:
        return {'status':'support_test_binding_failed','tests_passed':0,'frozen_identity':frozen['identity'],
                'diagnostic':str(binding_error),'binding_error':binding_error.evidence,'obligations':frozen['obligations'],
                'immutable_test_sources':frozen['tests'],'immutable_unit_tests':frozen.get('unit_tests',[])}
    if compile_only:
        bindings=required_test_bindings(frozen)
        missing=sorted(name for name,names in bindings.items() if len(names)!=1)
        return {'status':'support_test_compile_failed' if compiled['status']!='passed' else 'support_test_binding_failed' if missing else 'support_compiled',
            'compilation':compiled,'record':compiled,'tests_passed':0,'executed':False,'missing_required_tests':missing,
            'frozen_identity':frozen['identity'],'diagnostic':Path(compiled['stdout']).read_text()+Path(compiled['stderr']).read_text(),
            'obligations':frozen['obligations'],'immutable_test_sources':frozen['tests'],'immutable_unit_tests':frozen.get('unit_tests',[])}
    output=Path(record['stdout']).read_text()+Path(record['stderr']).read_text()
    import re
    count=sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed',output))
    executed=passed_test_names(output)
    bindings=required_test_bindings(frozen)
    missing=sorted(name for name,names in bindings.items() if len(names)!=1 or names[0] not in executed)
    from .source_suite_review import inventory
    missing=sorted(set(missing)|({r['id'] for r in inventory(frozen)}-executed))
    return {'missing_required_tests':missing,'executed_tests':sorted(executed),'status':'support_test_compile_failed' if compiled['status']!='passed' else 'support_coverage_missing' if record['status']=='passed' and missing else 'passed' if record['status']=='passed' and count>0 else 'support_contract_failed',
        'compilation':compiled,'record':record,'tests_passed':count,'frozen_identity':frozen['identity'],'diagnostic':output,
        'obligations':frozen['obligations'],'immutable_test_sources':frozen['tests'],
        'immutable_unit_tests':frozen.get('unit_tests',[])}


def required_test_bindings(frozen):
    """Resolve an obligation uniquely against frozen tests, including disabled ones."""
    import re
    from .segmented_contract import items
    tests=[]
    groups=[(code,[f'__i2r_source_contract_{i}']) for i,code in enumerate(frozen['tests'])]
    groups += [(row['source'],row.get('module',[])+[f'__i2r_contract_{i}']) for i,row in enumerate(frozen.get('unit_tests',[]))]
    for code,prefix in groups:
        for rows in items({'src/lib.rs':code}).values():
            for row in rows:
                if row['kind']=='function_item' and any(re.fullmatch(r'#\s*\[\s*test\s*\]',a) for a in row.get('attributes',[])):
                    relative='::'.join(row['module_scope']+[row['name']])
                    tests.append((relative,'::'.join(prefix+[relative])))
    return {o['test_name']:[full for relative,full in tests if o['test_name'] in {relative,full} or relative.endswith('::'+o['test_name'])]
            for o in frozen['obligations'] if o.get('test_name')}


def group_obligations(tests,unit_tests,obligations,test_offset=0,unit_offset=0):
    """Bind only within the original author group before combining independent groups.

    Fully qualified names must already match this group's actual wrapper. Never
    select a binding from execution results or accept ambiguous local short names.
    """
    group={'tests':['']*test_offset+tests,
           'unit_tests':[{'source':'','file':'','module':[]}]*unit_offset+unit_tests,
           'obligations':obligations}
    bindings=required_test_bindings(group)
    result=[]
    for obligation in obligations:
        row=dict(obligation)
        if row.get('test_name'):
            candidates=bindings[row['test_name']]
            if len(candidates)!=1:
                raise Failure('invalid_support_test_binding','Obligation must identify exactly one test in its own author group',
                              {'test_name':row['test_name'],'candidates':candidates})
            row['test_name']=candidates[0]
        result.append(row)
    return result


def author_group_scope(state,payload,source_pages,system):
    from copy import deepcopy
    payload=deepcopy(payload)
    for k in ['index','count','plan_identity']:payload.get('author_group',{}).pop(k,None)
    return fingerprint({'policy':'candidate-source-obligation-prompt-framework-v1',
        'candidate':{'files':state['files'],'mapping':state['mapping'],'rust_config':state['rust_config']},
        'payload':{k:v for k,v in payload.items() if k!='prior_authoring_failure'},
        'source_pages':source_pages,'system':system})


def read_author_group(path,scope):
    if not Path(path).exists():return None
    cached=read(path);origin=Path(cached['validated_origin'])
    if (cached['scope']!=scope or fingerprint(cached['chosen'])!=cached['chosen_sha256']
            or not origin.is_file() or digest(origin)!=cached['validated_origin_sha256']
            or read(origin)!=cached['chosen']):
        raise Failure('stale_support_group_cache','Validated author-group provenance changed',str(path))
    return cached['chosen']


def verified_author_group(cfg,scope):
    for ref in cfg['segmented'].get('verified_support_groups',[]):
        path=Path(ref['path'])
        if digest(path)!=ref['sha256']:raise Failure('stale_verified_support','Inherited group packet changed')
        packet=read(path)
        if packet['obligation_scope']!=scope:continue
        for name,expected in packet['files_sha256'].items():
            if digest(Path(name))!=expected:raise Failure('stale_verified_support','Inherited group provenance changed',name)
        artifact=read(packet['artifact']);execution=read(packet['execution'])
        if execution['status']!='passed' or execution['tests_passed']<1 or execution['frozen_identity']!=artifact['identity']:
            raise Failure('unverified_support_inheritance','Inherited tests lack executed passing evidence')
        return {'chosen':packet['chosen'],'artifact':artifact,'packet_path':str(path)}
    return None
