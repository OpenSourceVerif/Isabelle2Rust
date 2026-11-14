"""Independent source-correspondence acceptance over immutable candidate versions.

This audit does not generate code, tests, proofs, or performance targets. It can
only approve an existing validated candidate or fall back to an earlier one.
"""
from copy import deepcopy
from pathlib import Path
import json
import difflib
import hashlib
import time
from .common import Failure, digest, now, read, save
from .request_budget import atomic_save
from .task_context import fingerprint
from .translation_workflow import version
from .program_model import readable
from . import optimization_contracts, optimization_baseline_quality as baseline_quality


SYSTEM = '''Independently audit source correspondence for a performance ablation. You are not the optimization author. Do not propose code, new tests, target runtimes or edits. Judge each candidate's CURRENT business computation and introduced/changed/activated obligations against its supplied source equations. The frozen baseline validation is executed historical evidence, not a proof. Report inherited baseline findings separately; unchanged helper bytes AND unchanged use/domain/invariant dependence must not alone cause candidate rejection. A prior candidate is not proof of a new change. No timing results or author justifications are supplied.
The Rust-refinement scope preserves the source computation. Allowed: ownership and buffer reuse, eliminating representation-induced copies/allocations/conversions, inlining, fusion/deforestation preserving source visitation and element-operation order, resident-container index lowering with a valid bound and arbitrary-value behavior, loop unrolling of the same transition, and exact local primitive strength reduction. Ordinary constant propagation and simplifying primitive operations on constructor-known values are allowed when exact for every source value; they do not by themselves constitute a new algorithm. Disallowed without a proved revised source: a different mathematical algorithm, an unproved closed-form replacement of the source recurrence, removing logical iterations/marking work using a new algorithmic invariant, or replacing a source business algorithm by a different library algorithm. Preserving observable results alone does not establish membership in this ablation arm. A retained public helper that is bypassed by the actual exported hot path does not establish source correspondence.
For a candidate tagged with checked source equivalence, use its REVISED source equations, not the old source. The controller has separately checked its proof, types, compilation and frozen tests. Judge whether its Rust realization corresponds to that supplied graph.
Also reject benchmark answer tables, environment/timing detection, arbitrary numeric narrowing without a complete exact path, newly strengthened generic bounds relative to the supplied frozen interfaces, or new assumptions absent from the source. Existing unchanged baseline interface constraints are outside this audit: do not attribute them to the optimization. A bounded stack/heap storage choice with unchanged computation is permitted; hardcoded benchmark answers are not. If uncertain, return uncertain; never assume an author claim is a proof.
Return one JSON object: {"reviews":[{"candidate_id":"exact supplied id","decision":"within_scope|requires_source_change|uncertain","reason":"concise source/code evidence","source_ids":["relevant supplied source IDs"]}]}. Include every candidate exactly once. Be concise.'''

COMPUTATION_PRESERVATION_CONTRACT = """Changes introduced or activated by fixed-source Rust refinement preserve the CURRENT supplied source equations, their recursive/accumulator dependencies, source visitation, and element-operation/constructor order. Attribute a violation using the actual original and parent Rust, not by substituting the HOL trace for the prior Rust trace. An unchanged computation with unchanged use/domain/invariant dependence inherited from the correctness-qualified original is not an optimization-introduced algorithm change; record that history separately. This does not excuse newly activated flaws, new domain restrictions, or a realization that fails genuinely revised, proved source equations. Exact local binary operand symmetry can preserve one primitive event only under the separately supplied source-law and runtime-definedness evidence; it never permutes business events or changes association. Final result order and the order of operations constructing that result are different: equal complete outputs do not establish preserved computation. For example, a current equation fold(left, fold(right, cons(op, acc))) requires the cons/op transition before the right recursive transition, then the left transition; emitting left, right, op into a fresh prefix and appending acc changes that recurrence even when the final list agrees. A checked source transformation may establish new authoritative equations before Rust refinement; a theorem about output equality or an earlier accepted Rust candidate does not waive these rules.
Pure storage operations may encode/decode the SAME business transitions, for example push into a reversed buffer to implement cons, followed by one final decode. A pure capacity-sizing or representation-metadata prepass is distinct from business construction and may add its own reads/counts; explain and exclude those metadata events when aligning the original business recurrence/node/element operations. It cannot replace, reorder, or change the verdict on an otherwise identical business traversal. The two full implementation traces need not be literally identical. Existing contract-approved native/container primitives retain their established abstraction boundary and permitted representation simplifications. For example, when a source root is append and its approved exact primitive contract permits an empty-right fast path returning the owned left container, that remains allowed: internal list-cell/container transport is not a new mandatory business transition. Do not infer business visitation obligations from the physical implementation of an approved primitive, and do not use this allowance to erase an actual source business recurrence or element computation. This is the declared experimental source-level refinement boundary, not a claim that pure HOL equality imposes machine evaluation order.
List-spine allocation and linking that only store already-computed payloads are representation operations, not an additional mandatory business-constructor schedule. For a structural map, a forward push loop and an exact-order iterator map/extend may encode the same source recurrence: each logical input cell is visited once, each callback executes exactly once head-to-tail, and the returned sequence decodes to the same list. Neither capacity reservation nor changing this storage spelling changes that business trace. This does not allow callback reordering, removing logical visits, or changing accumulator-dependent calculations. Distinguish a list link from a domain constructor or computation, such as emitting an ADD instruction before recursing into the right and left children; changing those domain events still requires a proved source rewrite. Compare both original/parent diffs before attributing a transition change: a forward storage schedule already present in the original cannot become a newly introduced business-order violation merely because push becomes extend. Any genuinely activated numeric/domain obligation still needs its own evidence.
Rust comments, doc strings, and mapping descriptions/basis/conditions are AUTHOR CLAIMS, not authoritative source equations, checked proofs, or evidence that order is preserved. Compare the actual hot-path bodies with the controller-supplied CURRENT execution equations. Do not copy an older equation from a comment or infer preserved order from the phrase 'source order'. If correspondence is unknown, do not accept the candidate."""


