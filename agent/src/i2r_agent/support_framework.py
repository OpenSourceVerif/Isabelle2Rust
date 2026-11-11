"""Reusable representation scaffolding, containing no task cases or expectations."""
import re
from .segmented_contract import interfaces
from .task_context import fingerprint

SCHEMA='source-test-scaffolding-v1'


def enum_layout_matches(declaration,name,kind):
    """Compare Rust syntax, ignoring only lexical comments, never attributes/fields."""
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    parser=Parser(Language(tree_sitter_rust.language()))
    data=declaration.encode();root=parser.parse(data).root_node
    items=[n for n in root.named_children if n.type not in {'line_comment','block_comment'}]
    if root.has_error or len(items)!=1 or items[0].type!='enum_item':return False
    generics=items[0].child_by_field_name('type_parameters')
    if generics is None:return False
    params=[n for n in generics.named_children if n.type not in {'line_comment','block_comment'}]
    if len(params)!=1 or params[0].type!='type_parameter':return False
    param=params[0].child_by_field_name('name')
    if param is None:return False
    t=data[param.start_byte:param.end_byte].decode()
    if kind=='list':fields=f'Nil,Cons({t},Box<{name}<{t}>>)'
    elif kind=='tree':fields=f'Leaf,Node(Box<{name}<{t}>>,{t},Box<{name}<{t}>>)'
    else:return False
    expected=f'pub enum {name}<{t}>{{{fields}}}'.encode()
    def shape(node,source):
        # Optional trailing commas do not change layout. All other syntax,
        # including cfg/doc attributes, bounds and discriminants, is retained.
        children=[n for n in node.children if n.type not in {'line_comment','block_comment'}]
        if children and children[-1].type=='}' and len(children)>1 and children[-2].type==',':
            children.pop(-2)
        return (node.type,tuple(shape(n,source) for n in children)) if children else (node.type,source[node.start_byte:node.end_byte])
    return shape(items[0],data)==shape(parser.parse(expected).root_node.named_children[0],expected)


def build(state):
    api=interfaces(state['files']);mapping={r['source']:r.get('rust_item','') for r in state['mapping']}
    sources=state['bundle']['source_model']['entities'];parts=[];provided=[]
    for source,kind in [('type:List.list','list'),('type:Tree_Test.tree','tree')]:
        path=mapping.get(source,'');rows=api.get(path,[])
        if source not in sources or len(rows)!=1 or not re.fullmatch(r'crate(?:::[A-Za-z_]\w*)+',path):continue
        name=path.rsplit('::',1)[-1];decl=rows[0].get('declaration','')
        actual=path.replace('crate::','i2r_candidate::',1)
        if kind=='list':
            alias=re.fullmatch(r'pub type '+re.escape(name)+r'<([A-Za-z_]\w*)>\s*=\s*Vec<\1>\s*;',decl.strip())
            enum=enum_layout_matches(decl,name,'list')
            if not alias and not enum:continue
            if enum and (mapping.get('constant:List.list.Nil',path+'::Nil')!=path+'::Nil' or mapping.get('constant:List.list.Cons',path+'::Cons')!=path+'::Cons'):continue
            body=('pub fn list_from_vec<T>(xs:Vec<T>)->LIST<T>{xs}\npub fn list_into_vec<T>(xs:LIST<T>)->Vec<T>{xs}' if alias else '''pub fn list_from_vec<T>(xs:Vec<T>)->LIST<T>{
    xs.into_iter().rev().fold(LIST::Nil,|tail,x|LIST::Cons(x,Box::new(tail)))
}
pub fn list_into_vec<T>(mut xs:LIST<T>)->Vec<T>{
    let mut values=Vec::new();
    loop {match xs {LIST::Nil=>return values,LIST::Cons(x,tail)=>{values.push(x);xs=*tail;}}}
}''')
            parts.append(body.replace('LIST',actual));provided+=['list_from_vec<T>(Vec<T>) -> CandidateList<T>','list_into_vec<T>(CandidateList<T>) -> Vec<T>']
        else:
            enum=enum_layout_matches(decl,name,'tree')
            if not enum or mapping.get('constant:Tree_Test.tree.Leaf')!=path+'::Leaf' or mapping.get('constant:Tree_Test.tree.Node')!=path+'::Node':continue
            parts.append('''#[derive(Debug,PartialEq)]
pub enum TreeShape<T>{Leaf,Node(Box<TreeShape<T>>,T,Box<TreeShape<T>>)}
pub fn tree_from_shape<T>(shape:TreeShape<T>)->TREE<T>{match shape{
    TreeShape::Leaf=>TREE::Leaf,
    TreeShape::Node(l,x,r)=>TREE::Node(Box::new(tree_from_shape(*l)),x,Box::new(tree_from_shape(*r)))}}
pub fn tree_into_shape<T>(tree:TREE<T>)->TreeShape<T>{match tree{
    TREE::Leaf=>TreeShape::Leaf,
    TREE::Node(l,x,r)=>TreeShape::Node(Box::new(tree_into_shape(*l)),x,Box::new(tree_into_shape(*r)))}}
'''.replace('TREE',actual))
            provided+=['TreeShape<T> = Leaf | Node(Box<TreeShape<T>>,T,Box<TreeShape<T>>)','tree_from_shape<T>(TreeShape<T>) -> CandidateTree<T>','tree_into_shape<T>(CandidateTree<T>) -> TreeShape<T>']
    if not parts:return None
    body='#[allow(dead_code)]\nmod i2r_test_support {\n'+'\n'.join(parts)+'\n}\n'
    return {'schema':SCHEMA,'identity':fingerprint([SCHEMA,body]),'integration_source':body,
        'unit_source':body.replace('i2r_candidate::','crate::'),'api':provided,
        'policy':'Scaffolding constructs/consumes data only. It contains no cases, expected values, target calls or added bounds on candidate APIs. Author meaningful business/source tests and fixed independent expectations yourself; call candidate operations on the actual side. Generic scaffold functions require no Clone/Ord/Debug/Eq. TreeShape derives only affect assertions on chosen concrete types.'}


def inject(code,framework,unit=False):
    if not code or not framework:return code
    # Rust item order is independent of use sites. Appending preserves inner
    # module attributes/doc comments at the author's original beginning.
    return code+'\n'+framework['unit_source' if unit else 'integration_source']
