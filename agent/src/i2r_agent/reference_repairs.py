"""One compile-triggered repair of generated BigInt reference boundaries.
Never patches candidate code or Isabelle input. Rejects ambiguous numeric domains.
"""
import re
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_rust

METHODS={
 'Zero':('zero','fn zero() -> Self { BigInt::ZERO }'),
 'One':('one','fn one() -> Self { BigInt::from(1u8) }'),
 'Plus':('plus','fn plus(a: Self, b: Self) -> Self { a + b }'),
 'Times':('times','fn times(a: Self, b: Self) -> Self { a * b }'),
}

def numeric_domains(candidate_model,wrapper_model):
    """Unify actual wrapper calls with each original exported root's type variables."""
    roots=set(candidate_model['entries']);evidence=[];domains=set()
    def unify(pattern,actual,bindings):
        if pattern.get('kind') in {'free','schematic'}:
            key=(pattern['name'],pattern.get('index'))
            if key in bindings and bindings[key]!=actual:raise ValueError('Inconsistent root type instantiation')
            bindings[key]=actual;return
        if pattern.get('name')!=actual.get('name') or len(pattern.get('args',[]))!=len(actual.get('args',[])):raise ValueError('Root type does not match actual wrapper call')
        for a,b in zip(pattern.get('args',[]),actual.get('args',[])):unify(a,b,bindings)
    def numbers(t):
        found={t['name']} if t.get('kind')=='type' and t.get('name') in {'Nat.nat','Int.int'} else set()
        for a in t.get('args',[]):found|=numbers(a)
        return found
    for eid,entity in wrapper_model['entities'].items():
        if not eid.startswith(('constant:Model.','constant:Kernel.')):continue
        for call in entity.get('instance_resolutions',[]):
            target='constant:'+call['constant']
            if target not in roots:continue
            bindings={};unify(candidate_model['entities'][target]['source_type'],call['type'],bindings)
            types=set().union(*(numbers(v) for v in bindings.values())) if bindings else set()
            domains|=types;evidence.append({'caller':eid,'root':target,'actual_type':call['type'],'numeric_variable_domains':sorted(types)})
    return {'domains':sorted(domains),'root_instantiations':evidence}

def supports(diagnostic):
    return ('expected expression, found `+`' in diagnostic or
            ('num_bigint::BigInt' in diagnostic and 'E0277' in diagnostic))


