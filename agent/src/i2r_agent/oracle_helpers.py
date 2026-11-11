"""Narrow, mechanically recognized local assertion helpers; no arbitrary argument edits."""
import re
from tree_sitter import Language,Parser
import tree_sitter_rust
from .task_context import fingerprint
PARSER=Parser(Language(tree_sitter_rust.language()))
MACROS={'assert_eq','assert_ne','assert','matches','panic'}

def tree(code):
    data=code.encode();root=PARSER.parse(data).root_node
    return data,root

def walk(node):
    yield node
    for child in node.named_children:yield from walk(child)

def spelling(data,node):return data[node.start_byte:node.end_byte].decode()
def unwrap(n):return n.named_children[0] if n.type in {'expression_statement','match_pattern'} and len(n.named_children)==1 else n

def tokens(code):
    """Exact Rust tokens except whitespace/comments and inert diagnostic string text."""
    data,root=tree('fn __shape()'+code)
    if root.has_error:return None
    body=root.named_children[0].child_by_field_name('body');out=[]
    def visit(n):
        if n.type in {'line_comment','block_comment'}:return
        if n.type in {'string_literal','raw_string_literal'}:out.append('"MESSAGE"');return
        if not n.children:out.append(spelling(data,n));return
        for c in n.children:visit(c)
    visit(body);return out

def proof(data,fn):
    """Recognize direct equality, or exhaustive consuming-chain element equality.

    Chain shape includes its terminal empty assertion: expected length cannot
    silently truncate testing. Constructors and binders are arbitrary, not case names.
    Unknown loops/methods/branches/dynamic calls are deliberately unsupported.
    """
    try:
        params=fn.child_by_field_name('parameters').named_children
        if len(params)!=2 or any(p.type!='parameter' or p.child_by_field_name('pattern').type!='identifier' for p in params):return None
        actual,expected=[spelling(data,p.child_by_field_name('pattern')) for p in params]
        if actual==expected:return None
        body=fn.child_by_field_name('body');bodytext=spelling(data,body)
        for macro in ['assert_eq','assert_ne']:
            if tokens(bodytext)==tokens('{'+macro+'!('+actual+','+expected+');}'):
                return {'kind':'direct-equality-helper','actual_parameter':actual,'expected_parameter':expected,'helper_sha256':fingerprint(spelling(data,fn))}
        nodes=[unwrap(n) for n in body.named_children if n.type not in {'line_comment','block_comment'}]
        if len(nodes)!=3 or nodes[0].type!='let_declaration' or nodes[1].type!='for_expression':return None
        init,loop,last=nodes;cursor=spelling(data,init.child_by_field_name('pattern'))
        if init.child_by_field_name('pattern').type!='identifier' or spelling(data,init.child_by_field_name('value'))!=actual:return None
        pat=loop.child_by_field_name('pattern')
        if pat.type!='tuple_pattern' or len(pat.named_children)!=2 or any(n.type!='identifier' for n in pat.named_children):return None
        index,element=[spelling(data,n) for n in pat.named_children]
        expected_type=spelling(data,params[1].child_by_field_name('type'))
        # Native primitive arrays only for the consuming iterator shape; no user
        # IntoIterator implementation can redirect the expected values to code.
        if not re.fullmatch(r'\[\s*(?:u|i)(?:8|16|32|64|128|size)\s*;\s*[A-Za-z_]\w*\s*\]',expected_type):return None
        lb=[unwrap(n) for n in loop.child_by_field_name('body').named_children]
        if len(lb)!=1 or lb[0].type!='match_expression':return None
        arms=lb[0].child_by_field_name('body').named_children
        if len(arms)!=2:return None
        cons=unwrap(arms[0].child_by_field_name('pattern'));empty=unwrap(arms[1].child_by_field_name('pattern'))
        if cons.type!='tuple_struct_pattern' or len(cons.named_children)!=3 or any(n.type!='identifier' for n in cons.named_children[1:]):return None
        if empty.type not in {'identifier','scoped_identifier'}:return None
        cons_path=spelling(data,cons.child_by_field_name('type'));empty_path=spelling(data,empty);head,tail=[spelling(data,n) for n in cons.named_children[1:]]
        cb=arms[0].child_by_field_name('value')
        if cb.type!='block' or len(cb.named_children)!=2:return None
        inner=unwrap(cb.named_children[0])
        if inner.type!='match_expression' or len(inner.child_by_field_name('body').named_children)!=1:return None
        arm=inner.child_by_field_name('body').named_children[0];wrap=unwrap(arm.child_by_field_name('pattern'))
        if wrap.type!='tuple_struct_pattern' or len(wrap.named_children)!=2 or wrap.named_children[1].type!='identifier':return None
        wrap_path=spelling(data,wrap.child_by_field_name('type'));value=spelling(data,wrap.named_children[1])
        if len({actual,expected,cursor,index,element,head,tail,value})!=8:return None
        template=f'''{{let mut {cursor}={actual};for ({index},{element}) in {expected}.into_iter().enumerate(){{match {cursor}{{{cons_path}({head},{tail})=>{{match {head}{{{wrap_path}({value})=>assert_eq!({value},{element},"MESSAGE",{index}),}}{cursor}=*{tail};}}{empty_path}=>panic!("MESSAGE",{index}),}}}}assert!(matches!({cursor},{empty_path}),"MESSAGE");}}'''
        if tokens(bodytext)!=tokens(template):return None
        return {'kind':'exhaustive-chain-equality-helper','actual_parameter':actual,'expected_parameter':expected,'empty_pattern':empty_path,'helper_sha256':fingerprint(spelling(data,fn)),'terminal_completeness_assertion_preserved':True}
    except (AttributeError,IndexError,TypeError):return None

def resolve(context,state=None):
    data,root=tree(context)
    if root.has_error:return {}
    nodes=list(walk(root))
    if any(n.type=='macro_definition' or n.type=='use_declaration' and '*' in spelling(data,n) for n in nodes):return {}
    # Reject imported/shadowed standard assertion macros and candidate macros.
    for n in nodes:
        if n.type=='use_declaration' and any(re.search(r'\b'+name+r'\b',spelling(data,n)) for name in MACROS):return {}
    if state:
        for text in state.get('files',{}).values():
            d,r=tree(text)
            if any(n.type=='macro_definition' and spelling(d,n.child_by_field_name('name')) in MACROS for n in walk(r)):return {}
    functions=[n for n in nodes if n.type=='function_item'];result={}
    for fn in functions:
        name=spelling(data,fn.child_by_field_name('name'))
        if sum(spelling(data,f.child_by_field_name('name'))==name for f in functions)!=1:continue
        # Only unambiguous artifact-level helpers, not nested/module-local paths.
        if fn.parent!=root:continue
        if any(n.type=='identifier' and spelling(data,n)==name and not (n.parent==fn and n==fn.child_by_field_name('name')) and not (n.parent.type=='call_expression' and n==n.parent.child_by_field_name('function')) for n in nodes):continue
        found=proof(data,fn)
        if found:result[name]=found
    return result

def expected_spans(code,context=None,state=None):
    from .source_failure_check import closed_expected_literal
    helpers=resolve(context or code,state);data,root=tree(code)
    if root.has_error:return []
    out=[]
    for n in walk(root):
        if n.type!='call_expression':continue
        fn=n.child_by_field_name('function');args=n.child_by_field_name('arguments').named_children
        if fn.type!='identifier' or spelling(data,fn) not in helpers or len(args)!=2:continue
        arg=args[1];text=spelling(data,arg)
        if closed_expected_literal(text):out.append((arg.start_byte,arg.end_byte,text))
    return out
