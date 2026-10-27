"""Verify native source-algorithm failure evidence without changing verdicts.

Resource exhaustion alone is not an adjudicated source failure. These checks
require a real original singleton request and an independent source invariant:
either a complete recursive pattern state cycle, or native conjunction
introduction that preserves a flexible Boolean rightmost goal. No generated
program is executed and no frontend or finished XML is manufactured.
"""
from pathlib import Path
import hashlib, json, re, shutil, sys, xml.etree.ElementTree as ET
import afp_common as c
# The original proof propositions can contain hundreds of pending goals.
sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))

def need(condition, message):
    if not condition: raise ValueError(message)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def same_command(actual, expected):
    """Compare complete sidecar fields after lossless JSON container encoding.

    A freshly returned subprocess identity is a tuple; the exact same durable
    identity is a JSON array when reread. Normalize only that representation.
    Status, exit code, arguments, birth identity and every other field remain
    part of the equality check.
    """
    return json.loads(json.dumps(actual)) == expected

def undo(text, edits):
    for edit in reversed(edits):
        need(text.count(edit['new']) == 1, 'Non-unique observation edit')
        text = text.replace(edit['new'], edit['old'])
    return text

def input_files(work):
    metadata = c.read_json(work / 'sources.json')
    for name, expected in metadata['files'].items():
        need(sha(work / name) == expected, 'Changed observation input: ' + name)
    return metadata

def installed_source(name, installed, reference):
    actual = (installed / name).read_bytes()
    need(actual == (reference / name).read_bytes(), 'Installed/reference mismatch: ' + name)
    return actual.decode()

def natural_failure(work, serializer):
    result = c.read_json(work / 'result.json')
    command = result['command']
    need(command['status'] == 'failed' and command.get('returncode') == 1,
         'Observation must have an actual native exception exit')
    # Natural exit status is essential. The global reserve was 512 MB; older
    # Arrow evidence predates the stricter serial-start policy. A source cycle
    # remains a cycle under memory pressure, but retain that resource context.
    need(command['min_available_mb'] > 512, 'Observation crossed the enforced global reserve')
    need(result.get('formal_serializer_sha256') == serializer, 'Changed serializer')
    text = (work / 'process.log').read_text()
    need('Interrupt_Breakdown' in text and ('Run out of store - interrupting threads' in text or 'Unable to increase stack' in text),
         'Missing native resource-exception log')
    return command, text

def decode(path):
    raw = re.sub(r'<(/?)([0-9]+|:)(?=[\s/>])', lambda m: '<' + m[1] + ('item' if m[2] == ':' else 'v' + m[2]), path.read_text())
    raw = re.sub(r' (\d+)=', r' a\1=', raw)
    root = ET.fromstring(raw)
    def term(node):
        tag = node.tag
        if tag in {'v0', 'v1', 'v2'}:
            return (tag, node.attrib['a0'], int(node.attrib.get('a1', '0')),
                    ET.tostring(node[0], encoding='unicode') if tag == 'v2' else None)
        if tag == 'v3': return (tag, int(node.text))
        if tag == 'v4': return (tag, node.attrib['a0'], ET.tostring(node[0], encoding='unicode'), term(node[1][0]))
        if tag == 'v5': return (tag, term(node[0][0]), term(node[1][0]))
        raise ValueError(tag)
    return root.attrib, term(root[0])

def app(term):
    args = []
    while term[0] == 'v5': args.append(term[2]); term = term[1]
    return term, list(reversed(args))

def const(term, name, arity):
    head, args = app(term)
    return args if head[0] == 'v0' and head[1] == name and len(args) == arity else None

def goals(term):
    rows = []
    while (args := const(term, 'Pure.imp', 2)) is not None:
        rows.append(args[0]); term = args[1]
    return rows