def apply(crate,diagnostic,numeric_proof):
    """Only missing BigInt traits / the exact rejected `if ... + ...` syntax."""
    missing=set(re.findall(r'the trait `(?:[A-Za-z_]\w*::)?(\w+)` is not implemented for `num_bigint::BigInt`',diagnostic))
    missing|=set(re.findall(r'num_bigint::BigInt: (\w+)` is not satisfied',diagnostic))
    fix_if='expected expression, found `+`' in diagnostic
    parser=Parser(Language(tree_sitter_rust.language()));changes=[];pending_writes=[];pending_writes=[]
    for path in sorted((Path(crate)/'src').glob('*.rs')):
        data=path.read_bytes();root=parser.parse(data).root_node
        if root.has_error:raise ValueError('Generated reference is not structurally parseable')
        traits={};impls={};edits=[]
        for n in root.named_children:
            if n.type=='trait_item':
                name=n.child_by_field_name('name').text.decode();traits[name]=n
            if n.type=='impl_item':
                tr=n.child_by_field_name('trait');ty=n.child_by_field_name('type')
                if tr and ty and ty.text==b'BigInt':impls[tr.text.decode()]=n
        needed=set();pending=list(missing)
        while pending:
            name=pending.pop()
            if name in needed or name not in traits:continue
            needed.add(name);node=traits[name];text=node.text.decode().split('{',1)[0]
            if ':' in text:pending.extend(re.findall(r'\b[A-Z]\w*\b',text.split(':',1)[1]))
        # A compile failure can mask an existing generated primitive panic stub.
        needed.update(name for name,n in impls.items() if name in METHODS and b'unimplemented instance method:' in n.text)
        methods=dict(METHODS)
        if 'Minus' in needed:
            domains=numeric_proof.get('domains',[])
            if domains==['Nat.nat']:body='if a <= b { BigInt::ZERO } else { a - b }'
            elif domains==['Int.int']:body='a - b'
            else:raise ValueError('Missing Minus needs exactly one proven nat/int root instantiation')
            methods['Minus']=('minus','fn minus(a: Self, b: Self) -> Self { '+body+' }')
        for name in sorted(needed):
            if name not in methods:continue  # Derived marker traits have blanket implementations.
            method,body=methods[name];node=traits[name]
            functions=[n for n in node.child_by_field_name('body').named_children if n.type=='function_signature_item']
            if len(functions)!=1 or functions[0].child_by_field_name('name').text.decode()!=method:raise ValueError('Unexpected primitive trait shape '+name)
            compact=re.sub(r'\s+','',functions[0].text.decode())
            expected0=r'fn'+method+r'\(\)->Self(?:whereSelf:Sized)?;'
            expected2=r'fn'+method+r'\(\w+:Self,\w+:Self\)->Self(?:whereSelf:Sized)?;'
            if not re.fullmatch(expected0 if name in {'Zero','One'} else expected2,compact):raise ValueError('Unsupported primitive signature '+name)
            replacement=('impl '+name+' for BigInt { '+body+' }').encode()
            if name in impls:
                n=impls[name]
                # Preserve real generated dictionaries; replace only the backend's exact panic stub.
                block=n.child_by_field_name('body');fs=[x for x in block.named_children if x.type=='function_item']
                if len(fs)!=1:raise ValueError('Unexpected concrete primitive instance '+name)
                actual=re.sub(r'\s+','',fs[0].child_by_field_name('body').text.decode())
                if actual=='{panic!("unimplementedinstancemethod:'+method+'")}' or actual=='{panic!("unimplementedinstancemethod:'+method+'");}':
                    edits.append((n.start_byte,n.end_byte,replacement,'stub:'+name))
            else:edits.append((len(data),len(data),b'\n'+replacement+b'\n','missing:'+name))
        # Preserve real comparison methods; replace only the exact BigInt panic stub.
        for trait,method,operator in [('Ord','less','<'),('Ord','less_eq','<='),('Equal','equal','==')]:
            if trait not in impls:continue
            block=impls[trait].child_by_field_name('body')
            for fn in block.named_children:
                if fn.type!='function_item' or fn.child_by_field_name('name').text.decode()!=method:continue
                body=fn.child_by_field_name('body')
                compact=re.sub(r'\s+','',body.text.decode())
                if compact not in {'{panic!("unimplementedinstancemethod:'+method+'")}', '{panic!("unimplementedinstancemethod:'+method+'");}'}:continue
                signature=re.sub(r'\s+','',fn.text.decode().split('{',1)[0])
                if not re.fullmatch('fn'+method+r'\(\w+:Self,\w+:Self\)->bool',signature):raise ValueError('Unsupported comparison stub signature')
                replacement=('fn '+method+'(a: Self, b: Self) -> bool { a '+operator+' b }').encode()
                edits.append((fn.start_byte,fn.end_byte,replacement,'stub:'+trait+'.'+method))
        if fix_if:
            stack=[root]
            while stack:
                n=stack.pop();stack.extend(n.children)
                if n.type=='binary_expression' and any(c.type=='+' for c in n.children):
                    for field in ['left','right']:
                        operand=n.child_by_field_name(field)
                        if operand and operand.type=='if_expression':edits.append((operand.start_byte,operand.end_byte,b'('+operand.text+b')','parenthesize_if_add_operand'))
        if edits:
            for a,b,text,reason in sorted(edits,key=lambda x:(x[0],x[1]),reverse=True):data=data[:a]+text+data[b:]
            pending_writes.append((path,data));changes.append({'file':str(path.name),'repairs':[r for _,_,_,r in edits]})
    if not changes:raise ValueError('No supported BigInt reference repair matched the compiler evidence')
    for path,data in pending_writes:path.write_bytes(data)
    return {'policy':'compile-triggered-bigint-reference-adapter-v1','numeric_proof':numeric_proof,'changes':changes}
