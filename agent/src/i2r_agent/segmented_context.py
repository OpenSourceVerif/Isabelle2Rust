"""Unit-scoped source/Rust context, including explicit oversized-entity pages."""
from copy import deepcopy
import json
from pathlib import Path
from .common import ROOT, Failure, save, read
from .task_context import fingerprint, register
from .program_model import readable
from .context import audit_request
from .segmentation import graph, project_functions, partition
from .segmented_config import rust_config
from .knowledge import requested


def pages(model, ids, size):
    out=[]
    for n in sorted(set(ids)):
        if n not in model['entities']:continue
        text=json.dumps(readable(model['entities'][n], model),ensure_ascii=False)
        key=fingerprint(text)[:10]
        chunks=[text[i:i+size] for i in range(0,len(text),size)] or ['{}']
        for i,chunk in enumerate(chunks):
            out.append({'id':n+'#'+key+':'+str(i+1), 'source':n,
                'part':i+1,'parts':len(chunks),'text':chunk,
                'notice':'Exact JSON text segment; join ordered parts to reconstruct full entity.'})
    return out


def read_pages(page_map, requested_ids, limit):
    if not isinstance(requested_ids,list) or any(not isinstance(n,str) or not n for n in requested_ids):
        raise Failure('invalid_page_request','request_pages must be a JSON array of exact nonempty page-ID strings, not page objects, a map or a single string',{'reply_shape':{'request_pages':['EXACT_CATALOG_PAGE_ID']},'available_page_ids':list(page_map)})
    unknown=set(requested_ids)-page_map.keys()
    if unknown:raise Failure('unknown_page','Unknown source pages',sorted(unknown))
    selected=[];size=0
    for n in dict.fromkeys(requested_ids):
        page=page_map[n]
        if selected and size+len(page['text'])>limit:break
        selected.append(page);size+=len(page['text'])
    supplied={p['id'] for p in selected}
    return {'pages':selected,'pending_pages':[n for n in requested_ids if n not in supplied]}


def reading_notes(existing, reply, supplied, catalog, *, quarantine_path=None):
    notes=reply.get('reading_notes',{})
    if not isinstance(notes,dict):
        raise Failure('invalid_reading_notes','reading_notes must be an object keyed by exact page IDs',
                      {'received_type':type(notes).__name__,'required_current_page_ids':sorted(supplied)})
    unknown=set(notes)-set(catalog)
    invalid=[k for k,v in notes.items() if not isinstance(v,str) or not v.strip()]
    # A malformed source-page identity is never reclassified as commentary.
    unbound_pages={k for k in unknown if k.startswith(('constant:','class:','type:'))}
    exact={k:v for k,v in notes.items() if k in catalog and k not in invalid}
    merged={**existing,**exact};missing=set(supplied)-set(merged)
    evidence={'unknown_note_keys':sorted(unknown),'missing_exact_page_ids':sorted(missing),
              'invalid_note_values':sorted(invalid),'unbound_source_page_keys':sorted(unbound_pages),'required_current_page_ids':sorted(supplied),
              'instruction':'Return reading_notes as an object keyed by complete page IDs including hash and part. Every value must be a nonempty source-specific STRING, not an object or list. Retain every required current page; never infer an alias or merge distinct pages.'}
    if invalid or unbound_pages or (unknown and (missing or quarantine_path is None)):
        raise Failure('invalid_reading_notes','Invalid note keys/values or missing exact-page evidence; no key is corrected or fuzzy-matched',evidence)
    if missing:
        raise Failure('missing_reading_notes','Before replacing pages, retain source-specific observations for every exact current page',evidence)
    commentary=reply.get('reading_commentary')
    if quarantine_path is not None and (unknown or commentary is not None):
        save(quarantine_path,{'status':'non_evidence_annotations_quarantined',
            'unknown_key_annotations':{k:notes[k] for k in sorted(unknown)},'reading_commentary':commentary,
            'used_as_reading_evidence':False,'required_current_page_ids':sorted(supplied),
            'accepted_exact_note_ids':sorted(exact),'catalog_identity':fingerprint(sorted(catalog)),
            'rule':'All required exact-page observations were already valid; annotations do not establish reading and never repair a missing page identity.'})
    return merged