ONLINE_SYSTEM = SYSTEM + '\n' + COMPUTATION_PRESERVATION_CONTRACT + '\n' + optimization_contracts.GUIDANCE + '''
This decision is an admission gate BEFORE any candidate becomes the next search state. Apply the SAME computation-preservation boundary to every numeric backend and optimization mode. Never waive it because a candidate is fast or is in Full mode.
In particular, a source countdown that visits every flag and subtracts one cannot be replaced in the Rust-only route by directly visiting m, m+n+1, m+2*(n+1), ... . Copied-through source positions are still logical iterations. Mathematical equivalence of those offsets is not source-correspondence evidence. This rewrite requires a revised source definition, a checked equality proof, and re-extraction. Conversely, if that strided computation is explicitly in the supplied proved REVISED equations, realizing those equations is allowed.
For EACH review also return "contract_evidence": {"obligations":"satisfied|violated|unknown", "source_and_runtime":"current source and verified primitive semantics, or explain why no primitive is affected", "guards_and_ranges":"actual branch guards, exact carrier/fallback and overflow obligations, or explain why none apply", "advisory_conflicts":[{"claim":"conflicting analysis prose", "authoritative_resolution":"current source/runtime/guard evidence resolving it"}]}. Use an empty conflicts list only when none occur. Analysis prose alone cannot establish a semantic violation. Here obligations means CURRENT business correspondence and obligations introduced, changed or activated by this candidate. Unresolved candidate-relevant obligations require unknown/uncertain and violations cannot accompany within_scope. Put unchanged inherited baseline concerns in inherited_baseline_findings, not candidate contract_evidence or transition flags.
For EACH review return "transition_evidence": {"eliminated_source_iterations": false, "changed_source_recurrence": false, "changed_source_marking_schedule": false, "changed_source_operation_order": false, "explanation": "compare actual business transitions, not only final outputs"}. All four booleans describe candidate-introduced or activated transition changes relative to the CURRENT source equations, which may already carry a checked rewrite. Establish introduction/activation from the actual original/parent Rust diffs; an unchanged inherited schedule belongs in baseline findings, not these flags. Do not set these flags merely because a separate inherited helper contract is unproved. A true flag cannot accompany within_scope.
For EACH current abstract type in performance_contract.abstract_representation_roles, return exactly one "abstract_type_obligations" row: {"type_id":"supplied type ID", "role":"code_representation|full_hol_abstraction|mixed|unknown", "source_domain_evidence":"identify representation domain and declared source exports, distinguishing code certificates from unconditional HOL theorems", "construction_and_adapter_evidence":"compare actual constructors/adapters and candidate changes to their use/domain", "mapped_helper_evidence":"compare applicable mapped-helper responsibilities against complete original/parent diffs", "usage_or_reachability_changed":false, "invariant_dependency_changed":false, "change_scope":"unchanged_helpers_and_use|modified_or_activated|unknown", "candidate":{"status":"satisfied|violated|unknown|outside_declared_domain", "evidence":"only the candidate's introduced/changed/activated obligations, never a rejection solely because an inherited helper was already unproved"}}. No abstract types permits an omitted/empty array. Unchanged bytes are insufficient if usage/reachability/domain/invariant dependence changes. Actual new restrictions, activated flaws, or uncertain new applicability must still reject/hold the candidate. An explicitly unknown unchanged abstract role must have a corresponding inherited baseline finding; an unknown modified/activated role cannot establish candidate admission. Unknown inherited source-domain quality by itself belongs in baseline findings; it must not be relabeled a candidate transition change.
Separately return "inherited_baseline_findings": [{"source_ids":["exact original source IDs from baseline_validation"], "status":"violated|unknown|claim_limit", "declared_root_impact":"affected|unknown|not_affected", "finding":"specific inherited finding, or a limit on stronger undeclared helper/API claims", "evidence":"original source/code/adapter basis and why declared roots are affected, unaffected, or applicability is unknown"}]. Omit/use [] if none. The controller binds this to the supplied baseline_validation identity. Only a reported violation (status=violated) whose root impact is affected/unknown creates a publication hold on Off, Rust-only AND Full; it does not change candidate admission. Unknown inherited concerns and claim limits remain visible without replacing the original correctness qualification. Use violated for a concrete contradiction of a declared obligation, supported by a counterexample or direct source/code argument; merely lacking an all-input proof, or seeing a theorem=null code certificate, is unknown or a claim limit, not a violation. This does not relax uncertainty about candidate-introduced/activated obligations. Do not claim the baseline is mathematically proved, infer a standalone HOL API contract from a Rust derive/public helper, erase an inherited finding because one candidate repairs it, or silently discard concerns from rejected candidates. A candidate repair is judged as a candidate change; baseline publication hold is resolved separately for the whole cohort, never automatically by that repair or another mode's positive review.
Also return a nonempty "operation_order_evidence" array covering affected business recurrences/cases on the actual exported hot path. Each row is {"source_id":"exact supplied current source ID", "source_equation":"exact current execution equation/case", "events":[{"id":"event_1", "source_operation":"source business transition", "rust_operation":"corresponding Rust business transition", "rust_locations":["actual helper and case"], "correspondence":"same_transition|different_transition|unknown"}], "source_order":["event_1"], "rust_order":["event_1"], "identity_case":false, "representation_relation":"identity or explicit encode/decode preserving the same business transitions", "comparison":"preserved|changed|unknown"}.
Event IDs are local to the row and unique in the events table. Both order arrays reference only those IDs; include every event with a source_operation in source_order and every event with a rust_operation in rust_order. A repeated occurrence of the SAME operation may repeat its ID; distinct business operations/children/branches require distinct IDs. The two operand orders of the SAME locally symmetric primitive may share an ID only with the primitive_equivalence evidence below. Preserve occurrence counts and actual order. Use null for the missing side of an added/deleted business operation, with different_transition. same_transition asserts semantic correspondence under the stated representation relation, not identical wording: source "construct False" may correspond to Rust "write false", and source predecessor k may correspond to guarded m-1. Do not relabel unequal transitions as the same event. Distinct primitive operand roles may correspond only under the local operand-symmetry rule below; distinct business children/branches must retain distinct events.
Whenever an event uses primitive operand symmetry, add "primitive_equivalence": {"kind":"operand_symmetry|reassociation|other", "primitive":"exact source primitive ID", "source_law_id":"supplied source-law evidence_id or null if unknown", "runtime_contract_id":"supplied runtime-symmetry evidence_id or null if unknown", "same_operand_evaluation":true, "same_primitive_sequence":true, "same_association":true, "same_recurrence_and_visits":true, "no_new_generic_restrictions":true, "value_and_definedness":"preserved|changed|unknown", "implementation_domain":"verified_concrete|source_lawful_generic|unknown", "implementation_evidence":"identify actual concrete instance, or source-lawful generic domain and every affected default/override implementation; a Nat/Int runtime hash is not evidence for arbitrary custom Rust overrides", "explanation":"map actual source primitive and runtime/helper operations, operands, all-input domain and unchanged effects/count/order"}. The containing row's source_id must be the typed source occurrence named by that law. A fully established local symmetry uses correspondence=same_transition and the same event ID on both sides. Ordinary direct/representation correspondences need no primitive_equivalence field. Do not omit this field when relying on an algebraic law. Unprovided laws, guessed names, unknown runtime/trait correspondence or changed checked overflow domains cannot establish admission. Reassociation is not licensed by this local symmetry rule. Record unknown when correspondence cannot be established.
Extract source operations from the current equation first, then align actual Rust bodies. Exclude explained pure storage encode/decode, metadata-only prepasses, and internal details of approved primitives from these BUSINESS traces; never omit an actual business operation. A nonempty trace cannot use identity_case=true. Only a source identity case with no business transition (including an approved primitive identity fast path) may use events=[], source_order=[], rust_order=[], identity_case=true, with its justification in representation_relation. within_scope requires all event correspondences same_transition, equal ID sequences (including repetitions), and comparison=preserved. Changed orders, missing business operations or different transitions require changed; unknown correspondence requires uncertain. No timing results are supplied. Return JSON.'''


