"""Typed, byte-exact provenance against the material actually supplied to checker."""
from copy import deepcopy
import json,re
from .common import Failure
from .task_context import fingerprint
POLICY='actual-input-typed-exact-citations-v1'
PROTOCOL={'id':'unique local label, e.g. e1; basis uses this exact label, never an implicit array position','kind':'source | interface | numeric_policy','source':'exact source ID, exact interface key, or numeric_policy','page_id':'optional exact current page ID; omit for an interface/numeric policy citation','quotes':['one or more separate exact contiguous excerpts; never concatenate disjoint source rules into one quote']}
GUIDANCE='Citation protocol: each source_evidence row needs one unique local id such as e1, and every basis entry must equal an explicitly declared id. page_id identifies an exact supplied page, not the local citation label. Use kind:source with an exact source ID for source equations/types; kind:interface with exact interfaces key for API facts only; kind:numeric_policy for the declared numeric policy. Copy quotes from actual supplied JSON page text, decoded source string fields, or interface signature/declaration. Separate disjoint quotations as quotes:[...]; never splice prose/rules into a fabricated excerpt. Interface citations justify binding/type/generic facts, never replace source evidence for expected values. Every checklist item must retain source-grounded evidence as well as any API evidence. Return edits only for test_wrong; omit edits otherwise.'

def error(message,evidence=None):raise Failure('source_suite_citation_protocol',message,evidence)

def catalog(material):
    records=[];pages={};groups={}
    for page in material['source']:
        pages[page['id']]=page;groups.setdefault(page['source'],[]).append(page)
        records.append({'kind':'source','source':page['source'],'reference':page['id'],'page_ids':[page['id']],'text':page['text']})
    # Decoded source fields are traced to their JSON path and exact supplying pages.
    # This handles backslash escaping without treating any rewritten quote as exact.
    for source,parts in groups.items():
        parts=sorted(parts,key=lambda p:p['part'])
        if len(parts)!=parts[0]['parts'] or [p['part'] for p in parts]!=list(range(1,len(parts)+1)):continue
        value=json.loads(''.join(p['text'] for p in parts))
        def visit(v,path):
            if isinstance(v,str):records.append({'kind':'source','source':source,'reference':source+'::json'+path,'page_ids':[p['id'] for p in parts],'text':v})
            elif isinstance(v,dict):
                for key,child in v.items():visit(child,path+'/'+key.replace('~','~0').replace('/','~1'))
            elif isinstance(v,list):
                for i,child in enumerate(v):visit(child,path+'/'+str(i))
        visit(value,'')
    for name,rows in material['interfaces'].items():
        for index,row in enumerate(rows):
            for field in ['signature','declaration']:
                if row.get(field):records.append({'kind':'interface','source':name,'reference':f'interface:{name}:{index}:{field}','page_ids':[],'text':row[field]})
    records.append({'kind':'numeric_policy','source':'numeric_policy','reference':'numeric_policy','page_ids':[],'text':json.dumps(material['numeric_policy'],ensure_ascii=False)})
    return records,pages

def normalize(proposal,material):
    if not isinstance(proposal,dict):error('Citation reply must be an object')
    evidence=proposal.get('source_evidence')
    if not isinstance(evidence,list) or not evidence:error('source_evidence must be a nonempty array')
    records,pages=catalog(material);sources={r['source'] for r in records};out=deepcopy(proposal);seen={};proof=[]
    for index,row in enumerate(out['source_evidence']):
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id']:error('Each citation needs an explicit nonempty local id',{'index':index})
        label=row['id'];source=row.get('source');page_id=row.get('page_id')
        # Legacy exact page IDs carry real provenance; resolving their source is
        # deterministic. They do NOT imply e1/e2 labels or repair duplicate IDs.
        if label in pages and not source:source=pages[label]['source'];page_id=label
        elif '#' in label and label not in pages:error('Unknown exact page ID; no hash correction',{'index':index,'id':label})
        if isinstance(source,str) and source in pages:page_id=source;source=pages[source]['source']
        if page_id is not None and (not isinstance(page_id,str) or page_id not in pages):error('Unknown exact page_id; no fuzzy matching',{'index':index,'page_id':page_id})
        if not isinstance(source,str) or source not in sources:error('Citation source is absent from the actual supplied material',{'index':index,'source':source})
        if page_id and pages[page_id]['source']!=source:error('Page/source mismatch',{'index':index})
        kind='source' if source in {p['source'] for p in pages.values()} else 'numeric_policy' if source=='numeric_policy' else 'interface'
        if row.get('kind',kind)!=kind:error('Typed citation kind does not match its exact origin',{'index':index,'expected_kind':kind})
        quotes=row.get('quotes') if 'quotes' in row else [row.get('quote')]
        if ('quotes' in row and 'quote' in row) or not isinstance(quotes,list) or not quotes or any(not isinstance(q,str) or not q for q in quotes):error('Use quote or nonempty quotes, never both',{'index':index})
        matches=[]
        for q in quotes:
            found=[r for r in records if r['source']==source and r['kind']==kind and (not page_id or page_id in r['page_ids']) and q in r['text']]
            if not found:error('Quote is not one exact contiguous actual-input excerpt; use separate quotes for disjoint rules',{'index':index,'source':source,'quote':q,'page_id':page_id})
            matches.append({'quote':q,'origins':[{'reference':r['reference'],'text_sha256':fingerprint(r['text']),'page_ids':r['page_ids'],'start':r['text'].index(q),'end':r['text'].index(q)+len(q)} for r in found]})
        row.update(source=source,kind=kind)
        if page_id:row['page_id']=page_id
        if label in seen:error('Duplicate citation local ID; never infer e labels from array positions',{'id':label,'indices':[seen[label],index]})
        seen[label]=index;proof.append({'id':label,'kind':kind,'source':source,'matches':matches})
    for field in ['tests','obligations']:
        for row in proposal.get(field,[]):
            basis=row.get('basis') if isinstance(row,dict) else None
            if not isinstance(basis,list) or not basis or any(not isinstance(b,str) or b not in seen for b in basis):error('Checklist basis has unresolved explicit citation labels',{'field':field,'id':row.get('id') if isinstance(row,dict) else None,'basis':basis,'declared_ids':list(seen)})
            if not any(out['source_evidence'][seen[b]]['kind']=='source' for b in basis):error('API/policy citations alone cannot replace source grounding of a checklist item',{'field':field,'id':row['id'],'basis':basis})
    return out,{'policy':POLICY,'actual_input_sha256':fingerprint(material),'original_evidence':proposal['source_evidence'],'resolved_evidence':out['source_evidence'],'citations':proof,'semantic_manifest_unchanged':all(out.get(k)==proposal.get(k) for k in proposal if k!='source_evidence')}