def advance_source_reading(existing,reply,supplied,page_map,limit,feedback,path):
    notes=reading_notes(existing,reply,supplied,page_map,quarantine_path=path/'non-evidence-reading-annotations.json')
    material=read_pages(page_map,reply['request_pages'],limit)
    # Only a successful notes+page transition resolves these precise errors.
    # Unrelated source, grouping or protocol failures remain visible.
    if feedback and (feedback.get('status') in {'invalid_reading_notes','missing_reading_notes','invalid_page_request'} or
                     (feedback.get('status')=='incomplete_analysis' and isinstance(feedback.get('evidence'),dict) and
                      feedback['evidence'].get('kind')=='source_page_reading')):
        save(path/'resolved-reading-feedback.json',{'status':'resolved_by_exact_page_notes_and_valid_page_request','previous_feedback':feedback})
        feedback=None
    return notes,material,feedback


def page_reading_failure(code,message,page_map,seen,supplied,progress):
    """Explain the output protocol without trusting model-supplied page content."""
    missing=sorted(set(page_map)-seen)
    repeats=progress.get('repetitions',0)+1 if progress.get('missing_page_ids')==missing else 1
    progress.update(missing_page_ids=missing,repetitions=repeats)
    return Failure(code,message,{'kind':'source_page_reading','missing_page_ids':missing,
        'required_current_page_ids':sorted(supplied),'same_missing_pages_repetitions':repeats,
        'instruction':'Return top-level request_pages:["EXACT_CATALOG_PAGE_ID",...] and reading_notes:{"EXACT_CURRENT_PAGE_ID":"nonempty source-specific observation"}. requested_material.pages is controller input, not a reply action. Do not return page text or page objects; only the controller supplies source text. Copy complete IDs including hash and part. No final analysis is accepted while pages remain unread.',
        'next_action':'correct_page_request_only' if repeats>=2 else 'request_unread_pages'})


def reject_page_reply_alias(reply,page_map,seen,supplied,progress):
    material=reply.get('requested_material')
    if isinstance(material,dict) and 'pages' in material:
        raise page_reading_failure('invalid_page_request',
            'requested_material.pages cannot request source pages; use top-level request_pages',
            page_map,seen,supplied,progress)


def code_pages(files,size):
    result=[]
    for name,text in sorted(files.items()):
        key=fingerprint(text)[:10]
        chunks=[text[i:i+size] for i in range(0,len(text),size)] or ['']
        for i,chunk in enumerate(chunks):
            result.append({'id':name+'#'+key+':'+str(i+1),'file':name,'part':i+1,'parts':len(chunks),'text':chunk})
    return result