ONLINE_SYSTEM += '''
Rejection must be attributed to this candidate, not merely to an inherited source/Rust discrepancy. For a negative decision return a nonempty "rejection_changes" array. Each item has "origin":"introduced|activated|unknown|revised_source", "reference":"original|parent", "source_ids":["current source IDs"], "before":{"path":"src/lib.rs","excerpt":"exact focused code excerpt"}, "after":{"path":"src/lib.rs","excerpt":"exact focused code excerpt"}, "before_events":["business event IDs or domain/guard obligations in that BEFORE Rust excerpt"], "after_events":["the same vocabulary for the AFTER Rust excerpt"], and "explanation":"the new/activated candidate obligation and its connection to the cited code". The before trace describes actual prior Rust, NOT the HOL source trace. Do not count buffer capacity, comments or list-spine storage as changed business events. If the implicated behavior and its use/domain are inherited unchanged, put it in inherited_baseline_findings and do not use it to reject this candidate. Activated obligations must cite the changed caller/guard/use, not identical helper text. revised_source is reserved for a checked changed source graph; then before may be null and the explanation must identify the unmet REVISED equation. Unknown NEW obligations still require uncertain. Unsupported or self-contradictory rejection evidence receives only the existing bounded evidence repair, never automatic approval.
For new inherited_baseline_findings also give "obligation_kind":"observable_semantics|source_domain|numeric_contract|public_contract|source_computation_history|claim_limit". A different pure evaluation/partition schedule already present in the original is source_computation_history, not by itself a behavioral correctness violation. Such history is recorded as claim_limit/unknown, never violated without a separate concrete semantic/domain contradiction. The Rust-only computation-preservation restriction applies to changes introduced/activated by optimization, not retrospectively to the original correctness-qualified transpilation. Actual inherited semantic/domain violations still hold all modes.
'''


