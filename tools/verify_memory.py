"""Reproducible synthetic lexical probe; not a natural-language model eval."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import statistics
import subprocess
import tempfile
from time import perf_counter
from uuid import UUID, uuid5

from mist import __version__
from mist.memory import MemoryStore
from mist.memory_types import MemoryCandidate, MemoryItem, MemorySource, MemoryStatus
from mist.schemas import Sensitivity


def run():
    root = Path(__file__).resolve().parents[1]
    namespace = UUID('c6cc58ce-b951-4b0f-9a96-d71cfa7152cc')
    stamp = '2026-10-13T00:00:00+00:00'
    with tempfile.TemporaryDirectory(prefix='mist-memory-probe-') as directory:
        store = MemoryStore(Path(directory) / 'memory')
        try:
            # Deterministic IDs and unique lexical anchors. Batched setup is excluded
            # from query timings and does not claim production ingestion throughput.
            with store.transaction():
                for index in range(10000):
                    source = MemorySource(origin='user', session_id=namespace,
                        message_id=uuid5(namespace, str(index)), timestamp=stamp)
                    value = MemoryCandidate(content=f'Registro sintético marco{index:05d} decisão validada.',
                        source=source, project='aurora' if index % 2 else None,
                        sensitivity=Sensitivity.LOCAL_ONLY if index % 3 == 0 else Sensitivity.EXTERNAL_ALLOWED)
                    item = MemoryItem(id=uuid5(namespace, 'item-' + str(index)), candidate=value, sources=(source,),
                        status=MemoryStatus.ACTIVE, created_at=stamp, updated_at=stamp)
                    store._save(item)
            measurements, trials = [], []
            for index in range(100):
                query_index = index * 97
                project = 'aurora'
                external = index % 2 == 0
                expected = [] if external and query_index % 3 == 0 else [str(uuid5(namespace, 'item-' + str(query_index)))]
                start = perf_counter()
                found = store.retrieve(f'marco{query_index:05d}', project, external=external)
                elapsed = (perf_counter() - start) * 1000
                ids = [str(item.id) for item in found]
                measurements.append(elapsed)
                trials.append({'index': query_index, 'query': f'marco{query_index:05d}', 'project': project,
                    'external': external, 'expected': expected, 'actual': ids, 'passed': ids == expected,
                    'duration_ms': elapsed})
            other_scope = store.retrieve('marco00001', 'luna')
            missing = store.retrieve('inexistente99999', 'aurora')
            scored = [trial for trial in trials if trial['expected']]
            precision = sum(len(set(t['actual']) & set(t['expected'])) / max(1, len(t['actual'])) for t in scored) / len(scored)
            recall = sum(len(set(t['actual']) & set(t['expected'])) / len(t['expected']) for t in scored) / len(scored)
            return {'application_version': __version__, 'verified_at': datetime.now(timezone.utc).isoformat(),
                'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
                'platform': platform.platform(), 'source_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
                'source_sha256': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted((root/'src/mist').glob('*.py'))},
                'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'corpus_size': 10000,
                'setup': 'batched synthetic insertion; excluded from query latency',
                'scope': 'unique-anchor lexical queries; warm connection, filesystem cache uncontrolled; retrieval includes SQLite metadata audit commit',
                'trials': trials, 'precision_of_returned_items_nonempty_ground_truth': precision,
                'recall_up_to_5_nonempty_ground_truth': recall, 'correct_empty_results': sum(t['passed'] for t in trials if not t['expected']),
                'latency_ms': {'p50': statistics.median(measurements), 'p95_nearest_rank': sorted(measurements)[94]},
                'cross_project_filtered': not other_scope, 'missing_query_empty': not missing,
                'passed': all(t['passed'] for t in trials) and not other_scope and not missing,
                'limitations': 'Synthetic unique tokens do not establish semantic retrieval quality or the proposed production latency target.'}
        finally:
            store.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('corpus_size','passed','latency_ms')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
