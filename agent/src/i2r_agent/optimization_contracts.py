"""Evidence authority for optional performance generation and admission.

This projection never changes the frozen source, partition, mapping or numeric
runtime. Analysis prose remains available as a claim to check, not a new axiom.
"""
from copy import deepcopy

from .common import Failure
from .task_context import fingerprint
from . import optimization_primitives, numeric_interface, optimization_source_authority


POLICY = 'performance-contract-authority-v6'
GUIDANCE = '''Use the supplied performance_contract as the shared evidence hierarchy for optimization and admission. CURRENT extracted source execution equations and types determine business transitions. Abstract representation invariants, typedef/code-abstype obligations, and projection/adapter contracts are also authoritative. Use abstract_representation_roles to distinguish a code representation constructor/projection over its justified source representation domain from a promised unrestricted HOL abstraction operation. An abstraction-marked execution certificate with theorem=null is not an unconditional HOL theorem for every raw constructor value. On the justified representation domain, storing/retrieving the represented payload can implement that certificate without executing the logical abstraction's normalization algorithm. This does not establish that arbitrary raw values belong to that domain. Establish construction/adapter validity or a justified representation relation for the declared source exports and each mapped helper's actual source-domain use. Do not invent standalone source Eq/Hash or full-domain abstraction contracts from Rust derives/public visibility alone; preserve any such contract actually declared by source exports, mappings or adapters. A changed use, reachability, representation domain or invariant dependency must be reviewed even if helper bytes are unchanged. Report inherited and candidate-introduced findings separately for EVERY abstract type; inheritance is neither a new violation nor proof of correctness. Candidate admission concerns CURRENT business computation and obligations introduced, changed or activated by this candidate, including changed use, domain and invariant dependency. An unchanged inherited helper/domain gap must be attributed separately; it does not by itself reject this candidate or prove that the source operation order changed. Preserve genuine mapped-helper obligations when a candidate changes or activates them. A reported inherited violation affecting declared roots creates a baseline-identity-bound publication hold for all modes. Unknown inherited concerns and missing all-input proofs remain recorded; they do not replace or strengthen the existing correctness workflow that qualified the frozen baseline. Executed validation is not a mathematical proof, but lack of a proof is not evidence of a violation. Controller-verified numeric runtime semantics, exact registered primitive contracts, frozen public interfaces, and numeric-domain/overflow obligations remain hard constraints. A partition boundary's source/kind declares a permitted primitive abstraction boundary; it does not erase source or numeric obligations.
Boundary basis/conditions, implementation guidance, mapping descriptions and Rust comments are analysis/author claims. Preserve and check their substantive semantic requirements against the source and trusted numeric contract; do not treat a historical use-site description such as "only used in function X" as a new semantic prohibition on exact primitive lowering elsewhere. Do not discard a real obligation merely because it was also repeated in prose. Resolve apparent conflicts explicitly by citing current equations, actual branch guards and verified runtime semantics. If those authorities do not settle a substantive requirement, leave that correspondence unestablished; a prior accepted candidate or baseline implementation is not a proof.
For a source natural-number Suc k pattern, a Rust branch establishing m != 0 may recover the SAME predecessor k with exact natural subtraction by one. The same holds when an exact primitive helper is inlined or its constant one is hoisted. This is a representation of one source transition, not a new recurrence; a general total Nat subtraction is not permission to take a predecessor on a zero branch. Machine-carrier lowering needs exact conversion/range evidence for every value on that path, a nonzero guard before decrement, safe updates, and a complete exact fallback for values outside that range unless a source-derived bound covers all inputs. Exact guards/fallback are necessary evidence, not an exemption from frozen numeric type/library/generic restrictions or source-derived resident-index bounds. In paired-numeric experiments the ban on implementing mathematical arithmetic with u128/i128 or backend-specific code remains in force. Never infer a machine-range assumption from benchmark data. When implementing the CURRENT fixed source in Rust, keep every logical business visit and its decision/order: using arithmetic to skip countdown positions or replace a recurrence by strided offsets still requires a proved revised source. Apply these Rust-realization rules identically across optimization modes and numeric backends. During source proposal assessment, the controller explicitly permits changing recurrences/visitation through a checked Isabelle equivalence proof and re-extraction; the fixed-source restriction constrains Rust implementation of the resulting equations, not which proved source transformation may be proposed.'''


