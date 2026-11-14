"""Optional, budgeted performance stage over immutable correctness artifacts.

Candidates reuse source tests, observation connectors and executed reference
outputs. Only newly accepted candidate versions acquire validation evidence.
"""
from copy import deepcopy
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import fcntl
import json
import math
import shutil
import statistics
import threading
import time
from .common import ROOT, Executor, Failure, digest, now, read, save
from .task_context import fingerprint
from .provider import Provider
from .experiment_config import SOURCE_LIMITS
from . import numeric_experiment, numeric_interface, source_optimization
from . import optimization_protocol, optimization_scope, optimization_contracts, optimization_materials
from . import implementation_strategy as strategy
from .segmented_config import materialize
from .segmented_contract import coverage, probes
from .translation_workflow import apply_transaction, compile_crate, connection, version


DEFAULT_CALLS = 25
DEFAULT_SECONDS = 3600
SEARCH_OPTIONS = {'processes': 3, 'samples_per_process': 6, 'warmup_min_seconds': .2,
                  'warmup_max_seconds': 1.0, 'target_batch_ns': 5000000,
                  'order_design': 'williams', 'short_batch_samples': 40}
_PREPARATION_SLOTS = threading.BoundedSemaphore(2)
STAGE_SCHEMA = 2
FATAL_EXECUTION_ERRORS = {'tool_cleanup_incomplete', 'performance_cleanup_hold',
                          'process_ownership_unavailable'}


@contextmanager
def computation(budget, exclusive=False):
    """Two preparation jobs may overlap; measurement excludes all preparation."""
    from .owned_process import assert_timing_ready
    assert_timing_ready()
    started = time.monotonic(); acquired = False; slot = None; entered = False
    try:
        path = ROOT / 'cache/timing-v2.lock'; path.parent.mkdir(parents=True, exist_ok=True)
        if not exclusive:
            acquired = _PREPARATION_SLOTS.acquire(timeout=budget.remaining())
            if not acquired:
                budget.remaining()
                raise Failure('optimization_time_exhausted', 'Elapsed budget includes preparation queue waiting')
            # File slots also cap preparation when separate processes launch
            # Rust-only and Full concurrently.
            while slot is None:
                budget.remaining()
                for number in range(2):
                    candidate = (path.parent / f'optimization-preparation-{number}.lock').open('a+')
                    try:
                        fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB); slot = candidate; break
                    except BlockingIOError:
                        candidate.close()
                if slot is None: time.sleep(min(.1, budget.remaining()))
        with path.open('a+') as lock:
            while True:
                budget.remaining()
                try:
                    fcntl.flock(lock, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB); break
                except BlockingIOError:
                    time.sleep(min(.1, budget.remaining()))
            assert_timing_ready()
            budget.data['resource_wait_seconds'] = budget.data.get('resource_wait_seconds', 0) + time.monotonic() - started
            entered = True
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
    finally:
        if not entered:
            budget.data['resource_wait_seconds'] = budget.data.get('resource_wait_seconds', 0) + time.monotonic() - started
        if slot is not None:
            fcntl.flock(slot, fcntl.LOCK_UN); slot.close()
        if acquired: _PREPARATION_SLOTS.release()
        budget.persist()


class Budget:
    def __init__(self, path, calls=DEFAULT_CALLS, seconds=DEFAULT_SECONDS, reserved_calls=0, source_limits=None):
        self.path = Path(path); self.started = time.monotonic()
        self.reserved_calls = reserved_calls
        self.source_limits = {**SOURCE_LIMITS, **(source_limits or {})}
        self.data = read(path) if self.path.exists() else {
            'max_model_calls': calls, 'max_seconds': seconds, 'charged_seconds': 0,
            'calls': 0, 'started_at': now(), 'sessions': 0}
        if self.data['max_model_calls'] != calls or self.data['max_seconds'] != seconds:
            raise Failure('optimization_budget_changed', str(path))
        if self.data.get('source_policy', SOURCE_LIMITS) != self.source_limits:
            if self.path.exists(): raise Failure('optimization_budget_changed', 'Frozen source phase policy changed')
        if source_limits is not None: self.data['source_policy'] = self.source_limits
        self.previous = self.data['charged_seconds']
        if self.data.get('active'):
            # An interrupted controller cannot silently refund a model wait.
            self.previous += max(0, time.time() - self.data['persisted_at'])
        self.data['sessions'] += 1; self.data['active'] = True
        self.persist()

    def elapsed(self):
        return self.previous + time.monotonic() - self.started

    def remaining(self):
        left = self.data['max_seconds'] - self.elapsed()
        if left <= 0:
            raise Failure('optimization_time_exhausted', 'Retain the last accepted incumbent')
        if self.data.get('active_phase') == 'source':
            phase = self.data['source_phase']
            left = min(left - phase['reserve_seconds'],
                       phase['seconds'] - (self.elapsed() - phase['start_seconds']))
            if left <= 0:
                raise Failure('optimization_source_budget_exhausted', 'Preserve the reserved fixed-source Rust budget')
        return left

    def begin_source(self):
        self.data.setdefault('source_phase', {
            'start_calls': self.data['calls'], 'start_seconds': self.elapsed(),
            'calls': self.source_limits['calls'], 'seconds': self.source_limits['seconds'],
            'reserve_calls': self.source_limits['reserve_rust_calls'],
            'reserve_seconds': self.source_limits['reserve_rust_seconds']})
        self.data['active_phase'] = 'source'; self.persist()

    def begin_rust(self):
        self.data['active_phase'] = 'rust'; self.persist()

    def persist(self):
        self.data['charged_seconds'] = self.elapsed(); self.data['persisted_at'] = time.time()
        save(self.path, self.data)

    def close(self):
        self.data['active'] = False; self.persist()

    def call(self, provider, payload, system=None, phase='performance_optimization'):
        self.remaining()
        calls = max(self.data['calls'], provider.calls)
        if self.data.get('active_phase') == 'source':
            limit = self.data['source_phase']
            if (calls - limit['start_calls'] >= limit['calls'] or
                    calls >= self.data['max_model_calls'] - self.reserved_calls - limit['reserve_calls']):
                raise Failure('optimization_source_budget_exhausted', 'Source call allowance exhausted; continue with fixed-source Rust')
        if calls >= self.data['max_model_calls'] - self.reserved_calls:
            raise Failure('optimization_calls_exhausted', 'Retain the last accepted incumbent')
        # Reservation is durable before the network request. Failed and
        # interrupted requests consume the same total allowance.
        self.data['calls'] = max(self.data['calls'], provider.calls) + 1
        self.persist()
        provider.cfg['budgets']['model_seconds'] = min(600, self.remaining())
        try:
            return provider.call(system or SYSTEM, json.dumps(payload, ensure_ascii=False), phase=phase)
        finally:
            self.persist()


