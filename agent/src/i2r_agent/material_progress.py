"""Evidence-based stall accounting; content delivery is not the request action itself."""
import hashlib,json

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def snapshot(state):
    # Strategy prose and notes cannot disguise an unchanged implementation.
    mapping=[{k:r.get(k) for k in ('source','rust_item','kind')} for r in state.get('mapping',[]) ]
    bound=state.get('progress_page_contents',{})
    return {'candidate':digest({'files':state.get('files'),'mapping':mapping,'rust_config':state.get('rust_config')}),
            'notes':{bound[k] for k in set(state.get('reading_notes',{}))|set(state.get('evidence_reading_notes',{})) if k in bound}}

def material_contents(request):
    texts=set()
    def visit(value):
        if isinstance(value,dict):
            if isinstance(value.get('text'),str):texts.add(digest(value['text']))
            else:
                for k,v in value.items():
                    if k not in {'pending_pages','pending_code_pages','pending_evidence_pages','id','version','path','source','notice'}:visit(v)
        elif isinstance(value,list):
            for v in value:visit(v)
    visit(request.get('program',{}).get('source_pages',[]));visit(request.get('code_pages',[]));visit(request.get('requested_material',{}))
    extra=request.get('requested_material',{})
    for key in ('entities','nodes','uses'):
        for row in extra.get(key,[]):
            texts.add(digest({k:v for k,v in row.items() if k not in {'model_version','graph_version'}}))
    for key in ('materials','graphs','references'):
        value=extra.get(key,{})
        if isinstance(value,dict):
            for row in value.values():texts.add(digest(row))
    # File and page aliases with exactly the same bytes share a content identity.
    texts.update(digest(v) for v in request.get('current_files',{}).values() if isinstance(v,str))
    return texts

def delivered(state,request):
    bound=state.setdefault('progress_page_contents',{})
    for row in request.get('program',{}).get('source_pages',[])+request.get('code_pages',[])+sum([request.get('requested_material',{}).get(k,[]) for k in ('pages','code_pages','evidence_pages')],[]):
        if isinstance(row.get('text'),str):bound[row['id']]=digest(row['text'])
    current=material_contents(request);seen=set(state.get('progress_material_contents',[]));new=current-seen
    state['progress_material_contents']=sorted(seen|current)
    # Mark exact diagnostic page IDs actually present in the outgoing payload.
    state['seen_evidence_page_ids']=sorted(set(state.get('seen_evidence_page_ids',[]))|{p['id'] for p in request.get('requested_material',{}).get('evidence_pages',[])})
    return {'new_content_count':len(new),'new_content_sha256':sorted(new),'provided_content_count':len(current)}

def execution_evidence(attempt):
    # Stable outcomes rather than command timestamps/log paths. Repeated identical
    # failure of the same candidate/unit cannot manufacture verified progress.
    out={}
    for key in ('compilation','coverage','support_precompile','support_execution','support','replay','behavior','tests','testing','performance'):
        value=attempt.get(key)
        if isinstance(value,dict):
            out[key]={k:v for k,v in value.items() if k in {'status','tests_passed','passed','failed','executed','missing_required_tests','source_ids','failures','count'}}
    return out

def advance(state,before,attempt):
    status=attempt.get('development',{}).get('status');after=snapshot(state)
    rejected=bool(status and status not in {'material_requested','transaction_committed','passed','quality_reviewed'})
    candidate_changed=before['candidate']!=after['candidate']
    new_notes=after['notes']-before['notes']
    material_new=attempt.get('delivered_material',{}).get('new_content_count',0)
    execution=execution_evidence(attempt);seen=set(state.get('progress_execution_evidence',[]));key=digest([after['candidate'],attempt.get('unit'),execution]) if execution else None
    new_execution=key is not None and key not in seen
    if key:state['progress_execution_evidence']=sorted(seen|{key})
    advanced=candidate_changed or new_execution or (not rejected and bool(new_notes or material_new))
    state['no_progress']=0 if advanced else state.get('no_progress',0)+1
    return {'advanced':advanced,'candidate_changed':candidate_changed,'new_execution_evidence':new_execution,'new_valid_note_content_sha256':sorted(new_notes),'new_delivered_content':material_new,'rejected_response':rejected,'no_progress':state['no_progress']}