MATHEMATICAL_CASE_GUIDANCE = """BENCHMARK MATCHING AND MATHEMATICAL CASES: A lookup table or branch recognizing supplied benchmark vectors/answers is forbidden. A general algebraic identity, degenerate-domain case or algorithmic guard that applies to an entire source-defined family is not forbidden merely because some measured inputs satisfy it. Source optimization may propose such a case only with an unconditional Isabelle equivalence over the ORIGINAL exported type/domain and a complete general fallback where needed. A proof does not make a benchmark-answer table acceptable. Rust implementation must then preserve the resulting CURRENT source branches; fixed-source Rust refinement cannot introduce a new algorithmic fast path without that source transition. Judge the actual source transformation and work reduction, not the mere presence of a branch or a favorable measured input. ORIGINAL exported source types, not the type of an internal generic helper, determine the source proposal's domain. A concrete export may be optimized with a concrete helper while preserving existing generic helper/public interfaces; generic exports cannot be specialized or gain new sort/trait bounds. Do not claim a mathematical operation-count lower bound as established without applicable evidence."""
GUIDANCE += '\n' + MATHEMATICAL_CASE_GUIDANCE


def context(state):
    """Same immutable authority projection for author and independent reviewer."""
    numeric = state['bundle'].get('numeric_policy') or {}
    paired = numeric.get('numeric_interface')
    runtime = {'kind': 'frozen_numeric_policy', 'policy': deepcopy(numeric),
               'note': 'No paired-runtime semantics are inferred for an unconfigured backend.'}
    if paired is not None or state['rust_config'].get('numeric_interface') is not None:
        expected = numeric_interface.contract()
        if paired != expected:
            raise Failure('numeric_runtime_changed', 'Performance evidence requires the frozen paired numeric contract')
        numeric_interface.verify_runtime(state['rust_config'])
        runtime = {'kind': 'controller_verified_paired_runtime', 'contract': deepcopy(expected),
                   'verification': 'Both frozen source numeric policy and Rust config match the current controller runtime hashes.'}
    representations = abstract_representation_roles(state)
    return {'policy': POLICY,
            'abstract_representation_roles': representations,
            'representation_adapter_context': ({'files': deepcopy(state.get('connector', {})),
                'rule': 'Frozen actual conversion/use code, not a source theorem or benchmark-domain restriction. Establish obligations for all source inputs, not only observed tests.'} if representations else {}),
            'primitive_operand_symmetry': {'source_laws': optimization_source_authority.context(state),
                                           'runtime_contracts': runtime_symmetry_contracts(runtime)},
            'source_model_sha256': fingerprint(state['bundle']['source_model']),
            'authoritative_evidence': ['current extracted execution equations and source types',
                'abstract representation invariants, projection and adapter obligations',
                'frozen public interfaces and numeric-domain/overflow obligations',
                'verified runtime contract and exact registered native primitive contracts'],
            'numeric_runtime': runtime,
            'registered_native_contracts': optimization_primitives.context(state),
            'analysis_claims': {
                'locations': ['source graph boundaries.basis/conditions', 'mapping descriptions/basis/conditions',
                              'global implementation guidance', 'Rust comments and doc strings'],
                'rule': 'Retained for checking; use-site prose cannot override source/runtime semantics or add restrictions. Substantive guard/domain requirements still need authoritative justification.'},
            'conflict_rule': 'Use current source equations plus verified runtime semantics and actual guards. Unresolved candidate-introduced/changed/activated obligations are uncertain; unchanged inherited concerns belong to baseline findings and uniform publication review, not the candidate decision.'}