def flexible(term):
    parameters = []
    while True:
        universal = const(term, 'Pure.all', 1)
        implication = const(term, 'Pure.imp', 2)
        if universal is not None:
            need(universal[0][0] == 'v4', 'Expected a bound universal parameter')
            parameters.append(universal[0][2]); term = universal[0][3]
        elif implication is not None: term = implication[1]
        else: break
    proposition = const(term, 'HOL.Trueprop', 1)
    need(proposition is not None, 'Goal has no HOL Boolean proposition')
    head, args = app(proposition[0])
    need(head[0] == 'v2', 'Goal is rigid rather than a schematic Boolean function')
    need([arg[1] if arg[0] == 'v3' else None for arg in args] == list(range(len(parameters)-1, -1, -1)),
         'Schematic function is not applied to all distinct quantified parameters')
    typ = ET.fromstring(head[3]); arity = 0
    while typ.tag == 'v0' and typ.attrib.get('a0') == 'fun': typ = typ[1][0]; arity += 1
    need(arity == len(parameters) and typ.attrib.get('a0') == 'HOL.bool', 'Wrong schematic function type')
    return {'name': head[1], 'index': head[2], 'parameters': parameters}

def conjunction(work, project, installed, serializer):
    reference = project / 'temp/Isabelle2025_ref/src'
    def source(name): return installed_source(name, installed, reference)
    metadata = input_files(work); command, log = natural_failure(work, serializer)
    need(command['min_available_mb'] > 3500, 'Conjunction observation did not satisfy its isolated resource policy')
    text = source('HOL/Tools/set_comprehension_pointfree.ML')
    observed = (work / 'set-comprehension-observe.ML').read_text()
    observed = undo(observed, metadata['proof_observer_adjustments'])
    observed = undo(observed, metadata['pointfree_additional_observation_edits'])
    ancestor = project / metadata['pointfree_source_observer']
    observed = undo(observed, c.read_json(ancestor.parent / 'sources.json')['observation_edits'])
    need(observed == text, 'Proof observer does not reverse exactly to installed algorithm')
    converter = source('Pure/Isar/code.ML')
    start = converter.index('fun eqn_conv conv ct ='); end = converter.index('\nfun apply_functrans', start)
    need((work / 'native-conversion.ML').read_text() == converter[start:end], 'Changed equation conversion')
    need(sha(installed / 'Pure/Isar/code.ML') == metadata['native_source_sha256'], 'Changed native code.ML')
    need("THEN' (TRY o REPEAT_ALL_NEW (resolve_tac ctxt @{thms conjI}))" in text, 'Changed conjunction tactic')
    subset = text[text.index('    val subset_tac2 ='):text.index('    val subset_tac2 =') + 850]
    need(subset.index('@{thms exI}') < subset.index('REPEAT_ALL_NEW') < subset.index('hyp_subst_tac'), 'Changed witness ordering')
    need('tac THEN_ALL_NEW (TRY o (fn i => REPEAT_ALL_NEW tac i));' in source('Pure/tactical.ML'), 'Changed recursive tactic')
    need('else op THEN (f j, INTERVAL f i (j - 1)) x;' in source('Pure/General/seq.ML'), 'Changed recursion order')
    need('lemma conjI: "\\<lbrakk>P; Q\\<rbrakk> \\<Longrightarrow> P \\<and> Q"' in source('HOL/HOL.thy'), 'Changed native rule')
    certificate = c.read_json(work / 'nontermination-analysis.json')
    entries = {}; returns = {}
    for line in log.splitlines():
        match = re.match(r'DIAGNOSTIC tactic (enter|return) (\d+) (\S+) (.*)', line)
        if match:
            row = dict(re.findall(r'(\w+)=([^ ]+)', match[4])); row['label'] = match[3]
            (entries if match[1] == 'enter' else returns)[int(match[2])] = row
    checked = []
    for pair in certificate['state_pairs']:
        step = pair['step']; before = work / pair['before']; after = work / pair['after']
        for path, key in [(before, 'before_sha256'), (after, 'after_sha256')]:
            need(path.resolve().parent == work.resolve() and sha(path) == pair[key], 'Changed or foreign proof state')
        before_attr, before_term = decode(before); after_attr, after_term = decode(after)
        need(before_attr['label'] == after_attr['label'] == 'subset2.conjI.step', 'Wrong recorded tactic')
        index = int(before_attr['goal_index']); before_goals = goals(before_term); after_goals = goals(after_term)
        need(int(after_attr['goal_index']) == index == len(before_goals) and len(after_goals) == index + 1, 'Changed goal count/index')
        old, left, right = [flexible(term) for term in (before_goals[-1], after_goals[-2], after_goals[-1])]
        need(old['parameters'] == left['parameters'] == right['parameters'], 'Changed quantified parameters')
        need(left['name'] == 'P' and right['name'] == 'Q' and left['index'] == right['index'] > old['index'], 'Not two fresh schematic Boolean functions')
        enter, returned = entries[step], returns[step]
        need(int(enter['goals']) == index and int(returned['goals']) == index + 1, 'XML/native count disagreement')
        need(left['index'] == int(returned['maxidx_after']) > int(returned['maxidx_before']), 'New variables are not globally fresh')
        checked.append({'step': step, 'parameters': len(old['parameters']), 'goals_before': index, 'goals_after': index + 1,
                        'before_sha256': sha(before), 'after_sha256': sha(after)})
    need(bool(checked), 'No actual typed proof pair')
    for step in range(min(row['step'] for row in checked), max(entries) + 1):
        enter, returned = entries[step], returns[step]
        need(enter['label'] == returned['label'] == 'subset2.conjI.step', 'Later source trajectory differs')
        need(int(enter['goal_index']) == int(enter['goals']) and int(returned['goals']) == int(enter['goals']) + 1, 'Later trajectory is not rightmost expansion')
    return {'family': 'flexible_boolean_conjunction', 'typed_state_pairs': checked,
            'native_observation': command, 'source_observer_reverses_exactly': True,
            'basis': 'Native conjI plus preservation of a flexible Boolean last goal under the rightmost recursive tactic'}

