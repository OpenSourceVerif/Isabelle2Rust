"""Small source-shaped list observers using actual candidate results."""
import re
from pathlib import Path
from .connector_templates import normalized,KERNEL,SCAFFOLD
from .segmented_contract import interfaces
from .support_framework import build as scaffold

SCHEMA='checked-list-observers-v1'


def signature(signature):
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    data=(signature+'{loop{}}').encode();root=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
    if root.has_error or len(root.named_children)!=1:return None
    fn=root.named_children[0]
    if fn.type!='function_item' or not signature.startswith('pub fn '):return None
    params=fn.child_by_field_name('parameters');result=fn.child_by_field_name('return_type')
    if params is None or result is None:return None
    raw=lambda node:data[node.start_byte:node.end_byte].decode()
    types=[]
    for param in params.named_children:
        typ=param.child_by_field_name('type')
        if param.type!='parameter' or typ is None:return None
        types.append(raw(typ))
    generics=fn.child_by_field_name('type_parameters')
    names=set()
    if generics:
        for param in generics.named_children:
            name=param.child_by_field_name('name')
            if param.type!='type_parameter' or name is None:return None
            names.add(raw(name))
    return types,raw(result),names


def map_callback(signature,parameter,input_type,output_type):
    """Require the exact owned-element Fn contract; shared borrow is ABI only."""
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    compact=lambda value:''.join(value.split())
    parameter=compact(parameter)
    match=re.fullmatch(r'(&?)([A-Za-z_]\w*)',parameter)
    if not match:return None
    borrowed,name=match.groups()
    data=(signature+'{loop{}}').encode()
    root=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
    if root.has_error:return None
    raw=lambda n:compact(data[n.start_byte:n.end_byte].decode())
    pending=[root];bounds=[]
    while pending:
        node=pending.pop();pending.extend(node.named_children)
        if node.type not in {'type_parameter','where_predicate'}:continue
        key=node.child_by_field_name('name' if node.type=='type_parameter' else 'left')
        bound=node.child_by_field_name('bounds')
        if key is not None and raw(key)==name and bound is not None:bounds.append(raw(bound))
    if bounds!=[':Fn('+input_type+')->'+output_type]:return None
    return borrowed


def generate(model,kernel,files,mapping,cfg):
    if cfg['preprocessing']['numeric_mode']!='checked' or cfg['testing']['transport']!='native-u128':return None
    if normalized(kernel)!=normalized(KERNEL):return None
    match=re.fullmatch(r'theory Model imports (\w+) begin definition observe :: "nat list \\<Rightarrow> nat list" where "observe input = (.*)" end',normalized(model))
    if not match:return None
    theory,term=match.groups();qualified=r'([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)'
    patterns=[('list',qualified+r' input'),('push',qualified+r' 0 input'),('sep',qualified+r' input 0'),
        ('map',qualified+r' \(\\<lambda>x\. x\+1\) input'),('deq',qualified+r' input \[\]'),
        ('delete',qualified+r' \(length input mod 8\) input')]
    chosen=next(((shape,re.fullmatch(pattern,term)) for shape,pattern in patterns if re.fullmatch(pattern,term)),None)
    if not chosen:return None
    shape,m=chosen;source='constant:'+m[1]
    if not m[1].startswith(theory+'.'):return None
    rows=[r for r in mapping if r.get('source')==source]
    if len(rows)!=1 or not re.fullmatch(r'crate(?:::[A-Za-z_]\w*)+',rows[0].get('rust_item','')):return None
    entry=rows[0]['rust_item'];api=interfaces(files);fn=api.get(entry,[])
    if len(fn)!=1:return None
    sig=signature(fn[0]['signature'])
    if not sig:return None
    framework=scaffold({'files':files,'mapping':mapping,'bundle':{'source_model':{'entities':{'type:List.list':{}}}}})
    if not framework or not any(x.startswith('list_from_vec') for x in framework['api']):return None
    mapped=[r.get('rust_item') for r in mapping if r.get('source')=='type:List.list']
    if len(mapped)!=1:return None
    typ=mapped[0];type_row=api.get(typ,[])
    if len(type_row)!=1:return None
    alias=type_row[0].get('kind')=='type_item';type_names={typ,typ.rsplit('::',1)[-1]}
    if alias:type_names|={'Vec','std::vec::Vec'}
    def list_type(raw):
        raw=''.join(raw.split())
        return any(raw==name+'<'+element+'>' for name in type_names for element in generic_names|{'u128'})
    params,returns,generic_names=sig
    if not list_type(returns):return None # unknown Result/partiality contracts stay explicit fallback
    actual=entry.replace('crate::','i2r_candidate::',1)
    data='i2r_observation_data::list_from_vec(input.to_vec())'
    scalar=lambda t:t.strip() in generic_names|{'u128'}
    if shape=='list' and len(params)==1 and list_type(params[0]):call=f'{actual}({data})'
    elif shape in {'push','delete'} and len(params)==2 and scalar(params[0]) and list_type(params[1]):
        value='0u128' if shape=='push' else '(input.len() as u128)%8'
        call=f'{actual}({value},{data})'
    elif shape=='sep' and len(params)==2 and list_type(params[0]) and scalar(params[1]):call=f'{actual}({data},0u128)'
    elif shape=='sep' and alias and len(params)==2 and any(''.join(params[0].split())=='&['+t+']' and ''.join(params[1].split())=='&'+t for t in generic_names|{'u128'}):call=f'{actual}(input,&0u128)'
    elif shape=='deq' and len(params)==2 and all(list_type(t) for t in params):call=f'{actual}({data},i2r_observation_data::list_from_vec(Vec::<u128>::new()))'
    elif shape=='map' and len(params)==2 and list_type(params[1]):
        element=lambda text:''.join(text.split()).rsplit('<',1)[1][:-1]
        borrow=map_callback(fn[0]['signature'],params[0],element(params[1]),element(returns))
        if borrow is None:return None
        callback='|x:u128|x.checked_add(1).unwrap_or_else(||panic!("I2R_NUMERIC_OVERFLOW"))'
        call=f'{actual}({borrow}({callback}),{data})'
    else:return None
    helpers=framework['integration_source'].replace('i2r_test_support','i2r_observation_data')
    code=helpers+'\n'+SCAFFOLD+f'pub fn observe(input:&[WireInt])->Vec<WireInt>{{i2r_observation_data::list_into_vec({call})}}\n'
    return {'status':'generated','schema':SCHEMA,'source':source,'shape':shape,'files':{'src/lib.rs':code},
        'scope':'Exact Model expression shape, identity Kernel, mapped list representation and candidate signature; observation encodes the actual returned list, never expected values. Actual compilation and dual references remain mandatory.'}
