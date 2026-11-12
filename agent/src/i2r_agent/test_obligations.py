"""Explicit source-operation obligations; finite coverage is not equivalence."""
import re
from .common import Failure


RESPONSIBILITY_POLICY='entry-focused-exact-nat-adaptations-v1'
RESPONSIBILITY_GUIDANCE='Author entry behavior, meaningful business branches and nontrivial semantic boundaries. Sources listed as context_dependencies are verified adopted primitives, not separate test targets: exercise them through the assigned entry cases where feasible instead of authoring alias/zero/Suc/addition mini-suites. In arbitrary mode choose meaningful executable representative values above 128 bits when the source computation permits; do not demand one huge case per helper or huge outputs from expensive recurrences. Record expensive untested regions. Preserve source literal-content, generic/non-Clone requirements and checked overflow obligations. This grouping changes neither source semantics nor any frozen suite.'


def responsibility_context(state):
    from .default_adaptations import proposals
    from .native_numeric_contracts import context as native_contracts,SOURCE
    from .task_context import fingerprint
    bundle=state['bundle'];numeric=bundle.get('numeric_policy',{});model=bundle['source_model']
    plan=state.get('partition',bundle.get('segmentation',{}))
    exact={r['source']:r for r in proposals(model,numeric)}
    declared={}
    for row in plan.get('boundaries',[]):declared.setdefault(row.get('source'),[]).append(row)
    candidates={'type:Nat.nat','constant:Nat.zero_nat_inst.zero_nat'}
    if numeric.get('mode')=='arbitrary':candidates.add('constant:Nat.Suc')
    # Checked addition retains its overflow/range obligation. Only the exact
    # verified native arbitrary addition may share the entry's test coverage.
    if numeric.get('mode')=='arbitrary' and native_contracts(state)['contracts']:candidates.add(SOURCE)
    library=numeric.get('numeric_library',{})
    if numeric.get('mode')!='checked' and not (numeric.get('mode')=='arbitrary' and library.get('name')=='dashu-int' and library.get('version')=='=0.6.2'):candidates=set()
    dependencies=sorted(n for n in candidates if n in exact and len(declared.get(n,[]))==1
        and declared[n][0].get('kind') in {'native','inlined'})
    result={'policy':RESPONSIBILITY_POLICY,'context_dependencies':dependencies,
        'verified_source_identities':{n:exact[n]['default_identity'] for n in dependencies},
        'numeric_mode':numeric.get('mode'),'guidance':RESPONSIBILITY_GUIDANCE}
    result['identity']=fingerprint(result);return result


def requirements(state,source_ids):
    rows=[]
    mapped={r['source'] for r in state['mapping'] if r.get('rust_item')}
    dependencies=set(responsibility_context(state)['context_dependencies'])
    for n in sorted(set(source_ids)&mapped):
        # Numeric runtime obligations apply to value-level source operations.
        # A class named divide/modulo is an interface, not an executable value.
        if not n.startswith('constant:') or n in dependencies:continue
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
