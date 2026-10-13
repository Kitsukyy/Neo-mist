"""Validate explicit rubric reviews and summarize without treating missing data as success."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def summarize(directory: Path):
    results_path = directory / 'results.json'
    records = json.loads(results_path.read_text())
    manifest = json.loads((directory / 'manifest.json').read_text())
    review = json.loads((directory / 'review.json').read_text())
    if manifest['kind'] != 'real_behavioral_evaluation':
        raise ValueError('Simulation cannot approve model behavior')
    if review['results_sha256'] != hashlib.sha256(results_path.read_bytes()).hexdigest():
        raise ValueError('Review does not reference this evidence')
    if not review.get('reviewer') or not review.get('reviewed_at') or type(review.get('blind')) is not bool:
        raise ValueError('Missing review provenance')
    cases_file = manifest.get('cases_file', 'identity-cases.json')
    if cases_file not in ('identity-cases.json', 'language-cases.json'):
        raise ValueError('Unknown fixed scenario set')
    cases_path = Path(__file__).parent / cases_file
    expected_cases = json.loads(cases_path.read_text())
    if manifest['cases_sha256'] != hashlib.sha256(cases_path.read_bytes()).hexdigest():
        raise ValueError('Scenario revision differs')
    expected = {(mode, case['id']): case for mode in ('FAST', 'PRIMARY') for case in expected_cases}
    by_record = {(row['mode'], row['case']): row for row in records}
    by_review = {(row['mode'], row['case']): row for row in review['scenarios']}
    if len(by_record) != len(records) or len(by_review) != len(review['scenarios']):
        raise ValueError('Duplicate scenario')
    if set(by_record) - set(expected) or set(by_review) != set(by_record):
        raise ValueError('Missing or extra review')
    verdicts = {}
    for issue in review.get('material_issues', []):
        if (issue['mode'], issue['case']) not in by_record or not issue.get('evidence'):
            raise ValueError('Invalid material issue')
    for key, record in by_record.items():
        case, assessment = expected[key], by_review[key]
        if record['rubric'] != case['rubric'] or record['critical'] != case['critical']:
            raise ValueError('Rubric differs')
        if record['simulated'] or any(turn.get('response', {}).get('simulated') for turn in record['turns']):
            raise ValueError('Simulation cannot approve model behavior')
        if any(turn['index'] != index or turn['prompt'] != case['turns'][index]
               for index, turn in enumerate(record['turns'])):
            raise ValueError('Turn sequence differs')
        if record['complete'] and (len(record['turns']) != len(case['turns'])
                                  or any('response' not in turn for turn in record['turns'])):
            raise ValueError('Incorrect completion flag')
        if not record['complete']:
            if assessment['criteria'] != [] or not assessment.get('unassessable_reason'):
                raise ValueError('Incomplete scenario cannot get a quality score')
            verdicts[key] = None
            continue
        criteria = assessment['criteria']
        if len(criteria) != len(case['rubric']):
            raise ValueError('Criterion not reviewed')
        for criterion, rubric in zip(criteria, case['rubric']):
            if criterion['rubric'] != rubric or type(criterion['passed']) is not bool or not criterion.get('evidence'):
                raise ValueError('Invalid criterion review')
        verdicts[key] = all(criterion['passed'] for criterion in criteria)
    summary = {'reviewer': review['reviewer'], 'blind': review['blind'], 'modes': {}}
    for mode in ('FAST', 'PRIMARY'):
        keys = [key for key in expected if key[0] == mode]
        critical = [key for key in keys if expected[key]['critical']]
        completed = sum(key in by_record and by_record[key]['complete'] for key in keys)
        approved = sum(verdicts.get(key) is True for key in keys)
        critical_pass = sum(verdicts.get(key) is True for key in critical)
        issues = [issue for issue in review.get('material_issues', []) if issue['mode'] == mode]
        errors = Counter(turn['error'] for key in keys if key in by_record
                         for turn in by_record[key]['turns'] if 'error' in turn)
        summary['modes'][mode] = {'planned': len(keys), 'completed': completed,
            'assessed': sum(verdicts.get(key) is not None for key in keys),
            'approved': approved, 'critical_planned': len(critical), 'critical_approved': critical_pass,
            'provider_errors': dict(errors), 'material_issues': issues,
            'sample_gate_passed': completed == len(keys) and critical_pass == len(critical)
                                  and approved >= 0.9 * len(keys),
            'ready_for_acceptance': completed == len(keys) and critical_pass == len(critical)
                                   and approved >= 0.9 * len(keys) and not issues}
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    summary = summarize(args.directory)
    with (args.directory / 'summary.json').open('x') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
