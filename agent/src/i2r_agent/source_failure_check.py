"""One isolated semantic check, source-grounded expectation-only revisions."""
from copy import deepcopy
from pathlib import Path
import re,json
from .common import Failure,save,read
from .task_context import fingerprint,Conversation
from .segmented_contract import interfaces
from .segmented_context import pages
from .segmented_test_audit import invariants

SYSTEM='Check a failing source assertion independently from exact source equations. Candidate bodies and generation history are unavailable. Never use observed candidate output as an oracle. Return test_correct, inconclusive, or test_wrong with exact source citations and derivation. Only a proven incorrect expectation may be repaired. Preserve inputs, calls, assertions, test names and all coverage obligations.'

def lock(state):
    return fingerprint({k:state.get(k) for k in ['files','mapping','rust_config','implementation_strategy']})

def enforce_lock(state):
    if state.get('source_candidate_lock') and state['source_candidate_lock']!=lock(state):
        raise Failure('source_candidate_locked','Candidate changed after entering source validation')

def expected_spans(code,helper_context=None,state=None):
    """Locate second assert_eq/assert_ne argument using Rust token-tree nesting."""
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    data=code.encode();root=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
    if root.has_error:return []
    out=[];stack=[root]
    while stack:
        n=stack.pop();stack.extend(n.children)
        if n.type!='macro_invocation':continue
        text=data[n.start_byte:n.end_byte].decode()
        if not re.match(r'(?:\w+::)*assert_(?:eq|ne)!',text):continue
        body=next((c for c in n.children if c.type=='token_tree'),None)
        if body is None:continue
        commas=[c for c in body.children if c.type==',']
        if not commas:continue
        start=commas[0].end_byte;end=commas[1].start_byte if len(commas)>1 else body.end_byte-1
        raw=data[start:end];left=len(raw)-len(raw.lstrip());right=len(raw.rstrip())
        out.append((start+left,start+right,data[start+left:start+right].decode()))
    from .oracle_helpers import expected_spans as helper_spans
    return out+helper_spans(code,helper_context,state)

def closed_expected_literal(expression):
    """Conservative literal-only expectation. Never infer an oracle from position.

    Constructors/calls, identifiers, methods, casts and arbitrary macros remain
    unsupported for automatic revision; an unresolved verdict preserves tests.
    Array/tuple/reference literals and vec! of those literal values are safe.
    """
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    if not isinstance(expression,str) or not expression.strip():return False
    data=('fn __oracle(){let __expected = '+expression+';}').encode()
    root=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
    if root.has_error:return False
    def text(node):return data[node.start_byte:node.end_byte].decode()
    def safe(node):
        if node.type in {'integer_literal','float_literal','boolean_literal','char_literal','string_literal','raw_string_literal'}:return True
        if node.type in {'unary_expression','reference_expression','parenthesized_expression','array_expression','tuple_expression'}:
            return all(safe(child) for child in node.named_children)
        if node.type=='scoped_identifier':return bool(re.fullmatch(r'(?:[iu](?:8|16|32|64|128)|usize|isize)::(?:MAX|MIN)',text(node)))
        if node.type=='macro_invocation':
            spelling=text(node);m=re.fullmatch(r'vec!\s*([\[({])(.*)([\])}])',spelling,re.S)
            return bool(m) and closed_expected_literal('['+m.group(2)+']')
        return False
    lets=[n for f in root.named_children for block in f.named_children if block.type=='block' for n in block.named_children if n.type=='let_declaration']
    return len(lets)==1 and safe(lets[0].child_by_field_name('value'))