class BudgetExecutor(Executor):
    def __init__(self, directory, budget):
        super().__init__(directory, cleanup_descendants=True); self.budget = budget

    def run(self, argv, cwd=None, timeout=300, env=None, stdin=None, check=True):
        try:
            return super().run(argv, cwd=cwd, timeout=min(timeout, self.budget.remaining()),
                               env=env, stdin=stdin, check=check)
        finally:
            self.budget.persist()


def make_executor(directory, budget):
    """Reuse normal session glue on this performance fork, without global hooks."""
    from .session_context import install
    class PerformanceExecutor(BudgetExecutor):
        pass
    install(PerformanceExecutor, Path(directory).resolve().parent)
    return PerformanceExecutor(directory, budget)


SYSTEM = '''Optimize an already validated Isabelle-to-Rust implementation using measured evidence.
The existing source program graph, global implementation guidance and source-to-Rust mapping are supplied together with exact candidate files. Read them together. The objective is lower kernel runtime with preserved source semantics, not beating another language. Production numeric representation, Cargo configuration, observation connector, public interfaces, inputs and test expectations are fixed. No benchmark-matching branches, answer tables, caching across calls, hardcoded benchmark answers, unsafe code, environment/timing/test detection or backend-specific implementations. Implement mathematical case distinctions already present in the CURRENT source, including those introduced by a checked source equivalence. Adding an algorithmic fast path to a fixed source still requires a source proposal and proof. Maintain generic type bounds and arbitrary mathematical integers. Changes must work for all source inputs. Obey the controller's current stage. In the rust stage keep the source algorithm/recurrence fixed: ownership, allocation, traversal realization and inlining may improve, but do not substitute a closed form or a different algorithm/library algorithm even when an equivalence lemma already exists. Full assesses source optimization first, accepts at most one proved and measured source transformation, then freezes that source for all Rust refinement; there is no return to the source stage. In the source stage, an algorithm change MUST be submitted as a source action, proved by Isabelle, re-extracted, and only then implemented by a rust action. Citing a theorem in prose does not replace that transition. Existing guidance was authored for correctness-only generation: after the source proof succeeds, revise obsolete algorithm/route restrictions using the new graph; source semantics and numeric contracts remain authoritative.
The request budget_accounting.phase_available and remaining_calls/remaining_seconds already deduct the reserved Rust allowance and apply the source-stage cap. Do not subtract rust_reserved again or compare phase_available against that reserve; total_remaining is the separate whole-search balance. All attempts, proof/translation work, scope review and waits use the shared budget.
Return one JSON object with top-level "action": "rust", "source", "inspect", or "finish". Actions:
1. "rust": full replacement contents only for changed files under "files"; optional "mapping" updates using the current mapping schema; REQUIRED "strategy_version" and "strategy_updates" updating relevant implementation choices. Optional "boundaries" replaces the complete native boundary list using exact source IDs, kind, basis and conditions; the shared partitioner recomputes dependencies and never permits hiding mandatory business functions. Include "reason" and "evidence" describing measured costs and why the change addresses them. Preserve the original public callable interfaces. Private free helpers may change signature or be renamed/removed together with callers and mappings; frozen tests and connectors must still compile unchanged. Rust-only keeps the source program fixed and improves ownership, allocation, iteration or other Rust realization choices. No need to invent a numeric target speedup.
2. "source" (full source stage only): REQUIRED "direction_id" (a stable name reused for proof/translation repairs) and "source_assessment" describing the measured hotspot, affected source IDs, intended reduction in work and proof route. At most two transformation directions may be tried. "definitions" containing Isabelle HOL function/definition/lemma text, plus "replacements":[{"source":original exported constant ID,"rhs":HOL function term,"proof":complete Isar proof}]. Private optimized helpers are allowed in definitions; replacement RHS wrappers may call them. The replacements list names only original exported constants, exactly once each including unchanged ones, with unconditional equivalence proofs. The source_replacement_protocol gives exact generated names indexed by the ORIGINAL entries order, never the proposal list order. The controller creates i2r_entry_N with definition i2r_entry_N = rhs and requires unconditional theorem i2r_entry_N = original_constant. Proofs may unfold i2r_entry_N_def. It controls imports and exports. No theory header/end, ML, axioms, sorry/oops, oracles, target printing, arbitrary imports or session options. A successful proof re-enters source extraction; the NEXT request supplies the new graph and requires a rust action implementing it with updated mapping and guidance. Original source files remain immutable.
3. "finish": concise evidence-based reason when no worthwhile next change remains. In full mode include "source_assessment" explaining the source optimization opportunities considered and their feasibility/cost, even if none is worthwhile.
4. "inspect": request_sources ranges from source_material_catalog, to read actual definitions, named lemmas and proof patterns. Reads are available in both modes, count toward the shared model budget, and do not count as failed candidates or source transformation directions. Use them instead of repeatedly guessing theorem names or proof rules. A missing theorem or unfamiliar proof interface is a knowledge gap, not evidence that the source algorithm cannot be optimized.
You can repair failed candidates or proof proposals using diagnostic feedback within the shared budget. A source proposal should address a concrete measured cost, not add a wrapper for its own sake. If source translation is pending, implement that extracted source or finish with an explicit source_assessment explaining why it should be abandoned. The supplied source_phase_policy specifies the source cap and reserved Rust allowance; assessment, reading, proof repairs, retranslation and acceptance review share that cap. Admission checks count within the same total model allowance; final sealing makes no model calls. All phases share the total allowance; failed requests count. Three consecutive unsuccessful Rust candidates stop the search. The same business source is later compiled with checked numerics; do not optimize separately for checked.
Strategy updates use {id,expected_revision,kind,sources,choice,conditions,status,links,test_focus,reason}; kind is ownership/representation/interface/library; status adopted; links uses mapping/rust_config/partition. Reuse IDs and correct revisions for existing choices; new decisions use expected_revision 0. Supersede obsolete conflicting choices when changing implementation intent. Tests are evidence for behavior, not a proof of Rust equivalence. Do not claim Isabelle proves the generated Rust.'''
SYSTEM += '\nThe request stage_contract determines whether this turn may propose a proved source algorithm change or must realize the current fixed source. In source_proposal, recurrence/visitation changes are allowed and must use action=source with checked equivalence and re-extraction. Never reject a source proposal merely because Rust refinement forbids that recurrence change. In source_translation and rust_refinement, the supplied computation_preservation contract applies to the current equations.'
SYSTEM += '\n' + optimization_contracts.GUIDANCE
SYSTEM += '\n' + optimization_protocol.EXAMPLES


