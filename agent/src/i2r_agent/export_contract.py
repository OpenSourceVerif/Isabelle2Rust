"""Narrow syntactic check against accidental monomorphization of public exports.

This is not Rust type checking, semantic validation, or an Isabelle/Rust proof.
Rustc checks the accepted implementation afterwards.
"""
import re
from .common import Failure


def polymorphic_exports(bundle):
    result=[]
    if 'source_model' in bundle:
        from .program_model import walk
        model=bundle.get('original_source_model',bundle['source_model'])
        for name in model['entries']:
            entity=model['entities'].get(name,{})
            variables={node['name']:node.get('sort',[]) for _,node in walk(entity.get('source_type',{}))
                       if node.get('kind') in {'free','schematic'}}
            if variables:
                result.append({'source':name,'type_variables':list(variables),'class_constraints':variables})
        return result
    for graph in bundle.get('programs',[]):
        entries=set(graph['entries'])
        for node in graph['nodes']:
            statement=node['statement']
            variables=statement.get('signature',{}).get('variables',[])
            if node['id'] in entries and statement.get('kind')=='function' and variables:
                result.append({'source':node['id'],'type_variables':[v[0] for v in variables],
                    'class_constraints':{v[0]:v[1] for v in variables}})
    return result


def generic_function_parameters(source,name):
    # Mask comments and ordinary strings before looking for an actual fn item.
    masked=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',lambda m:' '*len(m[0]),source)
    found=[]
    for match in re.finditer(r'\bfn\s+'+re.escape(name)+r'\s*',masked):
        start=match.end()
        if start>=len(masked) or masked[start]!='<':continue
        depth=0;parts=[];begin=start+1
        for pos in range(start,len(masked)):
            char=masked[pos]
            if char=='<':depth+=1
            elif char=='>' and (pos==0 or masked[pos-1]!='-'):
                depth-=1
                if depth==0:
                    parts.append(masked[begin:pos]);break
            elif char==',' and depth==1:
                parts.append(masked[begin:pos]);begin=pos+1
        names=set()
        for part in parts:
            parameter=re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::|=|$)',part)
            if parameter and parameter[1]!='const':names.add(parameter[1])
        found.append(names)
    return found


def check_exports(bundle,files,mapping):
    requirements=polymorphic_exports(bundle);by_source={row['source']:row for row in mapping}
    problems=[]
    for requirement in requirements:
        row=by_source[requirement['source']]
        item=row.get('rust_item',row['rust']);variables=row.get('type_parameters',{})
        if not isinstance(item,str) or not re.fullmatch(r'(?:[A-Za-z_][A-Za-z0-9_]*::)*[A-Za-z_][A-Za-z0-9_]*',item):
            problems.append({**requirement,'issue':'Provide rust_item as exact public Rust function path'});continue
        if not isinstance(variables,dict) or set(variables)!=set(requirement['type_variables']) or not all(isinstance(v,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',v) for v in variables.values()):
            problems.append({**requirement,'issue':'mapping.type_parameters must contain exactly the HOL type-variable keys; Rust-only callable/lifetime parameters are not additional HOL variables',
                'expected_keys':requirement['type_variables'],'actual_mapping':variables,
                'missing_keys':sorted(set(requirement['type_variables'])-set(variables)) if isinstance(variables,dict) else requirement['type_variables'],
                'extra_keys':sorted(set(variables)-set(requirement['type_variables'])) if isinstance(variables,dict) else [],
                'repair':'Retain mappings for the expected source keys only. Keep legitimate additional Rust generic parameters in the Rust declaration, not as invented HOL keys.'});continue
        declarations=[params for name,text in files.items() if name.endswith('.rs')
                      for params in generic_function_parameters(text,item.rsplit('::',1)[-1])]
        if not any(set(variables.values())<=params for params in declarations):
            problems.append({**requirement,'rust_item':item,'issue':'Export was narrowed or generic declaration is missing; wire UBig must not specialize the source API'})
    if problems:raise Failure('plan_contract_failed','Preserve polymorphic source exports independently of the UBig observation wrapper',problems)
    return {'checked_exports':requirements,'scope':'Syntactic presence of reported Rust type parameters; bounds, exact types and semantics are not proved'}