def validate_evidence(row, contract=None):
    """Reject inconsistent new admissions without changing legacy readers."""
    evidence = row.get('contract_evidence')
    if (not isinstance(evidence, dict) or not isinstance(evidence.get('obligations'), str) or
            evidence['obligations'] not in {'satisfied', 'violated', 'unknown'} or
            any(not isinstance(evidence.get(k), str) or not evidence[k].strip()
                for k in ['source_and_runtime', 'guards_and_ranges'])):
        raise Failure('invalid_scope_review', 'Admission needs source/runtime and guard/range contract evidence')
    conflicts = evidence.get('advisory_conflicts')
    if not isinstance(conflicts, list) or any(
            not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip()
                                             for k in ['claim', 'authoritative_resolution'])
            for item in conflicts):
        raise Failure('invalid_scope_review', 'Explicitly resolve conflicting analysis claims against source/runtime evidence')
    if row['decision'] == 'within_scope' and evidence['obligations'] != 'satisfied':
        row = {**row, 'decision': 'requires_source_change' if evidence['obligations'] == 'violated' else 'uncertain',
               'reason': 'Primitive/numeric contract evidence does not support admission: ' + row['reason']}
    return validate_abstract_obligations(row, contract)


def annotate_source(source):
    """Attach field-level provenance without removing any declared condition."""
    result = deepcopy(source)
    for row in result.get('boundaries', []):
        row['evidence_provenance'] = {
            'source_and_kind': 'Controller-validated partition structure; source primitive abstraction boundary.',
            'basis_and_conditions': 'Analysis-generated claims; not source equations, checked proofs, or runtime definitions.',
            'obligation_resolution': 'Preserve substantive source/runtime/guard obligations; a historical use-site description alone cannot prohibit equivalent primitive lowering.'}
    return result


PRIMITIVE_SYMMETRY_GUIDANCE = """A local binary primitive operand swap may be the SAME business event when the supplied CURRENT source law applies to that typed operation and the verified runtime preserves both value and definedness. This is local operand symmetry, not reordering computation: keep operand evaluation effects/count/order, primitive-operation sequence/count (e.g. multiply then add), grouping/association, accumulator dependency, recursion and business visits unchanged, with no added generic restrictions. Do not infer laws from Rust trait names or author comments. Code-certificate sort evidence applies only to the typed executable domain and cannot strengthen a logical/public generic interface. Cite controller-supplied source-law and runtime-contract IDs, and explain actual helper correspondence. If either law applicability or runtime/domain correspondence is unknown, use unknown/uncertain. In particular, commutativity does not authorize changing AComp constructor/right/left recursion order or reassociating checked arithmetic: intermediate overflow domains can differ even when mathematical results agree."""
GUIDANCE += '\n' + PRIMITIVE_SYMMETRY_GUIDANCE


def abstract_representation_roles(state):
    """Preserve code-certificate roles without promoting them to HOL theorems."""
    from .program_model import readable
    model = state['bundle']['source_model']; entities = model['entities']; result = []
    for type_id, entity in sorted(entities.items()):
        if entity.get('kind') != 'type' or entity.get('abstract') is not True:
            continue
        constructors = {c['id'] for c in entity.get('constructors', [])}
        certificates = []
        for source_id, source in sorted(entities.items()):
            for index, equation in enumerate(source.get('execution_equations') or []):
                roles = []
                for location, part in [(f'arguments[{i}]', part) for i, part in enumerate(equation['arguments'])] + [('rhs', equation['rhs'])]:
                    abstraction = part.get('abstraction')
                    if abstraction and 'constant:' + abstraction in constructors:
                        roles.append({'location': location, 'abstraction': 'constant:' + abstraction,
                                      'typed_term': deepcopy(part.get('term'))})
                if roles:
                    certificates.append({'source_id': source_id, 'equation_index': index,
                        'equation_sha256': fingerprint(equation), 'abstraction_roles': roles,
                        'execution_certificate': readable({'execution_equations': [equation]})['execution_equations'][0],
                        'logical_theorem_present': equation.get('theorem') is not None,
                        'authority_limit': 'Code-abstraction execution certificate on its representation domain; not an unconditional HOL equation on arbitrary raw constructor inputs.'})
        helpers = constructors | {c['source_id'] for c in certificates}
        result.append({'type_id': type_id, 'abstract': True, 'variables': deepcopy(entity.get('variables', [])),
                       'representation_constructors': deepcopy(entity.get('constructors', [])),
                       'code_certificates': certificates,
                       'declared_source_exports': list(model['entries']),
                       'mapped_representation_helpers': [r for r in state['mapping'] if r['source'] in helpers],
                       'domain_rule': 'Determine applicability from current source types/certificates, declared exports, mappings and actual adapters/uses. Preserve mapped-helper obligations on their justified source domain; do not infer an unrestricted HOL abstraction API solely from a raw Rust constructor or derived traits.'})
    return result