def validate_rejection_attribution(row, original, state, parent=None):
    """Require grounded before/after evidence; never turn a rejection into approval."""
    for finding in row.get('inherited_baseline_findings', []):
        kind = finding.get('obligation_kind')
        if not isinstance(kind, str) or kind not in {'observable_semantics', 'source_domain', 'numeric_contract',
                        'public_contract', 'source_computation_history', 'claim_limit'}:
            raise Failure('invalid_scope_review', 'Classify each inherited finding by obligation_kind')
        if kind in {'source_computation_history', 'claim_limit'} and finding['status'] == 'violated':
            raise Failure('invalid_scope_review', 'Historical computation shape alone is not a baseline semantic violation')
    if row['decision'] == 'within_scope':
        return
    changes = row.get('rejection_changes')
    if not isinstance(changes, list) or not changes:
        raise Failure('invalid_scope_review', 'Negative admission needs grounded rejection_changes relative to actual prior Rust')
    parent = original if parent is None else parent
    revised = (fingerprint(original['bundle']['source_model']) != fingerprint(state['bundle']['source_model'])
               and state['bundle'].get('source_equivalence', {}).get('status') == 'proved')
    def excerpt(value, files):
        if (not isinstance(value, dict) or not isinstance(value.get('path'), str)
                or not isinstance(value.get('excerpt'), str) or not value['excerpt'].strip()
                or value['path'] not in files or value['excerpt'] not in files[value['path']]):
            raise Failure('invalid_scope_review', 'Rejection excerpts must occur verbatim in the supplied before/after files')
        return value['excerpt']
    for change in changes:
        if (not isinstance(change, dict) or not isinstance(change.get('origin'), str)
                or change['origin'] not in {'introduced', 'activated', 'unknown', 'revised_source'}):
            raise Failure('invalid_scope_review', 'Inherited unchanged behavior is not a candidate rejection origin')
        ids = change.get('source_ids')
        if (not isinstance(ids, list) or not ids or any(not isinstance(n, str) or n not in state['bundle']['source_model']['entities'] for n in ids)
                or not isinstance(change.get('explanation'), str) or not change['explanation'].strip()):
            raise Failure('invalid_scope_review', 'Rejection changes need current source IDs and an attribution explanation')
        after = excerpt(change.get('after'), state['files'])
        if change['origin'] == 'revised_source':
            if not revised:
                raise Failure('invalid_scope_review', 'revised_source requires an actual checked source-model change')
            continue
        reference = change.get('reference')
        if not isinstance(reference, str) or reference not in {'original', 'parent'}:
            raise Failure('invalid_scope_review', 'Name the original or exact parent attribution reference')
        before = excerpt(change.get('before'), (original if reference == 'original' else parent)['files'])
        for key in ['before_events', 'after_events']:
            if not isinstance(change.get(key), list) or any(not isinstance(v, str) or not v.strip() for v in change[key]):
                raise Failure('invalid_scope_review', 'Provide comparable before/after business or obligation traces')
        if before == after or change['before_events'] == change['after_events']:
            raise Failure('invalid_scope_review', 'Unchanged implicated code/obligation cannot justify candidate rejection; cite changed use/domain or record inherited history separately')


def normalize_admission_envelope(reply):
    """Move unambiguous single-review evidence without changing its contents.

    Providers sometimes place evidence beside ``reviews``. Only a single review
    with no duplicate fields has an unambiguous recipient; all evidence still
    goes through the complete semantic validator below.
    """
    if not isinstance(reply, dict): return reply, []
    fields = sorted(set(reply) & {'contract_evidence', 'transition_evidence',
        'operation_order_evidence', 'abstract_type_obligations', 'inherited_baseline_findings', 'rejection_changes'})
    if not fields: return reply, []
    rows = reply.get('reviews')
    if (not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)
            or any(key in rows[0] for key in fields)):
        raise Failure('invalid_scope_review', 'Ambiguous or duplicate top-level review evidence')
    normalized = deepcopy(reply)
    for key in fields: normalized['reviews'][0][key] = normalized.pop(key)
    return normalized, fields