def protected_expected_pair(old,new,code,kind,state=None):
    """Closed literals, or unchanged unshadowed prelude constructors of literals.

    Constructor support is deliberately limited to standalone integration code;
    every possible local/import/macro binding of its name is conservatively
    rejected. A candidate call, nested call/input, or changed constructor stays
    unsupported. This does not infer expected/actual direction from position.
    """
    if closed_expected_literal(old) and closed_expected_literal(new):return True
    if kind!='integration':return False
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()))
    def constructor(expr):
        data=('fn __oracle(){let __expected = '+expr+';}').encode();root=parser.parse(data).root_node
        if root.has_error:return None
        stack=[root];values=[]
        while stack:
            n=stack.pop();stack.extend(n.children)
            if n.type=='let_declaration':values.append(n.child_by_field_name('value'))
        if len(values)!=1:return None
        n=values[0]
        if n.type!='call_expression':return None
        f=n.child_by_field_name('function');args=n.child_by_field_name('arguments');name=data[f.start_byte:f.end_byte].decode()
        if f.type!='identifier' or name not in {'Ok','Err','Some'} or len(args.named_children)!=1:return None
        arg=args.named_children[0]
        return name if closed_expected_literal(data[arg.start_byte:arg.end_byte].decode()) else None
    name=constructor(old)
    if not name or constructor(new)!=name:return False
    if state and any(n.rsplit('::',1)[-1]==name for n in interfaces(state['files'])):return False
    def unshadowed(text):
        data=text.encode();root=parser.parse(data).root_node
        if root.has_error or 'no_implicit_prelude' in text:return False
        stack=[root]
        while stack:
            n=stack.pop();spelling=data[n.start_byte:n.end_byte].decode()
            if n.type in {'macro_definition','extern_crate_declaration'}:return False
            if n.type=='use_declaration' and '*' in spelling:return False
            if n.type=='attribute_item' and not re.match(r'#\s*\[\s*(?:test|should_panic|cfg|allow)\b',spelling):return False
            if n.type=='macro_invocation':
                if not re.match(r'(?:assert_eq|assert_ne|assert|vec|panic)!',spelling):return False
                body=next((c for c in n.children if c.type=='token_tree'),None)
                if body is None:return False
                arguments=data[body.start_byte+1:body.end_byte-1].decode()
                # Macro arguments are token trees, not Rust expression ASTs.
                # Reparse as expressions before deciding that Ok is a call,
                # rather than overlooking a hidden let/pattern/import binding.
                if not unshadowed('fn __macro_args(){__args('+arguments+');}'):return False
                continue
            stack.extend(n.children)
            if n.type in {'identifier','type_identifier'} and spelling==name:
                parent=n.parent
                if parent.type!='call_expression' or parent.child_by_field_name('function')!=n:return False
        return True
    return unshadowed(code)


def exact_source_quote(entity,quote):
    if quote in json.dumps(entity,ensure_ascii=False) or quote in str(entity):return True
    todo=[entity]
    while todo:
        value=todo.pop()
        if isinstance(value,str) and quote in value:return True
        if isinstance(value,dict):todo.extend(value.values())
        elif isinstance(value,list):todo.extend(value)
    return False


def nonliteral_tokens(expression):
    """Keep the lexical guard, excluding complete Rust literal tokens.

    Parsing and protected_expected_pair still reject malformed or open
    expressions. Literal contents are data, never identifiers or syntax.
    """
    from tree_sitter import Language, Parser
    import tree_sitter_rust
    data=expression.encode();root=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
    output=bytearray(data);stack=[root]
    while stack:
        node=stack.pop()
        if node.type in {'string_literal','raw_string_literal','char_literal'}:
            output[node.start_byte:node.end_byte]=b' '*(node.end_byte-node.start_byte)
        else:stack.extend(node.children)
    return output.decode()


