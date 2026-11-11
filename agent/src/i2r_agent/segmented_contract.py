"""Exact module/item identities and separately scoped source coverage checks."""
from pathlib import PurePosixPath
import re
from .common import Failure
from .rust_index import build
from .segmentation import dependencies, INTRINSICS
from .export_contract import check_exports


def items(files):
    index=build(files);result={}
    for row in index['items']:
        if not row['name'] or not row.get('path_addressable',True):continue
        path=PurePosixPath(row['file'])
        parts=list(path.with_suffix('').parts[1:])
        if parts and parts[-1] in {'lib','mod'}:parts.pop()
        # impl scope is supplied by the index; exact module placement is required.
        name='::'.join(['crate']+([] if row.get('crate_root_path') else parts+row['scope'])+[row['name']])
        result.setdefault(name,[]).append(row)
    return result


def canonical(name):
    return name if name.startswith('crate::') else 'crate::'+name


def interfaces(files):
    """Test authors need actual data constructors, not algorithm bodies."""
    return {name:[{**{k:r.get(k) for k in ['signature','file','scope','module_scope','kind','attributes']},
                   **({'declaration':r['text']} if r['kind'] in {'struct_item','enum_item','enum_variant','type_item'} else {})}
                  for r in rows] for name,rows in items(files).items()}


PRIMITIVES={'bool','char','str','usize','isize','u8','u16','u32','u64','u128','i8','i16','i32','i64','i128','f32','f64'}

def external_type(row):
    name=row.get('rust_item','')
    return row.get('kind') in {'native','trait'} and row.get('source','').startswith(('type:','class:')) and (name in PRIMITIVES or bool(re.fullmatch(r'[A-Za-z_]\w*(?:::[A-Za-z_]\w*)+',name)) and not name.startswith(('crate::','self::','super::')))

def validate_item(index,row):
    if external_type(row):return {'file':'src/lib.rs','text':row['rust_item'],'signature':row['rust_item'],'kind':'external_type'}
    return resolve(index,row['rust_item'])

def probes(mapping):
    lines=[]
    for i,row in enumerate(mapping):
        if not external_type(row):continue
        name=row['rust_item']
        if name in PRIMITIVES:lines.append(f'type I2RType{i} = {name};')
        else:lines.append(f'use {name} as I2RType{i};')
    return '\n#[allow(dead_code, unused_imports)]\nmod __i2r_mapping_checks {\n'+'\n'.join(lines)+'\n}\n'

def resolve(index, name):
    matches=index.get(canonical(name),[])
    if len(matches)!=1:
        raise Failure('ambiguous_rust_item','Use an existing unambiguous fully qualified item',{'item':name,'matches':len(matches),'available':sorted(index)})
    return matches[0]


def coverage(bundle, files, mapping, roots, plan, final=False):
    model=bundle['source_model'];index=items(files);rows={r['source']:r for r in mapping}
    if len(rows)!=len(mapping):raise Failure('invalid_mapping','Duplicate source mappings')
    unknown=set(rows)-model['entities'].keys()
    if unknown:raise Failure('invalid_mapping','Mappings reference unknown source facts',sorted(unknown))
    planned={r['source']:r for r in plan['boundaries']}
    visited=set();todo=list(roots);missing=[]
    while todo:
        n=todo.pop()
        if n in visited or n in INTRINSICS:continue
        visited.add(n)
        row=rows.get(n)
        if not row:
            missing.append(n);continue
        if not row.get('rust_item'):raise Failure('invalid_mapping','A realization needs an exact owning Rust item',row)
        validate_item(index,row)
        if row.get('kind') in {'replacement','native','inlined','trait'}:
            if not row.get('basis') or not row.get('conditions'):raise Failure('invalid_mapping','Boundary contract needs basis and conditions',row)
        else:
            todo.extend(dependencies(model['entities'][n]))
        # All scheduled business/support entities remain mandatory, even if a
        # consumer uses replacement: global boundary selection controls schedule.
    if missing:raise Failure('plan_contract_failed','Realize missing active source obligations',{'missing':sorted(missing)})
    exports=set(model['entries']) & set(roots)
    if final and set(model['entries'])-exports:raise Failure('missing_exports','Final roots must include every original export')
    scoped={**bundle,'source_model':{**model,'entries':sorted(exports)},'original_source_model':{**model,'entries':sorted(exports)}}
    # Verify generics against the resolved item alone, never another same-name item.
    for n in exports:
        row=rows[n];item=resolve(index,row['rust_item'])
        one={**scoped,'source_model':{**model,'entries':[n]},'original_source_model':{**model,'entries':[n]}}
        check_exports(one,{'src/lib.rs':item['text']},[row])
    return {'status':'passed','source_ids':sorted(visited),'exports':sorted(exports),
            'scope':'Exact item identity and declared source coverage; compiler and independent tests remain required.'}