def pattern_cycle(work, project, installed, serializer):
    reference = project / 'temp/Isabelle2025_ref/src'
    def source(name): return installed_source(name, installed, reference)
    metadata = input_files(work); command, text = natural_failure(work, serializer)
    original = source('HOL/Tools/set_comprehension_pointfree.ML')
    observed = undo((work / 'set-comprehension-observe.ML').read_text(), metadata['observation_edits'])
    need(observed == original == (work / 'native-source.ML').read_text(), 'Pattern observer does not reverse to native source')
    need(sha(installed / 'HOL/Tools/set_comprehension_pointfree.ML') == metadata['native_source_sha256'], 'Changed native merge source')
    block = original[original.index("fun merge' []"):original.index('\nfun merge (', original.index("fun merge' []"))]
    need("fun disjoint_to_pat p = null (inter (op =) pat p)" in block and
         "val overlap_pats = filter_out disjoint_to_pat pats" in block and
         "val rem_pats = filter disjoint_to_pat pats" in block and
         "merge' (distinct (op =) (flat overlap_pats @ pat)) (rem_pats, pats1)" in block,
         'Changed recursive merge branch')
    states = [json.loads(match[1]) for line in text.splitlines()
              if (match := re.search(r'DIAGNOSTIC merge_state (\{.*\})$', line))]
    need(all(row['step'] == index for index, row in enumerate(states)), 'Changed merge event order')
    for index, row in enumerate(states[:-2]):
        pat, left, right = [row[key] for key in ('pat', 'pats1', 'pats2')]
        if not (pat and left and right) or len(pat) != len(set(pat)): continue
        if any(set(pat).intersection(other) for other in left + right): continue
        swapped = {'pat': pat, 'pats1': right, 'pats2': left}; initial = {'pat': pat, 'pats1': left, 'pats2': right}
        if all(states[index+1][key] == value for key, value in swapped.items()) and all(states[index+2][key] == value for key, value in initial.items()):
            return {'family': 'empty_overlap_merge_cycle', 'cycle_start': index, 'state': initial, 'swapped': swapped,
                    'native_observation': command, 'source_observer_reverses_exactly': True,
                    'basis': 'The native empty-overlap branch swaps two nonempty queues while preserving a distinct nonempty selected pattern; two calls restore the entire recursive state'}
    raise ValueError('No actual recursive cycle of the source-checked form')