def revise(frozen,proposal,state,citation_material=None):
    entities=state['bundle']['source_model']['entities'];citations=proposal.get('source_evidence',[])
    if proposal.get('action')!='test_wrong' or not proposal.get('derivation') or not citations:
        raise Failure('source_check_unresolved','No established source-based test defect',proposal)
    if citation_material is not None:
        # Use the same exact actual-input catalog as the independent checker.
        # Readable source pages are a mechanical view, not raw entity JSON.
        from .source_check_citations import normalize
        normalized,_=normalize({'source_evidence':citations},citation_material)
        if any(r.get('kind')!='source' or r.get('source') not in entities for r in normalized['source_evidence']):
            raise Failure('source_check_unresolved','Expectation correction requires actual source citations')
        citations=[]  # Already validated by the canonical typed/page validator.
    for row in citations:
        entity=entities.get(row.get('source'))
        if entity is None or not row.get('quote') or not exact_source_quote(entity,row['quote']):
            raise Failure('source_check_unresolved','Citation is not an exact source excerpt',row)
    updated=deepcopy(frozen);edits=proposal.get('edits',[])
    if not edits:raise Failure('source_check_unresolved','Missing expectation correction')
    from .expectation_targets import plan
    for edit,span in plan(frozen,state,citation_material,edits):
        kind=edit.get('kind');index=edit.get('index');seq=updated['tests'] if kind=='integration' else updated.get('unit_tests',[]) if kind=='unit' else []
        if not isinstance(index,int) or not 0<=index<len(seq):raise Failure('source_check_unresolved','Invalid test index')
        code=seq[index] if kind=='integration' else seq[index]['source'];old=edit.get('old');new=edit.get('new')
        if code.encode()[span[0]:span[1]].decode()!=old:raise Failure('source_check_unresolved','Expected target changed during edit application')
        # Expectations must remain closed expressions: no candidate function calls,
        # macros except vec!, identifiers except primitive constructors/constants.
        if not isinstance(new,str) or not new or old==new:
            raise Failure('source_check_unresolved','Edit must identify exactly one complete expected argument')
        lexical=nonliteral_tokens(new)
        names=re.findall(r'\b[A-Za-z_]\w*\b',lexical)
        if any(n not in {'vec','Vec','new','Some','None','Ok','Err','true','false','MAX','MIN','u8','u16','u32','u64','u128','i8','i16','i32','i64','i128','usize','isize'} for n in names) or any(t in lexical for t in [';','{','}','unsafe','return']):
            raise Failure('source_check_unresolved','Expectation must be a closed literal/constructor expression')
        if not protected_expected_pair(old,new,code,kind,state):
            raise Failure('source_check_unresolved','Automatic correction requires both original and replacement to be closed literal expectations; candidate calls/inputs and reversed assertions are immutable')
        a,b,_=span;changed=(code.encode()[:a]+new.encode()+code.encode()[b:]).decode()
        before=invariants(code);after=invariants(changed)
        if any(before[k]!=after[k] for k in ['tests','ignored','bounds']) or len(before['assertions'])!=len(after['assertions']):
            raise Failure('source_check_unresolved','Test strength changed')
        if kind=='integration':seq[index]=changed
        else:seq[index]['source']=changed
    if proposal.get('obligations',frozen['obligations'])!=frozen['obligations']:
        raise Failure('source_check_unresolved','Obligations must remain complete and unchanged')
    updated.update(parent_identity=frozen['identity'],oracle_identity=frozen.get('oracle_identity',frozen['identity']),status='source_proven_expectation_revision_pending_execution',source_check=deepcopy(proposal))
    updated['identity']=fingerprint({'parent':frozen['identity'],'tests':updated['tests'],'unit_tests':updated.get('unit_tests',[]),'obligations':updated['obligations'],'source_check':proposal})
    return updated

def validate_scope(proposal,selected):
    allowed={(t['kind'],t['index']) for t in selected}
    for edit in proposal.get('edits',[]):
        if (edit.get('kind'),edit.get('index')) not in allowed or 'file' in edit:
            raise Failure('source_check_unresolved','Test edit lies outside exact failure-selected artifacts',edit)

