"""Report observed context/repair cost without inventing causal savings."""
import json
from pathlib import Path
from .common import read, save


def trial_metrics(directory):
    directory = Path(directory)
    result = read(directory / 'result.json') if (directory / 'result.json').exists() else {}
    diagnostics = directory / 'diagnostics'
    calls = []
    for path in sorted((diagnostics / 'model').glob('*/request.json')):
        request = read(path)
        response = path.parent / 'response.json'
        usage = read(response).get('usage', {}) if response.exists() else {}
        messages = request.get('messages', [])
        graph_messages = []
        for message in messages:
            if message.get('role') != 'user':
                continue
            try:
                payload = json.loads(message.get('content', ''))
            except (ValueError, TypeError):
                continue
            if isinstance(payload, dict) and 'thingol' in payload.get('program', {}):
                graph_messages.append(len(json.dumps(payload['program']['thingol'], ensure_ascii=False)))
        calls.append({'call': path.parent.name, 'messages': len(messages),
                      'input_characters': sum(len(m.get('content', '')) for m in messages),
                      'full_graph_messages': len(graph_messages), 'full_graph_characters': sum(graph_messages),
                      'usage': usage, 'response_received': response.exists()})
    events = [read(p) for p in sorted(diagnostics.glob('candidate-*/repair-event.json'))]
    audits = [read(p) for p in diagnostics.rglob('conversation-audit.json')]
    return {'status': result.get('status', 'not_run'), 'model_calls': len(calls),
            'prompt_tokens': sum(c['usage'].get('prompt_tokens', 0) for c in calls),
            'completion_tokens': sum(c['usage'].get('completion_tokens', 0) for c in calls),
            'cache_hit_tokens': sum(c['usage'].get('prompt_cache_hit_tokens', c['usage'].get('prompt_tokens_details', {}).get('cached_tokens', 0)) for c in calls),
            'calls_without_response_usage': sum(not c['response_received'] for c in calls),
            'full_graph_messages': sum(c['full_graph_messages'] for c in calls),
            'full_graph_characters': sum(c['full_graph_characters'] for c in calls),
            'input_characters': sum(c['input_characters'] for c in calls),
            'reads': sum(e['result'] == 'material_requested' for e in events),
            'unchanged_repairs': sum(e['result'] in {'unchanged_repair', 'unchanged_connector'} for e in events),
            'repair_events': len(events), 'audited_requests': len(audits), 'calls': calls,
            'limitations': ['Characters are not tokens or currency.',
                           'Missing provider usage is unknown, not zero cost.',
                           'Different generated code/check counts confound historical cost comparison.',
                           'This report alone is not a skill/context ablation or a generalization study.']}


def summarize(study):
    study = Path(study)
    trials = {p.name: trial_metrics(p) for p in sorted((study / 'trials').iterdir()) if p.is_dir()}
    summary = {'trials': trials, 'completed_passes': sum(t['status'] == 'passed' for t in trials.values()),
               'prompt_tokens': sum(t['prompt_tokens'] for t in trials.values()),
               'completion_tokens': sum(t['completion_tokens'] for t in trials.values()),
               'claim': 'Observed measurements for this run; no causal attribution or unrun ablation.'}
    save(study / 'context-evaluation.json', summary)
    return summary


if __name__ == '__main__':
    import sys
    report = summarize(sys.argv[1])
    print(json.dumps({k: v for k, v in report.items() if k != 'trials'}, ensure_ascii=False, indent=2))