def runtime_symmetry_contracts(runtime):
    # Audited exact runtime version: mathematical sum/product in arbitrary mode,
    # checked_add/checked_mul in checked mode. Assignment forms use those same
    # operations. A different runtime hash needs review before this rule applies.
    audited = '563485bddf8b4e5fa94deb1af6aa76cf788f48ca664d29825fcb88c91beae702'
    if (runtime['kind'] != 'controller_verified_paired_runtime' or
            runtime['contract'].get('runtime_sha256') != audited):
        return []
    rows = []
    for primitive, operation in [('constant:Groups.plus_class.plus', 'addition'),
                                  ('constant:Groups.times_class.times', 'multiplication')]:
        row = {'primitive': primitive, 'runtime_sha256': audited, 'types': ['i2r_numeric::Nat', 'i2r_numeric::Int'],
               'transformation': 'swap the two operands of ONE existing binary operation',
               'value_and_definedness': 'The exact mathematical ' + operation + ' is symmetric. Both operand orders have the same result and representability; checked arithmetic reports the same overflow domain for this single operation.',
               'implementation': 'Owned/borrowed and assignment forms use exact arbitrary operations or the same checked_add/checked_mul with explicit Overflow.',
               'limits': 'No reassociation, changed evaluation effects/count/order, skipped operations, arbitrary custom Rust trait implementation, backend-specific rewrite or business-event permutation.'}
        row['evidence_id'] = 'runtime-symmetry:' + fingerprint(row); rows.append(row)
    return rows


def primitive_equivalence(event, source_id, contract):
    """Validate claimed local symmetry against controller evidence, not prose."""
    evidence = event.get('primitive_equivalence')
    if evidence is None:
        return False, False
    if (not isinstance(evidence, dict) or not isinstance(evidence.get('kind'), str) or evidence['kind'] not in {'operand_symmetry', 'reassociation', 'other'} or
            not isinstance(evidence.get('explanation'), str) or not evidence['explanation'].strip()):
        raise Failure('invalid_scope_review', 'Primitive equivalence needs a structured kind and actual source/Rust explanation')
    flags = ['same_operand_evaluation', 'same_primitive_sequence', 'same_association',
             'same_recurrence_and_visits', 'no_new_generic_restrictions']
    if any(type(evidence.get(k)) is not bool for k in flags):
        raise Failure('invalid_scope_review', 'Primitive equivalence must compare evaluation, sequence, association, visits and generic restrictions')
    status = evidence.get('value_and_definedness')
    if not isinstance(status, str) or status not in {'preserved', 'changed', 'unknown'}:
        raise Failure('invalid_scope_review', 'Classify primitive value and definedness correspondence')
    for key in ['source_law_id', 'runtime_contract_id', 'primitive']:
        if evidence.get(key) is not None and not isinstance(evidence[key], str):
            raise Failure('invalid_scope_review', 'Primitive evidence references must be strings or null when unknown')
    implementation = evidence.get('implementation_domain')
    if (not isinstance(implementation, str) or implementation not in {'verified_concrete', 'source_lawful_generic', 'unknown'} or
            not isinstance(evidence.get('implementation_evidence'), str) or not evidence['implementation_evidence'].strip()):
        raise Failure('invalid_scope_review', 'Explain concrete-instance or generic default/override correspondence; a numeric runtime hash alone does not prove arbitrary trait implementations')
    changed = evidence['kind'] != 'operand_symmetry' or status == 'changed' or not all(evidence[k] for k in flags)
    authority = (contract or {}).get('primitive_operand_symmetry', {})
    source = next((r for r in authority.get('source_laws', {}).get('evidence', [])
                   if r['evidence_id'] == evidence.get('source_law_id')), None)
    runtime = next((r for r in authority.get('runtime_contracts', [])
                    if r['evidence_id'] == evidence.get('runtime_contract_id')), None)
    established = (source is not None and runtime is not None and source['source_id'] == source_id and
                   source['primitive'] == runtime['primitive'] == evidence.get('primitive'))
    return changed, status == 'unknown' or implementation == 'unknown' or not established


