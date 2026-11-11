"""Explicit source-operation obligations; finite coverage is not equivalence."""
import re
from .common import Failure


def requirements(state,source_ids):
    rows=[]
    mapped={r['source'] for r in state['mapping'] if r.get('rust_item')}
    for n in sorted(set(source_ids)&mapped):
        # Numeric runtime obligations apply to value-level source operations.
        # A class named divide/modulo is an interface, not an executable value.
        if not n.startswith('constant:'):continue
        low=n.lower();categories=[]
        if 'take_bit' in low:categories=['small_nonnegative_huge_count','bit_boundary']
        elif 'drop_bit' in low:categories=['small_nonnegative_huge_count','bit_boundary']+(['negative_huge_count'] if 'int' in low and 'nat' not in low else [])
        elif 'push_bit' in low:categories=['zero_huge_count','nonzero_range_boundary']
        elif any(k in low for k in ['divmod','divide','modulo','div_integer','div_int']):categories=['zero_divisor','division_signs']
        elif re.search(r'(plus|minus|times)_(nat|int)$',low):categories=['zero_and_range_boundaries']
        elif low.endswith('int.nat'):categories=['negative_clamp_and_range']
        elif low.endswith('of_nat'):categories=['conversion_range']
        elif n in state['bundle']['source_model']['entries']:categories=['public_behavior']
        if not categories and state['bundle']['source_model']['entities'].get(n,{}).get('execution_equations'):categories=['source_operation']
        for category in categories:rows.append({'source':n,'category':category})
    return rows


def validate_obligations(proposal,required):
    code=proposal.get('test_source','')+'\n'+'\n'.join(t.get('source','') for t in proposal.get('unit_tests',[]))
    # AST binds each claim to a real, enabled #[test], rather than a name in prose.
    from tree_sitter import Language,Parser
    import tree_sitter_rust
    data=code.encode();root=Parser(Language(tree_sitter_rust.language())).parse(data).root_node
    tests=set();stack=[root]
    while stack:
        node=stack.pop();stack.extend(node.named_children)
        if node.type!='function_item':continue
        attrs=[];p=node.prev_named_sibling
        while p is not None and p.type in {'attribute_item','line_comment','block_comment'}:
            attrs.append(data[p.start_byte:p.end_byte].decode());p=p.prev_named_sibling
        text=' '.join(attrs)
        if re.search(r'#\s*\[\s*test\s*\]',text) and not re.search(r'#\s*\[\s*ignore\b',text):
            name=node.child_by_field_name('name');tests.add(data[name.start_byte:name.end_byte].decode())
    claimed={(r.get('source'),r.get('category')) for r in proposal.get('obligations',[])
             if r.get('test_name','').split('::')[-1] in tests and r.get('expected_basis')}
    # Applicability is a source/API judgment, independently reviewed before this
    # check; archive explicit omissions instead of manufacturing a callable API.
    claimed|={(r.get('source'),r.get('category')) for r in proposal.get('obligations',[])
              if r.get('disposition')=='not_applicable' and r.get('source_basis') and r.get('api_basis') and r.get('expected_basis')}
    missing=[r for r in required if (r['source'],r['category']) not in claimed]
    if missing:raise Failure('missing_support_verification','Every applicable obligation needs an actual enabled test with exact test_name and category; source expectations cannot be weakened',{'missing':missing,'actual_tests':sorted(tests)})


def validate_records(proposal, known_sources):
    """Execution claims and explicit omissions have different required fields."""
    rows=proposal.get('obligations',[]);errors=[]
    if not isinstance(rows,list):
        raise Failure('missing_support_verification','obligations must be an array')
    for i,row in enumerate(rows):
        if not isinstance(row,dict):
            errors.append({'index':i,'error':'record must be an object'});continue
        missing=[k for k in ['source','expected_basis'] if not row.get(k)]
        if not isinstance(row.get('source'),str) or row['source'] not in known_sources:
            errors.append({'index':i,'source':row.get('source'),'error':'unknown source ID'})
        if 'category' in row and not isinstance(row['category'],str):
            errors.append({'index':i,'source':row.get('source'),'error':'category must be a string'})
        if row.get('disposition') in ('not_applicable','inaccessible'):
            missing += [k for k in ['category','source_basis','api_basis'] if not row.get(k)]
        elif 'case' not in row or row['case'] is None or row['case']=='':missing.append('case')
        if missing:errors.append({'index':i,'source':row.get('source'),'missing_fields':missing})
    if errors:
        raise Failure('missing_support_verification',
            'Executing obligations need a concrete case. Explicit not_applicable/inaccessible records instead need category, source_basis and api_basis; they are not executed successes. Every record needs one exact source ID and independent expected_basis.',
            {'record_errors':errors,'valid_source_ids':sorted(known_sources)})
