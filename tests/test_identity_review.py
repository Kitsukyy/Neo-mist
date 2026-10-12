import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / 'evaluations/identity-cases.json'


def summarize(directory):
    spec = importlib.util.spec_from_file_location('identity_summary', ROOT / 'evaluations/summarize_identity.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.summarize(directory)


def evidence():
    cases = json.loads(CASES_PATH.read_text())
    records, reviews = [], []
    for mode in ('FAST', 'PRIMARY'):
        for case in cases:
            records.append({'case': case['id'], 'mode': mode, 'critical': case['critical'],
                'rubric': case['rubric'], 'complete': True, 'simulated': False,
                'turns': [{'index': i, 'prompt': prompt, 'response': {'simulated': False, 'text': 'synthetic test'}}
                          for i, prompt in enumerate(case['turns'])]})
            reviews.append({'case': case['id'], 'mode': mode, 'criteria': [
                {'rubric': rubric, 'passed': True, 'evidence': 'synthetic test review'} for rubric in case['rubric']]})
    return records, {'reviewer': 'synthetic-test', 'reviewed_at': '2026-10-12', 'blind': False, 'scenarios': reviews}


def write(directory, records, review):
    directory.joinpath('results.json').write_text(json.dumps(records))
    review = copy.deepcopy(review)
    review['results_sha256'] = hashlib.sha256(directory.joinpath('results.json').read_bytes()).hexdigest()
    directory.joinpath('review.json').write_text(json.dumps(review))
    directory.joinpath('manifest.json').write_text(json.dumps({'kind': 'real_behavioral_evaluation',
        'cases_sha256': hashlib.sha256(CASES_PATH.read_bytes()).hexdigest()}))


class IdentityReviewTests(unittest.TestCase):
    def test_critical_failure_cannot_be_hidden_by_other_model_success(self):
        records, review = evidence()
        review['scenarios'][0]['criteria'][0]['passed'] = False
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            write(directory, records, review)
            result = summarize(directory)['modes']
        self.assertFalse(result['FAST']['sample_gate_passed'])
        self.assertTrue(result['PRIMARY']['sample_gate_passed'])
        self.assertEqual(result['FAST']['critical_approved'], result['FAST']['critical_planned'] - 1)

    def test_provider_failure_is_unassessed_and_blocks_complete_sample_gate(self):
        records, review = evidence()
        records[3]['complete'] = False
        records[3]['turns'] = [{'index': 0, 'prompt': records[3]['turns'][0]['prompt'], 'error': 'PROVIDER_TIMEOUT'}]
        review['scenarios'][3]['criteria'] = []
        review['scenarios'][3]['unassessable_reason'] = 'provider failure'
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            write(directory, records, review)
            result = summarize(directory)['modes']['FAST']
        self.assertEqual(result['assessed'], 11)
        self.assertEqual(result['approved'], 11)
        self.assertEqual(result['provider_errors'], {'PROVIDER_TIMEOUT': 1})
        self.assertFalse(result['sample_gate_passed'])

    def test_material_issue_blocks_acceptance_even_when_rubrics_pass(self):
        records, review = evidence()
        review['material_issues'] = [{'mode': 'FAST', 'case': records[0]['case'], 'evidence': 'incorrect operational explanation'}]
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            write(directory, records, review)
            result = summarize(directory)['modes']['FAST']
        self.assertTrue(result['sample_gate_passed'])
        self.assertFalse(result['ready_for_acceptance'])

    def test_missing_review_duplicates_tampering_and_simulation_never_approve(self):
        for variant in ('missing', 'duplicate', 'hash', 'simulation', 'criterion'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temp:
                records, review = evidence()
                if variant == 'missing':
                    review['scenarios'].pop()
                if variant == 'duplicate':
                    review['scenarios'].append(review['scenarios'][0])
                if variant == 'simulation':
                    records[0]['simulated'] = True
                if variant == 'criterion':
                    review['scenarios'][0]['criteria'].pop()
                directory = Path(temp)
                write(directory, records, review)
                if variant == 'hash':
                    directory.joinpath('results.json').write_text(json.dumps(records) + '\n')
                with self.assertRaises(ValueError):
                    summarize(directory)

    def test_unknown_case_file_cannot_select_arbitrary_data(self):
        records, review = evidence()
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            write(directory, records, review)
            path = directory / 'manifest.json'
            manifest = json.loads(path.read_text())
            manifest['cases_file'] = '../../secret.json'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Unknown fixed scenario set'):
                summarize(directory)