def admit(original, state, record, provider, budget, directory, parent=None):
    """Cached, charged admission against the exact current source and files."""
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    from .optimization_protocol import interfaces
    option = {'id': Path(record['path']).name, 'state': state, 'record': record}
    payload = admission_payload(original, option, parent)
    identity = admission_identity(original, option, payload)
    # The cache is independent of attempt number. An unchanged candidate must
    # never acquire a different decision merely because it was retried.
    cache = directory.parent / 'scope-cache' / (fingerprint(identity) + '.json')
    if cache.exists():
        report = read(cache)
        if report['identity'] != identity: raise Failure('scope_cache_changed', str(cache))
        report = {**report, 'cached': True, 'model_calls': 0}
    else:
        before = provider.calls; started = time.monotonic()
        request_payload = payload; format_errors = []
        for retry in range(2):
            try:
                reply = budget.call(provider, request_payload, system=ONLINE_SYSTEM, phase='performance_scope_admission')
                raw_reply = reply
                reply, moved = normalize_admission_envelope(reply)
                if moved:
                    save(directory / 'scope-envelope-normalization.json', {
                        'moved_fields': moved, 'original_sha256': fingerprint(raw_reply),
                        'normalized_sha256': fingerprint(reply), 'values_unchanged': True})
                row = validate_admission_reply(reply, option['id'], state['bundle']['source_model']['entities'],
                                               payload['candidates'][0]['performance_contract'], payload['baseline_validation'])
                validate_rejection_attribution(row, original, state, parent)
                break
            except Failure as error:
                if error.code not in {'invalid_model_response', 'invalid_scope_review', 'incomplete_response'}:
                    raise
                format_errors.append({'code': error.code, 'message': str(error), 'evidence': error.evidence})
                save(directory / 'scope-format-errors.json', format_errors)
                if retry: raise
                request_payload = {**payload, 'response_format_feedback': {
                    'code': error.code, 'message': str(error),
                    'instruction': 'One schema repair for the SAME candidate and evidence. Return complete valid JSON using the required review schema. No valid semantic decision has been obtained; do not assume approval or rejection.'}}
        report = {'identity': identity, 'review': row, 'model_calls': provider.calls-before,
                  'seconds': time.monotonic()-started, 'cached': False,
                  'baseline_validation': payload['baseline_validation'], 'format_errors': format_errors}
        save(cache, report)
    # IDs are display references, not part of the cached semantic decision.
    # Cached reviews obey this policy's schema too. Legacy completed results
    # are read through the existing readers, never migrated through admit.
    if report.get('baseline_validation') != payload['baseline_validation']:
        raise Failure('scope_cache_changed', 'Baseline evidence binding changed')
    row = validate_admission_reply(
        {'reviews': [{**report['review'], 'candidate_id': option['id']}]},
        option['id'], state['bundle']['source_model']['entities'],
                                       payload['candidates'][0]['performance_contract'], payload['baseline_validation'])
    validate_rejection_attribution(row, original, state, parent)
    report = {**report, 'review': row}
    path = directory / 'scope-admission.json'; save(path, report)
    if report['review']['decision'] != 'within_scope':
        raise Failure('optimization_scope_rejected', report['review']['reason'],
                      {'review': str(path), 'review_sha256': digest(path), 'decision': report['review']['decision'],
                       'baseline_id': payload['baseline_validation']['baseline_id']})
    return {'path': str(path), 'sha256': digest(path),
            'identity': identity, 'decision': 'within_scope', 'model_calls': report['model_calls']}


def validate_admission_reply(reply, candidate_id, source_ids, contract=None, baseline=None):
    """New admissions need paired order evidence; legacy validate_reply is unchanged."""
    row = validate_reply(reply, [candidate_id])[candidate_id]
    if baseline is not None:
        baseline_quality.findings(row, baseline)
    elif row.get('inherited_baseline_findings'):
        raise Failure('invalid_scope_review', 'Baseline findings require the original validation binding')
    evidence = row.get('transition_evidence')
    flags = ['eliminated_source_iterations', 'changed_source_recurrence',
             'changed_source_marking_schedule', 'changed_source_operation_order']
    if (not isinstance(evidence, dict) or not isinstance(evidence.get('explanation'), str) or
            not evidence['explanation'].strip() or any(type(evidence.get(k)) is not bool for k in flags)):
        raise Failure('invalid_scope_review', 'Admission requires all four source-transition/order flags and an explanation')
    pairs = row.get('operation_order_evidence')
    if not isinstance(pairs, list) or not pairs:
        raise Failure('invalid_scope_review', 'Admission requires paired current-source and Rust operation-order evidence')
    changed = any(evidence[k] for k in flags); unknown = False
    for pair in pairs:
        if (not isinstance(pair, dict) or not isinstance(pair.get('source_id'), str) or
                pair['source_id'] not in source_ids):
            raise Failure('invalid_scope_review', 'Order evidence must cite an exact current source ID')
        if any(not isinstance(pair.get(k), str) or not pair[k].strip()
               for k in ['source_equation', 'representation_relation']):
            raise Failure('invalid_scope_review', 'Order evidence needs a current equation and representation relation')
        if type(pair.get('identity_case')) is not bool:
            raise Failure('invalid_scope_review', 'Declare whether this is a source identity case')
        events = pair.get('events')
        if not isinstance(events, list):
            raise Failure('invalid_scope_review', 'Order evidence needs an event correspondence table')
        table = {}
        for event in events:
            if (not isinstance(event, dict) or not isinstance(event.get('id'), str) or
                    not event['id'].strip() or event['id'] in table):
                raise Failure('invalid_scope_review', 'Event IDs must be nonempty and unique within a row')
            for side in ['source_operation', 'rust_operation']:
                if side not in event or (event[side] is not None and
                        (not isinstance(event[side], str) or not event[side].strip())):
                    raise Failure('invalid_scope_review', 'Describe each event side, or use null for a missing operation')
            locations = event.get('rust_locations')
            if (not isinstance(locations, list) or any(not isinstance(x, str) or not x.strip() for x in locations) or
                    (event['rust_operation'] is not None and not locations)):
                raise Failure('invalid_scope_review', 'Each Rust event needs an actual code location')
            correspondence = event.get('correspondence')
            if not isinstance(correspondence, str) or correspondence not in {'same_transition', 'different_transition', 'unknown'}:
                raise Failure('invalid_scope_review', 'Classify every event correspondence')
            if event['source_operation'] is None and event['rust_operation'] is None:
                raise Failure('invalid_scope_review', 'An event cannot be absent from both implementations')
            if correspondence == 'same_transition' and (event['source_operation'] is None or event['rust_operation'] is None):
                raise Failure('invalid_scope_review', 'A missing business operation cannot be the same transition')
            primitive_changed, primitive_unknown = optimization_contracts.primitive_equivalence(event, pair['source_id'], contract)
            changed |= primitive_changed; unknown |= primitive_unknown
            changed |= correspondence == 'different_transition'
            unknown |= correspondence == 'unknown'
            table[event['id']] = event
        for side in ['source', 'rust']:
            order = pair.get(side + '_order')
            if not isinstance(order, list) or any(not isinstance(x, str) or x not in table for x in order):
                raise Failure('invalid_scope_review', 'Order arrays must reference IDs in the same event table')
            expected = {key for key, event in table.items() if event[side + '_operation'] is not None}
            if set(order) != expected:
                raise Failure('invalid_scope_review', 'Every described operation must occur on its corresponding side')
        if pair['identity_case'] != (not events):
            raise Failure('invalid_scope_review', 'Only an explicit source identity may have an empty business trace')
        if not isinstance(pair.get('comparison'), str) or pair['comparison'] not in {'preserved', 'changed', 'unknown'}:
            raise Failure('invalid_scope_review', 'Classify paired operation order as preserved, changed, or unknown')
        changed |= (pair['comparison'] == 'changed' or pair['source_order'] != pair['rust_order'])
        unknown |= pair['comparison'] == 'unknown'
    if row['decision'] == 'within_scope' and changed:
        row = {**row, 'decision': 'requires_source_change',
               'reason': 'Source-transition or paired operation-order evidence contradicts within_scope: ' + row['reason']}
    elif row['decision'] == 'within_scope' and unknown:
        row = {**row, 'decision': 'uncertain',
               'reason': 'Paired operation-order correspondence is unknown: ' + row['reason']}
    return optimization_contracts.validate_evidence(row, contract)