def ask(provider,cfg,path,payload,analysis=False):
    path=Path(path);path.mkdir(parents=True,exist_ok=True)
    analysis_prompt='translation-correctness-analysis.txt' if cfg.get('translation',{}).get('correctness_only') else 'translation-semantic-analysis.txt' if cfg.get('translation',{}).get('unit_policy')=='semantic-components' else 'segmented-analysis.txt'
    system=(ROOT/'prompts'/analysis_prompt).read_text() if analysis else ''
    if cfg['generation']['workflow']=='source-translation':
        if analysis:
            system+='\nReturn semantic_obligations:[{source,operation,rust_representation,conditions,boundary_cases,verification}] for important numeric, generic and representation choices. Use exact source IDs. Conditions and checks must be concrete; analysis remains revisable. Source optimization is disabled.\n'
            from .semantic_components import enabled
            if enabled(cfg):
                system+='\nReturn adaptation boundaries and components together in this global-analysis reply. Apply the SAME reply\'s explicit boundaries together with use_default_adaptations and revoke_default_adaptations before grouping. Own only the resulting reachable adapted closure, including retained adapted operations and their required type/class signature dependencies, exactly once. Classifying an entity in analysis_coverage or listing an unused adaptation does not require owning it. Feedback required_ids is scoped to its effective_boundaries_identity/default_adaptation_decision; changing any boundary/default choice invalidates that previous list. Never copy prior required_ids after changing those choices. Never split an SCC or introduce a cycle between groups. component_grouping describes the inclusive small-program limits; the controller deterministically uses one complete group only when both limits hold. Within both limits, components may be omitted; if uncertain supply them now. Otherwise components:[{name,purpose,members:[exact source IDs]}] is mandatory in this reply. A failed grouping receives feedback in this same analysis conversation; no separate planning call follows. A type class need not become an empty Rust trait, but its source capabilities and polymorphism remain obligations.\n'
        else:
            phase=payload['controller_state']['phase']
            topic='repair' if phase=='repair' else 'performance' if phase=='performance_review' else 'generate' if phase=='generate' else 'review'
            system=(ROOT/'prompts/translation-common.txt').read_text()+'\n'+(ROOT/'prompts'/('translation-'+topic+'.txt')).read_text()
        if cfg.get('translation',{}).get('correctness_only'):
            system=system.replace('only when both limits hold. Within both limits', 'when the entity-count limit holds; source-character size is advisory only. Within that entity-count limit')
        if cfg.get('testing',{}).get('reference_policy')=='available-per-input-v1':
            system+='\nREFERENCE AVAILABILITY: Execute all declared source tests and all fixed/generated ordinary/kernel inputs. Compare each input with every available executed reference; reference build/runtime failures are reported separately and do not authorize changing inputs, expected source-test assertions or semantics. If no reference succeeds for an input, report differential unavailable, never equivalence or passed differential. Do not repair an algorithm merely because a reference is unavailable.\n'
        if cfg.get('translation',{}).get('correctness_only'):
            system+='\nCORRECTNESS-ONLY: Do not review, measure, profile or optimize performance. Choose ordinary faithful Rust representations. Revise strategy only for implementation or correctness. Per-component stages are generation, mapping/coverage checks and cumulative compilation only. No routine unit or whole-program LLM review is requested; do not author or execute early semantic/support tests. After whole-program assembly and compilation, retain source-only test authorship, fixed expectations, mechanical coverage, actual execution, ordinary/kernel reference checks and original-failure repair replay. No independent final-test stage exists.\n'
        payload={**payload,'reference_catalog':[r for r in __import__('i2r_agent.task_context',fromlist=['reference_catalog']).reference_catalog() if not r['path'].endswith('isabelle-syntax.md')]}
        save(path/'guidance-manifest.json',{'workflow':'source-translation','phase':'analysis' if analysis else phase,'system_sha256':fingerprint(system),'skill_bodies':[], 'references_supplied':list(payload.get('targeted_references',{}))})
    if not analysis and payload['controller_state']['phase']=='whole_review':
        system+='\nYou are the independent whole-program reviewer in a separate conversation from generation. Treat global analysis and prior acceptance as untrusted suggestions. Compare actual source equations and Rust bodies, especially algorithm_routes; reject closed-form substitution, memoization absent from the source, alternate sorting/search/sqrt algorithms, or test-specialized tables. Mathematical equivalence alone does not authorize a business algorithm change. Patch back to the source route before accepting.\n'
    # Deliberately do not append legacy workflow instructions. References are
    # still requestable, but this workflow's phase and numeric policies prevail.
    text=audit_request(path/'context-audit.json',system,payload)
    if not cfg.get('translation',{}).get('correctness_only') and len(text)+len(system)>cfg['segmented']['max_request_characters']:
        raise Failure('context_budget_exceeded','Requested context is too large; use paged reads',{'characters':len(text)})
    save(path/'input.json',payload)
    from .task_context import Conversation
    scope=payload.get('task_kind','analysis') if analysis else payload['controller_state']['phase']+':'+str(payload['controller_state'].get('unit'))
    conversation=Conversation(path.parent/'conversations'/(fingerprint(scope)+'.json'),cfg)
    conversation.enter(scope)
    reply=conversation.call(provider,system,payload,path,phase='preprocessing' if analysis else 'generation',
                            options=cfg['preprocessing'].get('model') if analysis else None)
    if not isinstance(reply,dict):raise Failure('invalid_model_response','Expected a JSON object')
    save(path/'reply.json',reply);return reply


