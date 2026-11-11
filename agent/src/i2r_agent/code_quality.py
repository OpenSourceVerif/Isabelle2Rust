"""Concrete review leads, never automatic correctness/performance verdicts."""
import re
from .task_context import fingerprint


def findings(files):
    rules=[(r'\.remove\(\s*0\s*\)','front_shift','Repeated Vec front removal shifts the tail; inspect ordering and consider a local deque/iterator.'),
           (r'\.insert\(\s*0\s*,','front_insert','Repeated front insertion moves existing elements; inspect traversal and output order.'),
           (r'\[[^\]]*1\s*\.\.[^\]]*\]\.to_vec\(','tail_copy','Recursive tail rebuilding can copy the same elements repeatedly; inspect borrowed slices or consumption.'),
           (r'\.collect(?:::<[^;]+>)?\s*\(','iterator_collect','Collect consumes the remaining iterator. A collect after next inside a loop rebuilds the tail in linear work even if allocation is reused and no T is cloned. Source immutable-list head/tail decomposition is constant time. Check a persistent iterator/deque instead of recollecting each step.'),
           (r'\b\w+::cons\s*\(','list_cons','Inspect this support implementation: Vec-based cons may move the whole existing sequence, unlike constant-time source list cons. A local deque can preserve front insertion and scan order, with one conversion at the API boundary.'),
           (r'let\s+\w+\s*=\s*\w+\.clone\(\);','owned_copy','Check subsequent owner use: moving an otherwise unused owned value may avoid this copy.'),
           (r'\bas\s+(?:u(?:8|16|32|64)|i(?:8|16|32|64|128)|usize)\b','numeric_cast','Check mathematical range and sign before narrowing/casting, independently of test sample sizes.')]
    result=[]
    for name,text in files.items():
        for line,code in enumerate(text.splitlines(),1):
            if code.lstrip().startswith('//'):continue
            for pattern,kind,question in rules:
                if re.search(pattern,code):result.append({'id':fingerprint([name,line,kind])[:12],'file':name,'line':line,'kind':kind,'code':code,'question':question,'status':'review_lead_not_proven_defect'})
    return result


def validate_review(files,reply):
    """Require inspectable answers to structural leads, not a correctness verdict."""
    from .common import Failure
    structural={'front_shift','front_insert','tail_copy','iterator_collect','list_cons','owned_copy'}
    required=[x for x in findings(files)[:20] if x['kind'] in structural]
    rows=reply.get('quality_resolutions',[])
    answers={x.get('id'):x for x in rows if isinstance(x,dict)} if isinstance(rows,list) else {}
    missing=[x for x in required if not all(answers.get(x['id'],{}).get(k) for k in ['source_operation','source_cost','rust_cost','reason']) or answers.get(x['id'],{}).get('resolution') not in {'retain','not_applicable'}]
    if missing:
        raise Failure('incomplete_quality_review','Before unchanged acceptance, address each structural lead with quality_resolutions [{id,source_operation,source_cost,rust_cost,resolution:retain|not_applicable,reason}]. Otherwise return actual edits. These answers are judgments, not proof.',missing)
