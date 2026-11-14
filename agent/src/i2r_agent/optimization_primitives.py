"""Exact primitive adapters available only inside the performance workflow.

Re-extraction can introduce new library operations. Availability is recomputed
from that current graph, without changing the original generation defaults or
silently committing boundaries. Both optimization modes use this same catalog.
"""
from copy import deepcopy

from . import default_adaptations, native_numeric_contracts, numeric_interface
from .common import Failure
from .segmentation import graph, project_functions
from .task_context import fingerprint

POLICY = 'performance-paired-primitive-adapters-v1'
NAT = {'kind': 'type', 'name': 'Nat.nat', 'args': []}
INT = {'kind': 'type', 'name': 'Int.int', 'args': []}
BOOL = {'kind': 'type', 'name': 'HOL.bool', 'args': []}


def arrow(a, b):
    return {'kind': 'type', 'name': 'fun', 'args': [a, b]}


# Observed Isabelle2025 executable identities; fixtures retain their complete
# operational fields and extraction provenance. A name alone never matches.
SPECS = [
    ('Nat.plus_nat_inst.plus_nat', '958ba272699f71150886667a1197fc23078a426e15e6859f61b171dac81964c7', NAT, NAT, 2, 'exact natural addition', 'Nat + Nat; Nat::try_add'),
    ('Nat.times_nat_inst.times_nat', 'f5b8644cf2962ad61b2db411ed37b77131b99615609df1892f9600643f6c7fb0', NAT, NAT, 2, 'exact natural multiplication', 'Nat * Nat; Nat::try_mul'),
    ('Nat.minus_nat_inst.minus_nat', '99c397b31776443c1be0e2171547601cb032e68ad02d308d30b0ea5eda26d60b', NAT, NAT, 2, 'natural subtraction truncated at zero', 'Nat - Nat; Nat::sub_trunc'),
    ('Nat.equal_nat_inst.equal_nat', '618802cc897e074cf10233bc432ef1437a31d01afeb3781c6dca698119f348fc', NAT, BOOL, 2, 'natural equality', 'Nat == Nat'),
    ('Nat.ord_nat_inst.less_eq_nat', '0096ce3f147f8adedd118c355fda5edc8ed59c187564c82c35db840f813de665', NAT, BOOL, 2, 'natural less than or equal', 'Nat <= Nat'),
    ('Nat.ord_nat_inst.less_nat', '32afb920e87569ff6d9b761c511ce5188d7b4c629aca3cf59108c6d0e9079b04', NAT, BOOL, 2, 'natural less than', 'Nat < Nat'),
    ('Euclidean_Rings.divide_nat_inst.divide_nat', '9a3cda152ec562a7b4ab12964686f3eeb1e929a4abd2554b4c4a219f9d0e3c7d', NAT, NAT, 2, 'natural division, with division by zero equal to zero', 'Nat / Nat'),
    ('Int.plus_int_inst.plus_int', '299205629314d48b45768976c9d8416a5a5b844b62a7612a63ad511f9f9ce5df', INT, INT, 2, 'exact integer addition', 'Int + Int; Int::try_add'),
    ('Int.minus_int_inst.minus_int', '5925cd04cffbf1601b7a8e91e44f9999e83555266cc29ab8259bd6f3cb85b6f2', INT, INT, 2, 'exact integer subtraction', 'Int - Int; Int::try_sub'),
    ('Int.times_int_inst.times_int', '99aa039fa95916a827ae4d2420898889bd3076a3abba2a1b6dfb9d2c806f126e', INT, INT, 2, 'exact integer multiplication', 'Int * Int; Int::try_mul'),
    ('Int.uminus_int_inst.uminus_int', '862a72e222eaa061e37c51790e74957e444c43352b866a0c046dd9a8a6fb7e6d', INT, INT, 1, 'exact integer negation', '-Int; Int::try_neg'),
    ('Int.equal_int_inst.equal_int', 'ca1b378a9eedac45fc4e4d75acf33b3b505e6f0967f4c3ee6750d84b14ee57bf', INT, BOOL, 2, 'integer equality', 'Int == Int'),
]
GUIDANCE = '''Available adapters are proposals, not active boundaries or proof of a candidate. To use one, explicitly include its source/kind/basis/conditions in the COMPLETE boundaries list of the ordinary rust proposal. Keep other required boundaries. The partitioner and mapping checks still apply. Active contracts require that declaration plus exact current source identity/type, a non-business library entity, and the frozen paired numeric runtime. A registered library operation uses its backend implementation rather than the recursive presentation of its source equations. This permission does not extend to a user-defined arithmetic/business function, unregistered generic operation, or replacement of a business recurrence. A source equivalence proof may introduce a registered primitive into the new graph; recompute availability from that graph. Preserve operand evaluation and business event order, source domains, generic constraints and explicit checked overflow. Source tests and frozen observations remain required. These are trusted lowering contracts with runtime tests, not new HOL equivalence proofs of Rust.'''