def validate_semantic_obligations(obligations,model):
    fields=['operation','rust_representation','conditions','boundary_cases','verification']
    if not isinstance(obligations,list) or not obligations:
        raise Failure('missing_semantic_obligations','Provide a nonempty concrete source-linked semantic_obligations array',
                      {'field':'semantic_obligations','received_type':type(obligations).__name__})
    invalid=[]
    for i,row in enumerate(obligations):
        if not isinstance(row,dict):invalid.append({'index':i,'invalid_row_type':type(row).__name__});continue
        missing=[k for k in fields if not row.get(k)]
        unknown=row.get('source') not in model['entities']
        if missing or unknown:invalid.append({'index':i,'source':row.get('source'),'missing_or_empty_fields':missing,'unknown_source_id':unknown})
    if invalid:raise Failure('missing_semantic_obligations','Concrete source-linked semantic obligations have invalid rows; repair the listed fields without deleting responsibilities',
                            {'invalid_rows':invalid,'required_nonempty_fields':fields})


def analyze(bundle,cfg,provider,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    register(bundle,directory/'materials')
    model=bundle['source_model'];g=graph(model)
    from .repair_knowledge import semantic
    adaptation_knowledge=semantic(model,bundle['numeric_policy'])
    from .default_adaptations import proposals as primitive_defaults,apply as apply_defaults
    default_adaptations=primitive_defaults(model,bundle['numeric_policy']) if cfg.get('translation',{}).get('correctness_only') else []
    all_pages=pages(model,g['edges'],cfg['segmented']['source_page_characters'])
    page_map={p['id']:p for p in all_pages};seen=set();extra={};feedback=None;notes={}
    initial=[];used=0
    for p in all_pages:
        if used+len(p['text'])>cfg['segmented']['initial_source_characters']:break
        initial.append(p);used+=len(p['text'])
    tries=max([int(p.name.rsplit('-',1)[-1]) for p in directory.glob('analysis-[0-9]*') if p.is_dir()] or [0])
    stalled=0;length_failures={};draft=None;page_stall={}
    analysis_prompt='translation-correctness-analysis.txt' if cfg.get('translation',{}).get('correctness_only') else 'translation-semantic-analysis.txt' if cfg.get('translation',{}).get('unit_policy')=='semantic-components' else 'segmented-analysis.txt'
    resume_scope=fingerprint({'source_model':model,'numeric_policy':bundle['numeric_policy'],'config':cfg,
                              'default_adaptations':default_adaptations,'protocol':'analysis-state-v1',
                              'prompt':(ROOT/'prompts'/analysis_prompt).read_text(),'context_protocol':Path(__file__).read_text(),
                              'source_pages_identity':fingerprint(all_pages)})
    checkpoint=directory/'analysis-state.json'
    if checkpoint.exists():
        state=read(checkpoint)
        if state.get('scope')!=resume_scope or state.get('integrity')!=fingerprint({k:v for k,v in state.items() if k!='integrity'}):
            raise Failure('analysis_resume_mismatch','Analysis state is not bound to this exact source/config or its bytes changed')
        all_pages=state['all_pages'];page_map={p['id']:p for p in all_pages}
        if any(p not in page_map for p in state['seen']) or any(p not in page_map for p in state['notes']):
            raise Failure('analysis_resume_mismatch','Saved reading state names unavailable exact pages')
        seen=set(state['seen']);notes=state['notes'];extra=state['extra'];initial=state['initial'];feedback=state['feedback']
        tries=state['next_attempt']-1;stalled=state['stalled'];length_failures=state['length_failures'];draft=state['unvalidated_current_proposal']
        page_stall=state.get('page_stall',{})
    while True:
        tries+=1;path=directory/f'analysis-{tries:04d}'
        state={'schema':1,'scope':resume_scope,'next_attempt':tries,'all_pages':all_pages,'seen':sorted(seen),
               'notes':notes,'extra':extra,'initial':initial,'feedback':feedback,'stalled':stalled,'length_failures':length_failures,'unvalidated_current_proposal':draft,'page_stall':page_stall}
        save(checkpoint,{**state,'integrity':fingerprint(state)})
        payload={'task':'Global semantic adaptation and boundary selection for '+cfg['generation']['workflow'],
            'algorithm_policy':cfg['segmented']['algorithm_policy'],
            'numeric_policy':bundle['numeric_policy'],'toolchain':cfg['tools']['rust_toolchain'],'build_environment':cfg.get('_runtime_environment',{}),
            'entries':model['entries'],'mandatory_functions':sorted(project_functions(model)),
            'executable_graph':g,'source_pages':initial,'adaptation_knowledge':adaptation_knowledge,
            'default_adaptations':default_adaptations,
            'page_catalog':[{k:v for k,v in p.items() if k!='text'} for p in all_pages],
            'reading_protocol':'request_pages:[page_id,...] reads exact source segments. All pages must be read before analysis completion.',
            'read_pages':sorted(seen),'source_reading_notes':notes,'requested_material':extra,'feedback':feedback,
            'unvalidated_current_proposal':draft}
        if page_stall.get('repetitions',0)>=2 and feedback and isinstance(feedback.get('evidence'),dict) and feedback['evidence'].get('kind')=='source_page_reading':
            payload['task']='Correct only the source-page request protocol; the same unread-page set has repeated. Do not repeat a final analysis or requested_material.pages.'
            payload['reading_protocol']='Reply with request_pages:[exact unread catalog IDs] and reading_notes:{exact current page ID: nonempty observation}. Use feedback.evidence.missing_page_ids and feedback.evidence.required_current_page_ids. Source text is supplied only by the controller.'
        from .semantic_components import enabled,grouping_policy,grouping_context,from_analysis
        if enabled(cfg):
            payload['component_grouping']={'mode':'joint_analysis','limits':grouping_policy(cfg),
                'metric':'Count the actual adapted dependency closure including owned adapted helpers and required types/classes; sum full readable source characters without truncation.',
                'rule':'Both inclusive limits permit deterministic single-group ownership. Otherwise return components with boundaries in this same reply; exactly one owner per required entity, no split SCC and no group dependency cycle. All source pages still must be read.'}
            if cfg.get('translation',{}).get('correctness_only'):
                payload['component_grouping']['rule']='Entity-count policy permits deterministic single-group ownership; source-character size is advisory only. Otherwise return components with exact ownership and dependency rules. Every required source page must still be read.'
        try:
            reply=ask(provider,cfg,path,payload,True)
            supplied={p['id'] for p in initial+extra.get('pages',[])}
            seen.update(supplied)
            reject_page_reply_alias(reply,page_map,seen,supplied,page_stall)
            if reply.get('request_pages'):
                notes,extra,feedback=advance_source_reading(notes,reply,supplied,page_map,
                    cfg['segmented']['initial_source_characters'],feedback,path)
                supplied={p['id'] for p in extra['pages']}
                if supplied-seen:page_stall={}
                stalled=0 if supplied-seen else stalled+1
                if stalled>=cfg['segmented']['no_progress_limit']:raise Failure('analysis_no_progress','Repeated source reads without new material')
                initial=[];continue
            draft=reply
            additions=requested(reply,bundle)
            if additions:extra=additions;initial=[];continue
            if set(page_map)-seen:raise page_reading_failure('incomplete_analysis','Read remaining source pages',page_map,seen,supplied,page_stall)
            if not isinstance(reply.get('opportunities'),list):raise Failure('invalid_analysis','opportunities must be a list')
            if set(g['edges'])-set(reply.get('analysis_coverage',[])):raise Failure('incomplete_analysis','Classify every executable entity',sorted(set(g['edges'])-set(reply.get('analysis_coverage',[]))))
            if cfg['generation']['workflow']=='source-translation':
                validate_semantic_obligations(reply.get('semantic_obligations'),model)
            boundaries,default_decision=apply_defaults(reply,default_adaptations)
            reply={**reply,'boundaries':boundaries,'default_adaptation_decision':default_decision}
            if enabled(cfg):
                try:context=grouping_context(model,boundaries,cfg)
                except Failure as error:
                    if error.code!='invalid_partition':raise
                    reachable=set(g['edges'])
                    invalid=[{'index':i,'source':row.get('source'),'not_reachable':row.get('source') not in reachable}
                             for i,row in enumerate(boundaries) if isinstance(row,dict) and row.get('source') not in reachable]
                    raise Failure(error.code,str(error),{'validation':error.evidence,'invalid_boundary_rows':invalid,
                        'exact_reachable_source_ids':sorted(reachable),'default_adaptation_decision':default_decision,
                        'instruction':'Use exact reachable source IDs; no typo, hash or alias is automatically corrected.'}) from error
                required={r['source'] for r in context['required_entities']}
                additional=[p for p in pages(model,required,cfg['segmented']['source_page_characters']) if p['id'] not in page_map]
                if additional:
                    all_pages.extend(additional);page_map.update({p['id']:p for p in additional})
                    raise Failure('incomplete_analysis','Read newly retained adapted type/class dependency pages before completing joint analysis',[p['id'] for p in additional])
                if required-set(reply.get('analysis_coverage',[])):
                    raise Failure('incomplete_analysis','Classify every entity retained by adapted dependency closure',sorted(required-set(reply.get('analysis_coverage',[]))))
                plan=from_analysis(model,boundaries,reply.get('components'),cfg,default_decision)
            else:plan=partition(model,boundaries)
            rc=rust_config(reply.get('rust_config',{}),cfg)
            bundle={**bundle,'semantic_analysis':reply,'segmentation':plan,'rust_config':rc}
            from .implementation_strategy import initialize
            bundle['implementation_strategy']=initialize(reply)
            save(directory/'analysis.json',reply);save(directory/'partition.json',plan)
            save(directory/'reading-evidence.json',{'read_pages':sorted(seen),'retained_source_notes':notes,'analysis_calls':tries,'separate_component_planning_calls':0})
            return bundle,{'status':'analyzed','units':len(plan['units']),'analysis':reply,'path':str(directory/'analysis.json')}
        except Failure as e:
            if e.code in {'provider_error','budget_exhausted','analysis_no_progress'}:raise
            if e.code=='context_budget_exceeded':extra={};initial=[]
            feedback={'status':e.code,'message':str(e),'evidence':e.evidence};save(path/'failure.json',feedback)
            if e.code=='incomplete_response' and (e.evidence or {}).get('finish_reason')=='length':
                request_state=fingerprint({'materials':{k:v for k,v in payload.items() if k!='feedback'},'config':cfg})
                repeated=length_failures.setdefault(request_state,[]);repeated.append(str(path/'failure.json'))
                save(directory/'length-failures.json',{'limit_per_same_material_state':2,'states':length_failures,'partial_policy':'Raw response preserved; no partial JSON accepted, source pages and semantic coverage unchanged.'})
                if len(repeated)>=2:
                    raise Failure('analysis_output_budget_exhausted','Two length-truncated responses for the same authoritative analysis material; stop instead of repeating full-budget requests',
                        {'request_state':request_state,'failures':repeated,'limit':2,'partial_policy':'unvalidated evidence only'}) from e
            stalled+=1
            if stalled>=cfg['segmented']['no_progress_limit']:
                raise Failure('analysis_no_progress','Global analysis has not produced a valid plan',feedback)
