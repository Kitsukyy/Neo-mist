import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def summarizer():
    spec = importlib.util.spec_from_file_location('memory_review', ROOT/'evaluations/summarize_memory.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MemoryReviewTests(unittest.TestCase):
    def test_partial_rejected_or_cancelled_cases_do_not_pass_sample_gate(self):
        result = summarizer().summarize(ROOT/'evaluations/results/2026-10-13-nvidia-memory-v1')
        self.assertEqual((result['completed'],result['approved'],result['unattempted']), (7,6,2))
        self.assertEqual(result['errors'], {'CANCELLED':1})
        self.assertFalse(result['sample_gate_passed'])

    def test_tampered_evidence_missing_review_and_simulation_are_rejected(self):
        for change in ('responses','review','simulation','duplicate'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                target=Path(directory)/'run'
                shutil.copytree(ROOT/'evaluations/results/2026-10-13-nvidia-memory-v1',target)
                if change=='responses':
                    with (target/'results.json').open('a') as stream:
                        stream.write(' ')
                elif change in ('review','duplicate'):
                    path=target/'review.json'
                    review=json.loads(path.read_text())
                    if change=='review': review['rows'].pop()
                    else: review['rows'].append(review['rows'][0])
                    path.write_text(json.dumps(review))
                else:
                    path=target/'manifest.json'
                    manifest=json.loads(path.read_text())
                    manifest['kind']='offline_memory_flow'
                    path.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    summarizer().summarize(target)

    def test_cancelled_response_cannot_be_promoted_to_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'run'
            shutil.copytree(ROOT/'evaluations/results/2026-10-13-nvidia-memory-v1',target)
            path=target/'review.json'
            review=json.loads(path.read_text())
            review['rows'][-1]['passed']=True
            path.write_text(json.dumps(review))
            with self.assertRaises(ValueError):
                summarizer().summarize(target)