def validate_abstract_obligations(row, contract):
    roles = (contract or {}).get('abstract_representation_roles', [])
    expected = {r['type_id'] for r in roles}
    if not expected:
        return row
    rows = row.get('abstract_type_obligations')
    if (not isinstance(rows, list) or len(rows) != len(expected) or
            any(not isinstance(r, dict) or not isinstance(r.get('type_id'), str) for r in rows) or
            {r['type_id'] for r in rows} != expected):
        raise Failure('invalid_scope_review', 'Review candidate changes and usage for every supplied abstract type')
    changed = False; unknown = False
    for item in rows:
        if not isinstance(item.get('role'), str) or item['role'] not in {'code_representation', 'full_hol_abstraction', 'mixed', 'unknown'}:
            raise Failure('invalid_scope_review', 'Distinguish code representation and declared HOL abstraction responsibilities')
        for key in ['source_domain_evidence', 'construction_and_adapter_evidence', 'mapped_helper_evidence']:
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise Failure('invalid_scope_review', 'Compare actual source-domain, construction/adapter and mapped-helper changes')
        flags = ['usage_or_reachability_changed', 'invariant_dependency_changed']
        if any(type(item.get(key)) is not bool for key in flags):
            raise Failure('invalid_scope_review', 'Compare changed use/reachability and invariant dependencies even for unchanged helper bytes')
        scope = item.get('change_scope')
        if not isinstance(scope, str) or scope not in {'unchanged_helpers_and_use', 'modified_or_activated', 'unknown'}:
            raise Failure('invalid_scope_review', 'Attribute candidate-relevant changes separately from inherited findings')
        if scope == 'unchanged_helpers_and_use' and any(item[key] for key in flags):
            raise Failure('invalid_scope_review', 'New usage or invariant dependence cannot be classified as unchanged')
        finding = item.get('candidate')
        if (not isinstance(finding, dict) or not isinstance(finding.get('status'), str) or
                finding['status'] not in {'satisfied', 'violated', 'unknown', 'outside_declared_domain'} or
                not isinstance(finding.get('evidence'), str) or not finding['evidence'].strip()):
            raise Failure('invalid_scope_review', 'Classify candidate-introduced or activated obligations with actual source/diff evidence')
        if item['role'] == 'unknown':
            if scope != 'unchanged_helpers_and_use':
                unknown = True
            elif not any(item['type_id'] in f.get('source_ids', []) for f in row.get('inherited_baseline_findings', [])):
                raise Failure('invalid_scope_review', 'Disclose an explicitly unknown inherited abstract role as a baseline finding')
        changed |= finding['status'] == 'violated'
        unknown |= finding['status'] == 'unknown' or scope == 'unknown'
    if row['decision'] == 'within_scope' and (changed or unknown):
        return {**row, 'decision': 'requires_source_change' if changed else 'uncertain',
                'reason': 'Candidate-introduced or activated abstract-type obligations are violated or unestablished: ' + row['reason']}
    return row