def native_request(formal, observation, constant, project):
    sidecar = c.read_json(formal / 'process.log.json')
    need(sidecar and sidecar.get('log') == c.relative(formal / 'process.log'), 'Native sidecar belongs to another log directory')
    need(sidecar and sidecar['status'] == 'failed' and sidecar.get('returncode') == 1, 'Formal process has no natural failed exit')
    need(not c.identity_matches(sidecar), 'Formal process still live')
    need((formal / 'scope.txt').read_text().splitlines() == [constant], 'Formal request is not this singleton')
    need((formal / 'theories.txt').read_bytes() == (observation / 'theories.txt').read_bytes(), 'Formal/diagnostic theories differ')
    context_path = formal / 'contexts/merged.xml'; context = ET.parse(context_path).getroot()
    need([node.attrib['name'] for node in context.findall('constant')] == [constant], 'Wrong original singleton context')
    need(not (formal / 'finished.xml').exists() and not list(formal.glob('attempts/**/*.xml')), 'Request did record another outcome')
    argv = sidecar['command']
    need('timeout=0' in argv and 'skip_proofs=false' in argv, 'Wrong formal proof/timeout options')
    expression = argv[argv.index('-e') + 1]
    original = project / 'test/afp-Isabelle2025/full_export.ML'
    capture = project / 'test/afp-Isabelle2025/full_capture.ML'
    if str(capture) in expression:
        outcome = ET.parse(formal / 'native-request-outcome.xml').getroot()
        need(outcome.tag == 'native_request_outcome' and outcome.attrib.get('status') == 'exception'
             and outcome.attrib.get('origin') == 'original_full_export_outer_capture', 'Wrong native outer outcome')
        need([row.attrib['name'] for row in outcome.findall('constant')] == [constant], 'Wrong captured native scope')
        need(outcome.findtext('original_script') == str(original)
             and outcome.findtext('original_finished_exists') == 'false'
             and outcome.findtext('exception_name') == 'Interrupt_Breakdown', 'Wrong captured native exception')
    else:
        need(str(original) in expression, 'Formal request did not call the original exporter')
    text = (formal / 'process.log').read_text()
    need('Exception- Interrupt_Breakdown raised' in text and ('Run out of store - interrupting threads' in text or 'Unable to increase stack' in text), 'Missing actual formal native exception')
    return {'command': sidecar, 'context': c.relative(context_path), 'context_sha256': sha(context_path),
            'log_sha256': sha(formal / 'process.log'), 'scope_sha256': sha(formal / 'scope.txt'),
            'original_finished_exists': False, 'original_frontend_witness_exists': False}