def file_delta(before, after):
    """Complete deterministic diff and status/hash inventory; never truncate hunks."""
    rows = []; patches = []
    for name in sorted(set(before) | set(after)):
        old = before.get(name); new = after.get(name)
        status = 'added' if old is None else 'deleted' if new is None else 'unchanged' if old == new else 'modified'
        rows.append({'path': name, 'status': status,
                     'before_sha256': hashlib.sha256(old.encode()).hexdigest() if old is not None else None,
                     'after_sha256': hashlib.sha256(new.encode()).hexdigest() if new is not None else None})
        if old != new:
            # Explicit no-newline markers keep adjacent deletion/addition lines
            # separate and make end-of-file changes reviewable as unified diff.
            lines = difflib.unified_diff((old or '').splitlines(True), (new or '').splitlines(True),
                        fromfile='a/' + name if old is not None else '/dev/null',
                        tofile='b/' + name if new is not None else '/dev/null')
            patches.extend(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n' for line in lines)
    return {'files': rows, 'unified_diff': ''.join(patches)}


def attribution_context(state):
    return {'files_sha256': fingerprint(state['files']),
            'source_model_sha256': fingerprint(state['bundle']['source_model']),
            'mapping_sha256': fingerprint(state['mapping']), 'partition_sha256': fingerprint(state['partition']),
            'rust_config_sha256': fingerprint(state['rust_config'])}


def attribution(original, state, parent=None):
    """Distinguish inherited code from this change, without exempting defects."""
    parent = original if parent is None else parent
    baseline = {'context': attribution_context(original), **file_delta(original['files'], state['files'])}
    parent_context = attribution_context(parent)
    return {'policy': 'complete-change-attribution-v1',
            'rule': 'Attribute introduced restrictions using both complete diffs. Inherited code is not an optimization-introduced change, but remains subject to CURRENT source, numeric, generic and abstract representation obligations. A baseline or prior admission is not a proof of inherited correctness. Abstract representation/projection equations remain authoritative; do not dismiss them as prose. Check actual exported reachability and all source inputs, not only benchmark data.',
            'original_to_candidate': baseline,
            'parent_to_candidate': ({'same_as': 'original_to_candidate'} if parent_context == baseline['context'] else
                                    {'context': parent_context, **file_delta(parent['files'], state['files'])})}


def admission_payload(original, option, parent=None):
    """Keep complete current code/source evidence, with both attribution bases."""
    payload = review_payload(original, [option])
    payload['candidates'][0]['change_attribution'] = attribution(original, option['state'], parent)
    return payload


def admission_identity(original, option, payload):
    from .optimization_protocol import interfaces
    semantic_payload = deepcopy(payload)
    for candidate in semantic_payload['candidates']:
        candidate.pop('candidate_id', None)  # Display IDs do not affect semantics.
    state = option['state']
    return {'policy': fingerprint(ONLINE_SYSTEM), 'version': version(state),
            'source': fingerprint(state['bundle']['source_model']),
            'contract': fingerprint(optimization_contracts.context(state)),
            'frozen_interfaces': fingerprint(interfaces(original['files'])),
            'evidence_payload': fingerprint(semantic_payload)}


def finalize_admissions(original, provenance, attempts, directory):
    """Seal decisions already used by the search; never run a post-hoc selector."""
    from .common import digest
    from .optimization_protocol import interfaces
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    options = choices(original, provenance, attempts); reviews = []
    for option in options:
        link = option['record'].get('scope_admission', {})
        path = Path(link.get('path', ''))
        if not path.is_file() or digest(path) != link.get('sha256'):
            raise Failure('optimization_admission_changed', option['id'])
        audit = read(path); identity = audit['identity']
        transaction = read(Path(option['record']['path']) / 'transaction.json')
        before = transaction.get('before')
        if not isinstance(before, dict) or any(key not in before for key in ['files', 'mapping', 'partition', 'rust_config']):
            raise Failure('optimization_admission_changed', 'Missing exact admission parent: ' + option['id'])
        parent = deepcopy(option['state']); parent.update(deepcopy(before))
        expected = admission_identity(original, option, admission_payload(original, option, parent))
        if identity != expected or audit['review']['decision'] != 'within_scope':
            raise Failure('optimization_admission_changed', option['id'])
        validated = validate_admission_reply({'reviews': [{**audit['review'], 'candidate_id': option['id']}]},
                                            option['id'], option['state']['bundle']['source_model']['entities'],
                                            optimization_contracts.context(option['state']),
                                            baseline_quality.validation_context(original))
        if validated['decision'] != 'within_scope':
            raise Failure('optimization_admission_changed', option['id'])
        reviews.append(audit['review'])
    identity = {'policy': fingerprint(ONLINE_SYSTEM), 'frozen_interfaces': fingerprint(interfaces(original['files'])),
                'candidates': [{'id': r['id'], 'version': version(r['state']),
                                'source': fingerprint(r['state']['bundle']['source_model'])} for r in options]}
    report = {'identity': identity, 'status': 'reviewed' if options else 'no_optimized_candidates',
              'reviews': reviews, 'model_calls': 0, 'seconds': 0,
              'baseline_quality': baseline_quality.collect_admissions(original, attempts),
              'admission_meaning': 'CURRENT business computation and candidate-introduced/changed/activated obligations only. Candidate acceptance is not a new proof of inherited baseline helpers; baseline root findings apply uniformly to publication of all modes.',
              'timing_policy': 'Scope decisions occur before candidate acceptance, charged inside the shared search budget; finalization only verifies their seals.'}
    save(directory/'review.json', report)
    selected = options[-1] if options else None
    save(directory/'selection.json', {'review_sha256': digest(directory/'review.json'),
                                     'selected_candidate': selected['id'] if selected else None,
                                     'policy': 'Last already admitted, behavior-validated and performance-accepted state; no post-hoc model rollback.'})
    return selected, report


def compact_source(state):
    model=state['bundle']['source_model']
    ids=set(state['partition']['owner']) | {r['source'] for r in state['mapping']}
    ids.update(r['source'] for r in state['partition']['boundaries'])
    keys={'id','name','kind','source_type','type_variables','execution_sorts',
          'abstract','variables','parameters','execution_type','instance_identity','instance_resolutions',
          'specifications','function_input_equations','execution_equations',
          'dependencies','type_dependencies','class_dependencies','constructors','supers'}
    return optimization_contracts.annotate_source({'entries':model['entries'], 'entities':[
        {k:v for k,v in readable(model['entities'][n]).items() if k in keys}
        for n in sorted(ids) if n in model['entities']], 'boundaries':state['partition']['boundaries']})


def restore(original, provenance, record, proof=None):
    """Recover a prior version from the existing atomic transaction journal."""
    from .optimization import mutable_fork
    state=mutable_fork(original,provenance);path=Path(record['path'])
    state.update(deepcopy(read(path/'transaction.json')['after']))
    state['completed']=[];state['reviews']={};state['source_reviews']={};state['dirty_sources']={}
    if record.get('source_optimized'):
        if not proof:raise Failure('scope_proof_missing',str(path))
        bundle=read(Path(proof['directory'])/'extraction/program.json')
        bundle['original_source_model']=deepcopy(original['bundle']['original_source_model'])
        bundle['source_equivalence']=proof;state['bundle']=bundle
        from .source_optimization import preserve_export_types, verify_export_type_evidence
        if not verify_export_type_evidence(proof, proof['original_to_optimized']):
            preserve_export_types(original['bundle']['original_source_model'],
                                  bundle['source_model'], proof['original_to_optimized'])
    validation=read(path/'validation.json')
    if version(state)!=record['candidate_version'] or validation.get('candidate_version')!=version(state) or validation.get('status')!='passed':
        raise Failure('scope_candidate_changed',str(path))
    state['optimization_validation']=validation
    # The actual business files used for validation are still present and must
    # agree with the transaction journal, rather than being recreated by a model.
    for name,content in state['files'].items():
        actual=(path/'candidate'/name).read_text()
        if actual!=content and actual!='#![forbid(unsafe_code)]\n'+content:
            raise Failure('scope_candidate_changed',name)
    return state


def choices(original, provenance, attempts):
    result=[];proof=None
    for record in attempts:
        if record.get('status')=='source_proved':proof=record['proof']
        if record.get('status')=='accepted':
            state=restore(original,provenance,record,proof)
            result.append({'id':Path(record['path']).name,'state':state,'record':record})
    return result


def validate_reply(reply, expected):
    rows=reply.get('reviews') if isinstance(reply,dict) else None
    if not isinstance(rows,list) or len(rows)!=len(expected):
        raise Failure('invalid_scope_review','Review every supplied candidate exactly once')
    if {r.get('candidate_id') for r in rows if isinstance(r,dict)}!=set(expected):
        raise Failure('invalid_scope_review','Candidate IDs differ from the supplied immutable set')
    for row in rows:
        if row.get('decision') not in {'within_scope','requires_source_change','uncertain'} or not isinstance(row.get('reason'),str) or not row['reason'].strip():
            raise Failure('invalid_scope_review','Each decision needs a supported outcome and source/code evidence')
    return {r['candidate_id']:r for r in rows}


def checked_source_evidence(state):
    proof = state['bundle'].get('source_equivalence') or {}
    # Exclude proposal prose and path/run labels, retaining proof/type authority.
    return {key: proof[key] for key in [
        'status', 'kind', 'original_to_optimized', 'theory_sha256', 'skip_proofs',
        'oracle_dependencies', 'oracle_audit', 'command_guard', 'export_type_preservation',
        'export_type_authority', 'export_type_evidence_sha256', 'original_source_hashes'] if key in proof}


def review_payload(original, options):
    from .optimization_protocol import interfaces
    sources={fingerprint(compact_source(r['state'])):compact_source(r['state']) for r in options}
    return {'task':'source_correspondence_only','frozen_interfaces':interfaces(original['files']),
            'baseline_validation':baseline_quality.validation_context(original),
            'source_graphs':sources,'candidates':[
                {'candidate_id':r['id'],'files':r['state']['files'],'mapping':r['state']['mapping'],
                 'source_graph':fingerprint(compact_source(r['state'])),
                 'performance_contract':optimization_contracts.context(r['state']),
                 'source_equivalence_checked':bool(r['record'].get('source_optimized')),
                 'checked_source_evidence':checked_source_evidence(r['state']),
                 'change_attribution':attribution(original, r['state'], r.get('parent'))}
                for r in options]}


def audit(original, provenance, attempts, provider, budget_path, directory):
    from .optimization_protocol import interfaces
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    options=choices(original,provenance,attempts)
    identity={'policy':fingerprint(SYSTEM),'frozen_interfaces':fingerprint(interfaces(original['files'])),'candidates':[
        {'id':r['id'],'version':version(r['state']),
         'source':fingerprint(r['state']['bundle']['source_model'])} for r in options]}
    path=directory/'review.json'
    if path.exists():
        report=read(path)
        if report['identity']!=identity:raise Failure('scope_review_changed',str(path))
    elif not options:
        report={'identity':identity,'status':'no_optimized_candidates','reviews':[],'model_calls':0,'seconds':0}
        save(path,report)
    else:
        budget=read(budget_path)
        if budget.get('active'):raise Failure('scope_search_active','Close the search session before independent final review')
        payload=review_payload(original,options)
        started=time.monotonic();calls=0;decisions=None;error=None
        for _ in range(2):
            budget=read(budget_path)
            if max(provider.calls,budget['calls'])>=budget['max_model_calls']:break
            remaining=180-(time.monotonic()-started)
            if remaining<=1:break
            budget['calls']=max(provider.calls,budget['calls'])+1
            budget['final_scope_review_started_at']=now();atomic_save(budget_path,budget)
            provider.cfg['budgets']['model_seconds']=remaining
            calls+=1
            try:
                reply=provider.call(SYSTEM,json.dumps(payload,ensure_ascii=False),
                                    options={'max_output_tokens':32768},phase='performance_scope_review')
                decisions=validate_reply(reply,[r['id'] for r in options]);break
            except Failure as exc:
                error={'code':exc.code,'message':str(exc)};payload['protocol_feedback']=error
        elapsed=time.monotonic()-started;budget=read(budget_path)
        budget['final_scope_review_seconds']=budget.get('final_scope_review_seconds',0)+elapsed
        atomic_save(budget_path,budget)
        report={'identity':identity,'status':'reviewed' if decisions is not None else 'review_unavailable',
                'reviews':list(decisions.values()) if decisions is not None else [],
                'model_calls':calls,'seconds':elapsed,'error':error,
                'timing_policy':'Independent final validation after the one-hour search; review time is reported separately; all calls remain inside the same total call allowance.'}
        save(path,report)
    decisions=validate_reply({'reviews':report['reviews']},[r['id'] for r in options]) if report['status']=='reviewed' else {}
    eligible=[r for r in options if decisions.get(r['id'],{}).get('decision')=='within_scope']
    selected=eligible[-1] if eligible else None
    save(directory/'selection.json',{'review_sha256':digest(path),'selected_candidate':selected['id'] if selected else None,
                                    'policy':'Latest scope-approved, behavior-validated and performance-accepted candidate; otherwise original Off.'})
    return selected,report
