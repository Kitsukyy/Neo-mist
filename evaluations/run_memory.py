"""Fixed synthetic cross-session memory regression; no private user content."""
import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
from time import monotonic
import warnings

from mist import __version__
from mist.bootstrap import create_application
from mist.config import load_config
from mist.errors import ErrorCode, MistError
from mist.memory_types import EpistemicState, MemoryCandidate

ROOT = Path(__file__).resolve().parents[1]
CASES = Path(__file__).with_name('memory-cases.json')


def write_private(path, value):
    with open(path, 'w', encoding='utf-8', opener=lambda name, flags: os.open(name, flags, 0o600)) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


class CaptureProvider:
    def __init__(self, delegate):
        self.delegate = delegate
        self.envelope = None

    def generate(self, envelope):
        self.envelope = envelope
        return self.delegate.generate(envelope)


def metadata(provider):
    usage = getattr(provider, 'last_usage', None) or {}
    metrics = {name: value for name, value in usage.items() if name in
        ('prompt_tokens', 'completion_tokens', 'total_tokens', 'reasoning_tokens') and type(value) is int and value >= 0}
    reason = getattr(provider, 'last_finish_reason', None)
    return {'usage': metrics or None, 'finish_reason': reason if reason in ('stop','length','tool_calls','content_filter') else None}


def run(output, *, real=False, api_key=None, deadline_seconds=600, case_set='all'):
    if case_set not in ('all', 'primary-continuation'):
        raise ValueError('Unknown fixed case set')
    output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    cases = json.loads(CASES.read_text())
    modes = ('FAST', 'PRIMARY')
    if case_set == 'primary-continuation':
        modes = ('PRIMARY',)
        cases = [case for case in cases if case['id'] in
                 ('hypothesis_not_fact', 'corrected_name_current_revision', 'deleted_name_absent')]
    settings, constitution, personality = load_config(ROOT/'examples/nvidia' if real else None)
    manifest = {'version': 2, 'application_version': __version__, 'python': platform.python_version(),
        'started_at': datetime.now(timezone.utc).isoformat(), 'kind': 'real_synthetic_memory_regression' if real else 'offline_memory_flow',
        'cases_sha256': hashlib.sha256(CASES.read_bytes()).hexdigest(),
        'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((ROOT/'src/mist').glob('*.py'))},
        'settings': settings.model_dump(mode='json'),
        'identity_sha256': {name: hashlib.sha256(document.model_dump_json().encode()).hexdigest()
                            for name, document in (('constitution', constitution), ('personality', personality))},
        'temperature': 0.2 if real else None, 'output_contract': 'validated text; no tools; finish_reason stop',
        'min_external_start_interval_seconds': 2.1 if real else None,
        'case_set': case_set, 'selected_cases': [case['id'] for case in cases], 'modes': modes,
        'planned_cases': len(modes) * len(cases), 'deadline_seconds': deadline_seconds, 'retries': 0,
        'quality_status': 'pending_manual_review' if real else 'not_measured_simulation',
        'privacy': 'fixed fictitious records only; keys never persisted; runtime databases excluded from publication'}
    records = []
    stopped = False
    started = monotonic()
    write_private(output/'manifest.json', manifest)
    write_private(output/'results.json', records)
    for mode in modes:
        for index, case in enumerate(cases):
            if stopped or monotonic() - started >= deadline_seconds:
                stopped = True
                break
            directory = output / 'runtime' / f'{mode}-{index}'
            seed_app = create_application(audit_path=output/'audit.jsonl', memory_dir=directory)
            try:
                if case.get('hypothesis'):
                    source = seed_app._source().model_copy(update={'origin': 'application'})
                    item = seed_app.memory.remember(MemoryCandidate(content=case['seed'], source=source, state=EpistemicState.HYPOTHESIS))
                else:
                    seed_app.handle(case['seed'])
                    item = seed_app.last_memory_changes[0]
                if case.get('correction'):
                    seed_app.handle(case['correction'])
                    item = seed_app.last_memory_changes[0]
                if case['share']:
                    seed_app.memory.allow_external(item.id)
                if case.get('delete'):
                    seed_app.forget(item.id)
            finally:
                seed_app.close()
            app = None
            capture = None
            record = {'case': case['id'], 'mode': mode, 'query': case['query'], 'rubric': case['rubric'],
                      'seed': case['seed'], 'memory_id': str(item.id), 'complete': False, 'review': None}
            record['setup'] = {name: case[name] for name in ('correction', 'delete') if name in case}
            try:
                app = create_application(ROOT/'examples/nvidia' if real else None, output/'audit.jsonl',
                                         allow_external=real, api_key=api_key, memory_dir=directory)
                app.set_mode(mode)
                key = 'nvidia' if real else 'fake'
                capture = CaptureProvider(app.gateway.providers[key])
                app.gateway.providers[key] = capture
                record['response'] = app.handle(case['query']).model_dump(mode='json')
                record['complete'] = True
            except MistError as exc:
                record['error'] = exc.code.value
                if exc.code in (ErrorCode.RATE_LIMIT, ErrorCode.PROVIDER_AUTH, ErrorCode.AUDIT_FAILURE):
                    stopped = True
            except KeyboardInterrupt:
                record['error'] = 'CANCELLED'
                stopped = True
            finally:
                if capture is not None:
                    record['provider_metadata'] = metadata(capture.delegate)
                    if capture.envelope is not None:
                        record['request_snapshot'] = capture.envelope.model_dump(mode='json')
                        retrieved = []
                        for message in capture.envelope.request.messages:
                            if message.content.startswith('{"retrieved_local_memory":'):
                                retrieved.extend(json.loads(message.content)['retrieved_local_memory'])
                        expected_present = not case.get('delete') and (case['share'] or not real)
                        record['code_checks'] = {
                            'cross_session_item_selection': (any(value['id'] == str(item.id) for value in retrieved) == expected_present),
                            'state_preserved': all(value['state'] == ('hypothesis' if case.get('hypothesis') else 'declared') for value in retrieved),
                            'tools_disabled': app.settings.tools_enabled is False and app.settings.autonomy_level == 0,
                            'current_request_last': capture.envelope.request.messages[-1].content == case['query'],
                        }
                if app is not None:
                    app.close()
                records.append(record)
                write_private(output/'results.json', records)
        if stopped:
            break
    manifest.update(completed_at=datetime.now(timezone.utc).isoformat(), attempted_cases=len(records),
        completed_cases=sum(record['complete'] for record in records), stopped=stopped,
        dispatched_generations=sum('request_snapshot' in record for record in records))
    write_private(output/'manifest.json', manifest)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description='Regressão sintética de memória entre sessões')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--real', action='store_true')
    parser.add_argument('--ask-api-key', action='store_true')
    parser.add_argument('--case-set', choices=('all', 'primary-continuation'), default='all')
    args = parser.parse_args(argv)
    if args.ask_api_key and not args.real:
        print('Entrada oculta exige --real.')
        return 2
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            key = getpass.getpass('Chave NVIDIA (entrada oculta): ') if args.ask_api_key else None
        manifest = run(args.output, real=args.real, api_key=key, case_set=args.case_set)
        key = None
    except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
        print('Entrada oculta indisponível ou cancelada.')
        return 2
    print(json.dumps({key: manifest[key] for key in ('kind','attempted_cases','completed_cases','stopped','quality_status')}))
    return 0 if manifest['completed_cases'] == manifest['planned_cases'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