def context(state):
    numeric = state['bundle'].get('numeric_policy') or {}
    if not numeric.get('numeric_interface'):
        # Legacy correctness and non-paired adapters retain their old authority.
        return native_numeric_contracts.context(state)
    runtime = numeric_interface.contract()
    if numeric.get('mode') != 'arbitrary' or numeric['numeric_interface'] != runtime:
        raise Failure('numeric_runtime_changed', 'Performance primitives require the frozen paired generation policy')
    numeric_interface.verify_runtime(state['rust_config'])
    model = state['bundle']['source_model']
    reachable = graph(model)['edges']; mandatory = project_functions(model)
    plan = state.get('partition', state['bundle'].get('segmentation', {}))
    declared = {}
    for row in plan.get('boundaries', []):
        declared.setdefault(row.get('source'), []).append(row)
    available = default_adaptations.proposals(model, numeric)
    contracts = []
    for name, sha, operand, result, arity, operation, api in SPECS:
        source = 'constant:' + name; entity = model['entities'].get(source)
        typ = arrow(operand, result) if arity == 1 else arrow(operand, arrow(operand, result))
        if (source not in reachable or source in mandatory or not entity or
                entity.get('source_type') != typ or default_adaptations.operational_identity(entity) != sha):
            continue
        contract = {'source': source, 'source_operational_sha256': sha, 'source_type': deepcopy(typ),
            'operation': operation, 'implementation': api + ' through i2r_numeric; owned or borrowed operands',
            'execution_contract': 'Use the exact backend primitive; unary/value-proportional unfolding of this library operation is not required.',
            'numeric_mode': 'paired', 'numeric_policy_sha256': fingerprint(numeric),
            'numeric_runtime_sha256': runtime['runtime_sha256'],
            'limits': 'Arbitrary is exact; checked rejects every unrepresentable intermediate/result with I2R_NUMERIC_OVERFLOW. No wrap, narrowing, reassociation, backend-specific business code, or replacement of another source function.',
            'source_semantics': 'Current matched executable equations and type remain authoritative; this entry supplies a lowering contract, not expected output values.'}
        contract['identity'] = fingerprint(contract)
        proposal = {'source': source, 'kind': 'native',
            'basis': 'Exact Isabelle2025 source identity/type and frozen paired runtime: ' + operation,
            'conditions': [contract['implementation'], contract['execution_contract'], contract['limits']],
            'primitive_contract_identity': contract['identity'], 'adapter_policy': POLICY}
        available = [r for r in available if r['source'] != source] + [proposal]
        declarations = declared.get(source, [])
        if len(declarations) == 1 and declarations[0].get('kind') in {'native', 'inlined'}:
            contract['declared_boundary_kind'] = declarations[0]['kind']
            contract['identity'] = fingerprint(contract)
            contracts.append(contract)
    material = {'policy': POLICY, 'contracts': contracts, 'available_adapters': available,
                'guidance': GUIDANCE, 'declaration_policy': 'No automatic boundary insertion. Model prose cannot create or widen a registry entry.'}
    material['identity'] = fingerprint(material)
    return material