def check(frozen,result,state,cfg,provider,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if result.get('status')!='support_contract_failed' or result.get('compilation',{}).get('status')!='passed' or 'panicked at' not in result.get('diagnostic',''):
        raise Failure('source_check_unresolved','Only executed assertion failures admit semantic checking')
    if cfg['model']['name']!='deepseek-flash':raise Failure('source_check_unresolved','Failure check requires Flash')
    diagnostic=result['diagnostic'];key=fingerprint([lock(state),frozen['identity'],diagnostic])
    ledger=directory.parents[1]/'semantic-check-ledger.json';seen=read(ledger) if ledger.exists() else {}
    from .test_order_policy import source_first
    if (key in seen if source_first(state) else bool(seen)):raise Failure('source_check_unresolved','Unchanged failure already checked',seen)
    seen[key]={'status':'reserved','path':str(directory)};save(ledger,seen)
    # Select only failing integration groups; unit failures retain matching units.
    ids={int(i) for i in re.findall(r'__i2r_source_contract_(\d+)::|source_contract_(\d+)\.rs',diagnostic) for i in i if i}
    selected=[{'kind':'integration','index':i,'source':v} for i,v in enumerate(frozen['tests']) if i in ids]
    selected += [{'kind':'unit','index':i,'source':v['source']} for i,v in enumerate(frozen.get('unit_tests',[])) if f'__i2r_contract_{i}::' in diagnostic]
    if not selected:raise Failure('source_check_unresolved','Cannot localize failed test')
    prefixes=tuple(f'__i2r_source_contract_{i}::' for i in ids)
    obligations=[o for o in frozen['obligations'] if o.get('test_name','').startswith(prefixes) or any(v['kind']=='unit' for v in selected)]
    source_ids={o['source'] for o in obligations};model=state['bundle']['source_model']
    # Include declared source dependencies, never generation or candidate bodies.
    todo=list(source_ids)
    while todo:
        entity=model['entities'].get(todo.pop(),{})
        for dep in entity.get('dependencies',[]):
            if isinstance(dep,str) and dep in model['entities'] and dep not in source_ids:source_ids.add(dep);todo.append(dep)
    payload={'task':'Return {action:"test_correct|inconclusive|test_wrong",reason,source_evidence:[{source,quote}],derivation,edits:[{kind:"integration|unit",index,old:"complete old second assert_eq/ne argument",new:"source-derived closed literal/constructor expression"}]}. A test_wrong verdict must establish its exact corrected expectation from source equations. No weakened tests or candidate edits.', 'tests':selected,'obligations':obligations,'failure':re.sub(r'(?m)^\s*(?:left|right):.*$', '[observed output withheld]', diagnostic),'source':pages(model,source_ids,cfg['segmented']['source_page_characters']),'interfaces':interfaces(state['files']),'numeric_policy':state['bundle']['numeric_policy']}
    save(directory/'original.json',{'frozen':frozen,'failure':result,'candidate_lock':lock(state)})
    conversation=Conversation(directory/'isolated-conversation.json',cfg);conversation.enter('source-failure-check')
    proposal=conversation.call(provider,SYSTEM,payload,directory/'request',phase='generation');save(directory/'diagnosis.json',proposal)
    seen[key].update(status='completed',verdict=proposal.get('action'));save(ledger,seen)
    from .test_order_policy import source_first
    if proposal.get('action')=='test_correct' and source_first(state) and not state.get('source_candidate_lock'):
        return {'action':'candidate_repair','diagnosis':proposal,'evidence':str(directory)}
    if proposal.get('action')!='test_wrong':raise Failure('source_check_unresolved','Correct or inconclusive test: candidate remains failed',proposal)
    validate_scope(proposal,selected)
    updated=revise(frozen,proposal,state)
    updated['binding_audit']={'method':'source-expectation-check-v1','path':str(directory),'second_model_review':False}
    return {'action':'binding_fix','frozen':updated,'evidence':str(directory)}