def review(formal, observation, constant, family, serializer, project=None):
    """Recompute a proof-backed review from original bytes, never a verdict flag."""
    project = Path(project or c.PROJECT).resolve()
    formal, observation = Path(formal).resolve(), Path(observation).resolve()
    need(formal.is_relative_to(project) and observation.is_relative_to(project), 'Evidence outside project')
    command = c.read_json(formal / 'process.log.json', {})
    argv = command.get('command', [])
    executable = shutil.which(argv[0]) if argv else None
    need(executable is not None, 'Cannot identify the installed Isabelle executable')
    installed = Path(executable).resolve().parent.parent / 'src'
    metadata = input_files(observation)
    expected_source = installed / ('Pure/Isar/code.ML' if family in {'flexible_boolean_conjunction', 'fixed_parameter_boolean_conjunction'}
                                 else 'HOL/Tools/set_comprehension_pointfree.ML')
    need(Path(metadata['native_source']).resolve() == expected_source.resolve(), 'Observation used a different Isabelle installation')
    need((observation / 'scope.txt').read_text().splitlines() == [constant], 'Wrong independent observation scope')
    checkers = {'flexible_boolean_conjunction': conjunction,
                'empty_overlap_merge_cycle': pattern_cycle}
    # A fixed Free state argument uses native higher-order imitation rather
    # than the bound-only pattern certificate. Keep its stricter type and
    # complete-state substitution checks in a separate evidence reader.
    if family == 'fixed_parameter_boolean_conjunction':
        from frontend_fixed_parameter import conjunction as fixed_conjunction
        checkers[family] = fixed_conjunction
    need(family in checkers, 'Unrecognized source invariant family')
    proof = checkers[family](observation, project, installed, serializer)
    request = native_request(formal, observation, constant, project)
    return {'schema': 1, 'constant': constant, 'family': family,
            'formal_directory': str(formal.relative_to(project)),
            'observation_directory': str(observation.relative_to(project)),
            'serializer_sha256': serializer,
            'original_export_script_sha256': sha(project / 'test/afp-Isabelle2025/full_export.ML'),
            'native_evidence': request, 'source_invariant': proof,
            'observation_sources_sha256': sha(observation / 'sources.json'),
            'pointfree_input_sha256': sha(observation / 'pointfree-input.xml')}


def prepare_record(run, observation, family, serializer, review_root=None):
    """Save a separately labelled derived review; leave all native files intact."""
    need(len(run.get('scope', [])) == 1, 'A group failure cannot condemn its members')
    formal = c.PROJECT / run['directory']; constant = run['scope'][0]
    evidence = review(formal, observation, constant, family, serializer)
    need(same_command(run['command'], evidence['native_evidence']['command']), 'Stored command differs from original sidecar')
    need(not run.get('finished') and not run.get('attempts'), 'Recorded native outcomes require their normal handling')
    root = Path(review_root) if review_root is not None else formal.parents[3] / 'source-fault-reviews'
    path = root / (hashlib.sha256(run['directory'].encode()).hexdigest() + '.json')
    c.write_json(path, {'checked': c.timestamp(), 'origin': 'independent_source_invariant_review', 'evidence': evidence})
    return {'review': c.relative(path), 'review_sha256': sha(path),
            'constant': constant, 'family': family,
            'observation': evidence['observation_directory']}


def validate_record(run, serializer):
    """Independently reject stale reviews, altered proofs and fabricated statuses."""
    record = run.get('source_fault')
    need(isinstance(record, dict), 'No source invariant review supplied')
    need(len(run.get('scope', [])) == 1 and run['scope'][0] == record.get('constant'), 'Wrong singleton review scope')
    path = (c.PROJECT / record['review']).resolve()
    formal = (c.PROJECT / run['directory']).resolve()
    need(path.is_relative_to(c.PROJECT.resolve()) and path.is_file(), 'Missing or foreign derived review')
    need(sha(path) == record.get('review_sha256'), 'Source invariant review bytes changed')
    stored = c.read_json(path)
    need(stored.get('origin') == 'independent_source_invariant_review', 'Review does not identify its derived origin')
    evidence = review(formal, c.PROJECT / record['observation'], record['constant'], record['family'], serializer)
    need(stored.get('evidence') == evidence, 'Source invariant review is stale or inconsistent')
    need(same_command(run['command'], evidence['native_evidence']['command']), 'Stored command differs from original sidecar')
    need(not run.get('finished') and not run.get('attempts'), 'Original process completion must not be replaced')
    return evidence