def mutable_fork(state, provenance):
    result = deepcopy(state)
    # This creates a new search branch. It never unlocks or rewrites the
    # correctness artifact that the original terminal lock protects.
    result['optimization_origin'] = provenance
    for key in ['source_candidate_lock', 'support_pass_candidate', 'behavior_version',
                'source_scope_refreshes', 'support_pending_identity', 'strategy_digest']:
        result.pop(key, None)
    result['phase'] = 'optimization'; result['unit'] = None
    return result


def selection_workloads(row):
    workloads = row['performance_workloads']
    ids = {row['primary_workload'], workloads[0]['id'], workloads[len(workloads) // 2]['id']}
    return [w for w in workloads if w['id'] in ids]


def ensure_interfaces(original, files):
    before = optimization_protocol.interfaces(original['files']); after = optimization_protocol.interfaces(files)
    changed = [name for name, rows in before.items() if after.get(name) != rows]
    if changed:
        raise Failure('optimization_interface_changed', 'Keep the frozen source-test and observer bindings', changed)


def apply_candidate(state, reply, original, cfg, directory):
    if not reply.get('files') or not reply.get('strategy_updates'):
        raise Failure('invalid_optimization_proposal', 'A code change and explicit guidance revisions are required')
    forbidden = set(reply) & {'rust_config', 'connector', 'components', 'remove_files', 'remove_mapping'}
    if forbidden:
        raise Failure('invalid_optimization_proposal', 'This stage fixes configuration, connectors and existing interfaces', sorted(forbidden))
    result = apply_transaction(state, reply, cfg, directory)
    ensure_interfaces(original, result['files'])
    optimization_protocol.ensure_public_trait_members(original['files'], result['files'])
    numeric_interface.validate_candidate(result['files'], result['rust_config'])
    roots = sorted(set(result['partition']['owner']) | set(result['bundle']['source_model']['entries']))
    evidence = coverage(result['bundle'], result['files'], result['mapping'], roots, result['partition'], final=True)
    from .native_numeric_contracts import check_realization
    evidence['native_primitives'] = check_realization(result)
    save(Path(directory) / 'mapping-check.json', evidence)
    return result


def build_and_validate(state, cfg, frozen_tests, observations, directory, executor):
    from .segmented_support import execute as execute_tests
    directory = Path(directory)
    checked_files = {**state['files'], 'src/lib.rs': state['files']['src/lib.rs'] + probes(state['mapping'])}
    crate = materialize(directory / 'candidate', checked_files, state['rust_config'])
    result = compile_crate(crate, state['rust_config'], cfg, executor)
    if result['status'] != 'passed':
        raise Failure('optimization_compile_failed', 'Candidate library failed compilation', result)
    tested = execute_tests(frozen_tests, crate, state['rust_config'], cfg, executor)
    save(directory / 'source-tests.json', tested)
    if tested['status'] != 'passed':
        raise Failure('optimization_source_tests_failed', 'Frozen source contracts rejected the candidate', tested)
    materialize(crate, state['files'], state['rust_config'])
    harness = connection(crate, state['connector'], state['rust_config'], cfg)
    built = compile_crate(harness, state['rust_config'], cfg, executor, False)
    if built['status'] != 'passed':
        raise Failure('optimization_connector_compile_failed', 'Restore the frozen callable API', built)
    lanes = [numeric_experiment.validate_lane(built['binary'], observations, lane, 'arbitrary', executor,
                                             cfg['testing']['process_timeout']) for lane in ['ordinary', 'kernel']]
    evidence = {'status': 'passed', 'candidate_version': version(state), 'source_tests': tested,
                'cached_reference_checks': lanes, 'reference_executions': 0,
                'connector_regenerations': 0, 'source_test_regenerations': 0}
    save(directory / 'validation.json', evidence)
    return crate, evidence


def timing_build(crate, cfg, case, directory, budget=None):
    from .kernel_build import build
    # kernel_build owns compiler invocation; the controller bounds this phase
    # using remaining build time and checks before and after it.
    conf = deepcopy(cfg)
    if budget:
        conf['budgets']['build_seconds'] = min(conf['budgets']['build_seconds'], budget.remaining())
    result = build({'id': 'candidate', 'case': case, 'language': 'rust', 'kind': 'llm',
                    'source': str(crate), 'work': str(directory)}, conf)
    if budget:
        budget.persist(); budget.remaining()
    return result


def compare(parent, candidate, row, observations, cfg, directory, budget):
    from .kernel_timing import DEFAULTS, measure_group
    directory = Path(directory); results = []
    for workload in selection_workloads(row):
        budget.remaining(); path = directory / workload['id']
        options = {**DEFAULTS, **SEARCH_OPTIONS, 'timeout_seconds': min(60, budget.remaining()),
                   'deadline_monotonic': time.monotonic() + budget.remaining()}
        builds = [{**build, 'id': key, 'work': str(path / key)}
                  for key, build in [('parent', parent), ('candidate', candidate)]]
        result = measure_group(row['id'], builds, workload['input'],
                               observations[('kernel', tuple(workload['input']))], options, path)
        a, b = result['summary']['parent'], result['summary']['candidate']
        results.append({'workload': workload['id'], 'speedup': a['median_ns'] / b['median_ns'],
                        'ci95': numeric_experiment.interval(a, b),
                        'parent': a, 'candidate': b, 'record': str(path / 'measurement-v2.json')})
        budget.persist(); budget.remaining()
    geometric = math.exp(statistics.mean(math.log(r['speedup']) for r in results))
    lower = math.exp(statistics.mean(math.log(r['ci95'][0]) for r in results))
    accepted = geometric >= 1.03 and lower > 1 and all(r['speedup'] >= 1 / 1.05 for r in results)
    return {'accepted': accepted, 'geomean_speedup': geometric, 'conservative_lower': lower,
            'workloads': results, 'rule': 'geomean >= 1.03; geometric mean of per-workload CI lower bounds > 1; no measured regression > 5%',
            'role': 'development selection only; independent final measurements follow'}


def profile(state, cfg, observations, row, directory, executor):
    from .performance_search import instrument
    from .validation import execute
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    result = {'method': 'diagnostic function instrumentation',
              'limitations': 'Perturbs inlining and short functions; not production timing or allocation counts.'}
    try:
        files, catalog, skipped = instrument(state['files'])
        crate = materialize(directory / 'candidate', files, state['rust_config'])
        harness = connection(crate, state['connector'], state['rust_config'], cfg)
        main = harness / 'src/main.rs'; code = main.read_text()
        code = code.replace('let start=std::time::Instant::now();',
                            'i2r_candidate::__i2r_translation_profile::begin();\n let start=std::time::Instant::now();')
        code = code.replace('let elapsed=start.elapsed().as_nanos();',
                            'let elapsed=start.elapsed().as_nanos();\n i2r_candidate::__i2r_translation_profile::end();')
        main.write_text(code)
        built = compile_crate(harness, state['rust_config'], cfg, executor, False)
        if built['status'] != 'passed':
            raise Failure('profile_compile_failed', 'Diagnostic build unavailable', built)
        workload = next(w for w in row['performance_workloads'] if w['id'] == row['primary_workload'])
        checked = execute(built['binary'], [workload['input']], executor, cfg['testing']['process_timeout'],
                           arguments=('--i2r-benchmark',))
        expected = observations[('kernel', tuple(workload['input']))]
        if checked['status'] != 'passed' or checked['outputs'] != [expected]:
            raise Failure('profile_validation_failed', 'Diagnostic output differs from cached reference', checked)
        hotspots = []
        for line in Path(checked['record']['stderr']).read_text().splitlines():
            if line.startswith('I2R_PROFILE\t'):
                _, key, count, total, own = line.split('\t')
                hotspots.append({'location': key, 'calls': int(count), 'inclusive_ns': int(total), 'exclusive_ns': int(own)})
        result.update(status='measured' if hotspots else 'no_instrumented_functions', catalog=catalog,
                      skipped=skipped, hotspots=sorted(hotspots, key=lambda r: -r['exclusive_ns']), execution=checked)
    except Failure as error:
        if error.code in FATAL_EXECUTION_ERRORS:
            result.update(status='aborted', error=error.code, reason=str(error), evidence=error.evidence)
            save(directory / 'profile.json', result)
            raise
        result.update(status='unavailable', reason=str(error), evidence=error.evidence)
    save(directory / 'profile.json', result); return result


def check_stage_action(mode, stage, pending_source, action):
    if action == 'source' and (mode != 'full' or stage != 'source' or pending_source):
        raise Failure('source_action_unavailable', 'Source changes are available only in the bounded initial source phase; implement or abandon any pending proved source first')
    if action == 'rust' and stage == 'source' and not pending_source:
        raise Failure('source_proof_required', 'Submit a concrete source action and checked proof before implementing a changed algorithm; a Rust shortcut or theorem citation cannot bypass extraction')


def source_direction(reply, directions, limit=SOURCE_LIMITS['directions']):
    """Repairs reuse a direction; new transformations consume one of two slots."""
    name = reply.get('direction_id'); assessment = reply.get('source_assessment')
    if not isinstance(name, str) or not name.strip() or not isinstance(assessment, str) or not assessment.strip():
        raise Failure('source_assessment_required', 'Supply a stable direction_id and concrete source_assessment: measured hotspot, affected source IDs, work reduction and proof route')
    if name not in directions:
        if len(directions) >= limit:
            raise Failure('invalid_source_direction',
                'Source direction slots are full; resolve the proposed label before another proof attempt',
                {'proposed_direction': name, 'registered_directions': list(directions), 'direction_limit': limit,
                 'recovery': 'If this is a repair of a registered transformation, reuse its existing direction_id. Do not relabel a genuinely new transformation as a repair. Otherwise finish this source phase. No new direction or proof attempt was charged by this rejection; model calls and elapsed time still count.'})
        directions.append(name)
    return name


def source_replacement_protocol(original):
    model = original['bundle']['original_source_model']; entries = model['entries']
    return {'private_helpers_in_definitions': True,
            'replacement_coverage': 'Exactly one wrapper RHS and unconditional equivalence proof per original export, including unchanged exports.',
            'index_authority': 'Original entries order; independent of replacement proposal order.',
            'type_authority': 'Use each original exported source_type below. A generic internal helper does not make a concrete exported entry polymorphic. A concrete entry may use a proved concrete helper without specializing existing generic helpers or changing any frozen public Rust signature. Preserve original generic exports and their sorts exactly.',
            'exports': [{'source': name, 'generated_entry': 'i2r_entry_' + str(i),
                         'source_type': deepcopy(model['entities'][name].get('source_type')),
                         'definition_theorem': 'i2r_entry_' + str(i) + '_def',
                         'equivalence_theorem': 'i2r_equiv_' + str(i)}
                        for i, name in enumerate(entries)]}


def stage_contract(stage, pending_source):
    if stage == 'source' and not pending_source:
        return {'kind': 'source_proposal', 'source_recurrence_change_allowed': True,
                'requirement': 'Propose useful algorithm/recurrence/visitation changes with action=source, Isabelle equivalence for all exports, and re-extraction before Rust implementation. Rust-only computation-preservation rules do not prohibit proposing a proved revised source. finish skips this phase and continues fixed-source Rust refinement.'}
    return {'kind': 'source_translation' if stage == 'source' else 'rust_refinement',
            'source_recurrence_change_allowed': False,
            'requirement': 'Implement the CURRENT supplied equations. The same Rust admission gate applies in Full and Rust-only.',
            'computation_preservation': optimization_scope.COMPUTATION_PRESERVATION_CONTRACT}


def request(state, original, mode, budget, feedback, measured, pending_source, stage='rust', source_summary=None, material=None):
    effective_mode = 'rust-only' if stage == 'rust' else mode
    remaining_calls = max(0, budget.data['max_model_calls'] - budget.data['calls'] - budget.reserved_calls)
    if stage == 'source':
        phase = budget.data['source_phase']
        remaining_calls = max(0, min(remaining_calls - phase['reserve_calls'],
                                   phase['calls'] - (budget.data['calls'] - phase['start_calls'])))
    remaining_seconds = budget.remaining()
    reserve = budget.data.get('source_phase', {}) if stage == 'source' else {}
    accounting = {
        'phase_available': {'model_calls': remaining_calls, 'seconds': remaining_seconds},
        'total_remaining': {'model_calls': max(0, budget.data['max_model_calls'] - budget.data['calls']),
                            'seconds': max(0, budget.data['max_seconds'] - budget.elapsed())},
        'rust_reserved': {'model_calls': reserve.get('reserve_calls', 0),
                          'seconds': reserve.get('reserve_seconds', 0)},
        'rule': 'phase_available already applies the stage cap and subtracts Rust reserve; do not deduct that reserve again.'}
    return {'mode': effective_mode, 'run_mode': mode, 'stage': stage,
            'stage_contract': stage_contract(stage, pending_source),
            'allowed_actions': (['source', 'inspect', 'finish'] if stage == 'source' and not pending_source else ['rust', 'inspect', 'finish']),
            'remaining_calls': remaining_calls,
            'remaining_seconds': remaining_seconds, 'budget_accounting': accounting, 'state_version': version(state),
            'files': state['files'], 'mapping': state['mapping'], 'rust_config': state['rust_config'],
            'numeric_policy': state['bundle']['numeric_policy'],
            'performance_contract': optimization_contracts.context(state),
            'primitive_adapter_protocol': 'Read performance_contract.registered_native_contracts.available_adapters against the CURRENT graph, including after source re-extraction. These exact library adapters may be explicitly declared in the complete boundaries list; they are not silently applied. Update affected mappings/guidance in the same Rust transaction. A source-proved replacement may expose a new primitive; do not reimplement its unary equations merely because the old graph had no adapter. Business functions and unregistered operations retain their source obligations.',
            'source_program': optimization_contracts.annotate_source(source_optimization.source_context(state)),
            'original_exports': original['bundle']['original_source_model']['entries'],
            'source_replacement_protocol': source_replacement_protocol(original),
            'source_phase_policy': budget.source_limits if stage == 'source' else None,
            'original_source_files': original['bundle']['sources'] if effective_mode == 'full' else {},
            'source_material_catalog': optimization_materials.catalog(state['bundle']),
            'requested_source_material': material or {},
            'source_reading_protocol': 'Use action=inspect and request_sources with explicit line ranges to read frozen defining theories and existing lemmas (40000 characters/read, 120000 retained; no silent truncation). This consumes one model call but no proof attempt or optimization direction. Consider the prefilled defining theories before deciding to skip source optimization. Read actual theorem names/statements before guessing missing facts or abandoning a proof direction. If a proof-cost claim depends on missing theory facts, inspect those facts before treating that claim as established. Retrieved text is proof-search material; Isabelle must still check each new equivalence.',
            'global_implementation_guidance': strategy.project(state),
            'strategy_version': fingerprint(strategy.current(state)),
            'pending_source_translation': pending_source,
            'source_stage': source_summary, 'measured_evidence': measured, 'feedback': feedback}


def optimize_case(baseline_run, row, mode, directory, limits):
    from .experiment_baselines import resolve
    directory = Path(directory); outcome = directory / 'result.json'
    # Completed legacy experiments are immutable and remain readable without
    # re-freezing inputs or migrating their historical search decisions.
    if outcome.exists() and 'scope_selection' in read(outcome):
        return read(outcome)
    statepath = directory / 'search-state.json'
    saved = read(statepath) if statepath.exists() else {}
    if (saved and saved.get('stage_schema') != STAGE_SCHEMA) or (outcome.exists() and read(outcome).get('stage_schema') != STAGE_SCHEMA):
        raise Failure('optimization_stage_migration_required', 'Keep legacy experiments read-only; start this source-first controller in a new run directory')
    baseline_run = resolve(baseline_run, row['id'])
    directory.mkdir(parents=True, exist_ok=True)
    original, cfg, observations, seal = numeric_experiment.freeze(baseline_run, row, directory / 'baseline', paired=False)
    source_diag = Path(baseline_run) / 'tasks' / row['id'] / 'diagnostics'
    frozen_tests = read(source_diag / 'support-tests' / (original['support_evidence']['frozen_identity'] + '.json'))
    cfg = deepcopy(cfg); cfg['translation']['correctness_only'] = False
    cfg['translation']['performance_refinement'] = False
    cfg['budgets']['max_model_calls'] = limits['max_model_calls']
    save(directory / 'effective-config.json', cfg)
    provider = Provider(cfg, directory / 'model')
    if outcome.exists():
        result = finalize(original, cfg, provider, directory, read(outcome))
        verify_original(seal); return result
    budget = Budget(directory / 'budget.json', limits['max_model_calls'], limits['max_seconds'], source_limits=limits.get('source_limits'))
    executor = make_executor(directory / 'commands', budget)
    provenance = {'baseline_run': str(Path(baseline_run).resolve()), 'baseline_seal': digest(directory / 'baseline/frozen.json'),
                  'candidate_version': version(original), 'mode': mode}
    incumbent = saved.get('incumbent', mutable_fork(original, provenance))
    attempts = saved.get('attempts', []); incumbent_build = saved.get('incumbent_build')
    accepted_path = saved.get('accepted_path'); stage = saved.get('stage', 'source' if mode == 'full' else 'rust')
    current = saved.get('current', deepcopy(incumbent)); pending_source = saved.get('pending_source', False)
    feedback = saved.get('feedback'); no_gain = saved.get('no_gain', 0)
    measured = saved.get('measured', {})
    material = saved.get('source_material', {})
    source_summary = saved.get('source_stage', {'directions': [], 'accepted': False, 'stop': None})
    stop = 'budget_exhausted'

    def checkpoint():
        save(statepath, {'incumbent': incumbent, 'incumbent_build': incumbent_build,
                         'accepted_path': accepted_path, 'attempts': attempts, 'provenance': provenance,
                         'stage_schema': STAGE_SCHEMA, 'stage': stage, 'source_stage': source_summary,
                         'current': current, 'pending_source': pending_source, 'feedback': feedback,
                         'no_gain': no_gain, 'measured': measured, 'source_material': material})
        budget.persist()

    def enter_rust(reason):
        nonlocal stage, current, pending_source, feedback, no_gain
        phase = budget.data.get('source_phase', {})
        source_summary.update(stop=reason, model_calls=budget.data['calls']-phase.get('start_calls', budget.data['calls']),
                              seconds=max(0, budget.elapsed()-phase.get('start_seconds', budget.elapsed())))
        stage = 'rust'; current = deepcopy(incumbent); pending_source = False; no_gain = 0
        budget.begin_rust()
        feedback = {'status': 'source_stage_complete', 'reason': reason,
                    'instruction': 'Source is now fixed. Refine this accepted Rust incumbent; do not return to source transformations.'}

    checkpoint()
    try:
        if incumbent_build is None:
            with computation(budget):
                crate = materialize(directory / 'initial/candidate', incumbent['files'], incumbent['rust_config'])
                connection(crate, incumbent['connector'], incumbent['rust_config'], cfg)
                incumbent_build = timing_build(crate, cfg, row['id'], directory / 'initial/timing', budget)
        if not measured:
            with computation(budget, exclusive=True):
                measured = profile(incumbent, cfg, observations, row, directory / 'initial/profile', executor)
        if (Path(baseline_run) / 'performance/off' / row['id'] / 'result.json').exists():
            measured['baseline_measurements'] = read(Path(baseline_run) / 'performance/off' / row['id'] / 'result.json')
        if stage == 'source': budget.begin_source()
        else: budget.begin_rust()
        if stage == 'source' and not source_summary.get('context_prefill'):
            additions, context_audit = optimization_materials.initial_sources(original['bundle'])
            material = optimization_materials.merge(material, additions)
            context_path = directory / 'initial/source-context.json'
            save(context_path, {'material': additions, 'audit': context_audit})
            source_summary['context_prefill'] = {**context_audit, 'path': str(context_path),
                                                  'sha256': digest(context_path)}
        checkpoint()
        while True:
            attempt = directory / 'attempts' / f'{len(attempts)+1:03d}'
            attempt.mkdir(parents=True, exist_ok=True)
            record = {'path': str(attempt), 'started_at': now(), 'parent_version': version(incumbent), 'stage': stage}
            reply = None; done = False
            try:
                budget.remaining()
                from . import optimization_source_policy
                system = optimization_source_policy.SYSTEM if stage == 'source' and not pending_source else SYSTEM
                reply = budget.call(provider, request(current, original, mode, budget, feedback, measured, pending_source, stage, source_summary, material), system=system)
                reply = optimization_protocol.normalize(reply)
                save(attempt / 'proposal.json', reply); record['action'] = reply['action']
                check_stage_action(mode, stage, pending_source, reply['action'])
                if reply['action'] == 'inspect':
                    additions = optimization_materials.read_sources(reply, current['bundle'])
                    material = optimization_materials.merge(material, additions)
                    save(attempt / 'source-material.json', additions)
                    record.update(status='source_material_read', source_material_sha256=digest(attempt / 'source-material.json'))
                    feedback = {'status': 'source_material_read', 'instruction': 'Read the supplied versioned theory excerpts. No candidate or source direction has been submitted by this read.'}
                elif reply['action'] == 'finish':
                    if stage == 'source':
                        if not isinstance(reply.get('source_assessment'), str) or not reply['source_assessment'].strip():
                            raise Failure('source_assessment_required', 'Explain the considered source opportunity and why no further source work is worthwhile')
                        record.update(status='source_stage_complete', source_assessment=reply['source_assessment'], reason=reply.get('reason'))
                        enter_rust(reply.get('reason', 'source_not_worthwhile'))
                    else:
                        stop = reply.get('reason', 'model_finished'); record['status'] = 'finished'; done = True
                elif reply['action'] == 'source':
                    record['direction_id'] = source_direction(reply, source_summary['directions'], budget.source_limits['directions'])
                    with computation(budget):
                        bundle = source_optimization.prove(original, reply, cfg, executor, attempt / 'source')
                        current = source_optimization.rebase(original, incumbent, bundle)
                    pending_source = True
                    feedback = {'status': 'source_proved', 'instruction': 'Implement the supplied extracted graph, preserve callable APIs, and revise affected mapping and guidance. Proof alone is not acceptance.'}
                    record.update(status='source_proved', proof=bundle['source_equivalence'])
                else:
                    with computation(budget):
                        proposed = apply_candidate(current, reply, original, cfg, attempt)
                        crate, validation = build_and_validate(proposed, cfg, frozen_tests, observations, attempt, executor)
                        built = timing_build(crate, cfg, row['id'], attempt / 'timing', budget)
                    record.update(candidate_version=version(proposed), validation=str(attempt / 'validation.json'),
                                  source_optimized=bool(proposed['bundle'].get('source_equivalence')))
                    # Admit before this candidate can become a later search basis.
                    record['scope_admission'] = optimization_scope.admit(original, proposed, record, provider, budget, attempt, parent=current)
                    with computation(budget, exclusive=True):
                        comparison = compare(incumbent_build, built, row, observations, cfg, attempt / 'comparison', budget)
                    record.update(status='accepted' if comparison['accepted'] else 'no_gain', comparison=comparison)
                    if comparison['accepted']:
                        proposed['optimization_validation'] = validation
                        incumbent = deepcopy(proposed); incumbent_build = built; accepted_path = str(attempt); no_gain = 0
                        measured = {**measured, 'latest_comparison': comparison,
                                    'profile_source_version': measured.get('profile_source_version', provenance['candidate_version'])}
                        if stage == 'source':
                            source_summary.update(accepted=True, accepted_candidate=attempt.name)
                            enter_rust('source_candidate_accepted')
                    elif stage == 'rust':
                        no_gain += 1
                    current = deepcopy(incumbent); pending_source = False
                    feedback = {'status': record['status'], 'comparison': comparison,
                                'instruction': 'Current files are the accepted incumbent; rejected files are not applied. The current stage remains authoritative.'}
            except Failure as error:
                # Timing workers know only their absolute deadline. In the
                # source phase that deadline is the earlier phase allowance,
                # not necessarily the global one-hour search deadline.
                if stage == 'source' and error.code == 'optimization_time_exhausted':
                    try:
                        budget.remaining()
                    except Failure as limit:
                        error = limit
                record.update(status=error.code, error={'message': str(error), 'evidence': error.evidence})
                if error.code in FATAL_EXECUTION_ERRORS:
                    attempts.append(record); save(attempt / 'result.json', record); checkpoint()
                    raise
                if stage == 'source' and error.code == 'optimization_source_budget_exhausted':
                    enter_rust(error.code)
                elif error.code in {'optimization_time_exhausted', 'optimization_calls_exhausted', 'budget_exhausted'}:
                    stop = error.code; done = True
                else:
                    feedback = {'status': error.code, 'message': str(error), 'evidence': error.evidence,
                                'previous_proposal': reply}
                    record['feedback'] = feedback
                    if stage == 'rust':
                        # A malformed author/reviewer reply or failed build is
                        # not a validated candidate without benefit. It still
                        # consumes the same total calls and elapsed budget.
                        # A scope rejection has no admissible timing comparison.
                        # Only the measured `no_gain` branch above contributes
                        # to performance stagnation; invalid/rejected proposals
                        # remain bounded by the unchanged total call/time caps.
                        current = deepcopy(incumbent)
                    # While repairing source translation retain only the proved
                    # rebase, never an unadmitted Rust proposal.
            attempts.append(record); save(attempt / 'result.json', record); checkpoint()
            if done: break
            # Stagnation is feedback, not a hidden smaller search budget.
            # The configured call/time limits and an explicit author finish
            # bound the search; a fixed three-candidate cutoff truncated Full
            # even when substantial Rust refinement allowance remained.
            if record.get('status') == 'accepted':
                # Profile only accepted states. A timeout here must not revoke
                # the already sealed admission and measured acceptance.
                with computation(budget, exclusive=True):
                    measured = profile(incumbent, cfg, observations, row, attempt / 'profile', executor)
                measured.update(latest_comparison=record['comparison'], profile_source_version=version(incumbent))
                checkpoint()
    except Failure as error:
        if error.code not in {'optimization_time_exhausted', 'optimization_calls_exhausted', 'budget_exhausted'}:
            raise
        stop = error.code
    finally:
        checkpoint(); budget.close()
    result = {'case': row['id'], 'mode': mode, 'status': 'complete', 'stop': stop,
              'baseline': provenance, 'attempts': attempts,
              'stage_schema': STAGE_SCHEMA, 'completed_stage': stage, 'source_stage': source_summary,
              'reference_executions': 0, 'source_test_regenerations': 0, 'connector_regenerations': 0}
    result = finalize(original, cfg, provider, directory, result)
    verify_original(seal)
    return result


def verify_original(seal):
    for name, sha in seal['original_files'].items():
        if digest(Path(seal['original_artifact']) / name) != sha:
            raise Failure('paired_original_changed', name)


def finalize(original, cfg, provider, directory, result):
    """Select only existing, validated versions that pass the source-scope audit."""
    selected, review = optimization_scope.finalize_admissions(original, result['baseline'], result['attempts'],
                                                             directory / 'scope-review')
    incumbent = selected['state'] if selected else mutable_fork(original, result['baseline'])
    accepted_path = selected['record']['path'] if selected else None
    build_path = (Path(accepted_path) / 'timing/build-v2.json' if accepted_path
                  else directory / 'initial/timing/build-v2.json')
    incumbent_build = read(build_path) if build_path.exists() else None
    # Do not promote an unvalidated proposal when search or review fails.
    save(directory / 'selected-state.json', incumbent)
    output = materialize(directory / 'output', incumbent['files'], incumbent['rust_config'])
    delivery_cfg = deepcopy(cfg); delivery_cfg['translation']['correctness_only'] = True
    harness = connection(output, incumbent['connector'], incumbent['rust_config'], delivery_cfg)
    if incumbent_build:
        built_crate = Path(incumbent_build['source'])
        timing_crate = Path(incumbent_build['work']) / 'crate'
        for source, target in [(built_crate / 'Cargo.lock', output / 'Cargo.lock'),
                               (built_crate / 'harness/Cargo.lock', harness / 'Cargo.lock')]:
            if source.exists():shutil.copyfile(source, target)
            else:
                fallback = timing_crate / source.relative_to(built_crate)
                if fallback.exists():shutil.copyfile(fallback, target)
    output_hashes = {str(p.relative_to(output)): digest(p) for p in output.rglob('*') if p.is_file()}
    result = {**result, 'selected_version': version(incumbent),
              'improved': bool(accepted_path), 'selected_source_optimized': bool(incumbent['bundle'].get('source_equivalence')),
              'accepted_path': accepted_path, 'budget': read(directory / 'budget.json'),
              'model_calls': provider.calls, 'known_usage': provider.usage,
              'unknown_usage_requests': provider.unknown_usage_requests,
              'baseline_quality': review['baseline_quality'],
              'scope_selection': {'review_sha256': digest(directory / 'scope-review/review.json'),
                                  'selection_sha256': digest(directory / 'scope-review/selection.json'),
                                  'status': review['status'], 'candidate': selected['id'] if selected else None,
                                  'model_calls': review['model_calls'], 'seconds': review['seconds']},
              'selected_state': str(directory / 'selected-state.json'),
              'selected_state_sha256': digest(directory / 'selected-state.json'),
              'output': str(output), 'output_files': output_hashes}
    save(directory / 'result.json', result)
    return result


def run(baseline_run, run_directory, rows, mode, limits, release):
    if mode not in {'rust-only', 'full'}:
        raise Failure('optimization_mode_required', 'Select --rust-only or --full')
    run_directory = Path(run_directory); baseline_run = Path(baseline_run).resolve()
    from .experiment_baselines import identity
    origin = {'baseline_run': str(baseline_run), 'baseline_identity': identity(baseline_run),
              'release_identity': release['identity'], 'mode': mode, 'limits': limits,
              'selection_workloads': {r['id']: selection_workloads(r) for r in rows}}
    origin_path = run_directory / 'optimization-origin.json'
    if origin_path.exists() and read(origin_path) != origin:
        raise Failure('optimization_origin_changed', 'Use a separate run for a new baseline or budget')
    save(origin_path, origin)
    completed = {}
    with ThreadPoolExecutor(max_workers=release['workers']) as pool:
        futures = {pool.submit(optimize_case, baseline_run, row, mode,
                               run_directory / 'optimization' / row['id'], limits): row for row in rows}
        for future in as_completed(futures):
            row = futures[future]
            try:
                result = future.result()
            except Exception as error:
                result = {'case': row['id'], 'mode': mode, 'status': 'controller_failed',
                          'error': getattr(error, 'code', type(error).__name__), 'message': str(error)}
                save(run_directory / 'optimization' / row['id'] / 'controller-failure.json', result)
            completed[row['id']] = result
            results = [completed[r['id']] for r in rows if r['id'] in completed]
            save(run_directory / 'optimization-report.json', {'complete': False, 'mode': mode, 'results': results})
            print('OPTIMIZATION', row['id'], mode, result['status'], 'calls', result.get('model_calls'), flush=True)
    report = {'complete': all(r['status'] == 'complete' for r in results), 'mode': mode, 'results': results,
              'improved': sum(bool(r.get('improved')) for r in results), 'selected': len(rows)}
    save(run_directory / 'optimization-report.json', report); return report
