"""Require source-linked reviews; missing/cancelled responses never imply success."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

CASES = Path(__file__).with_name('memory-cases.json')


def summarize(directory):
    directory = Path(directory)
    results_path = directory/'results.json'
    records = json.loads(results_path.read_text())
    manifest = json.loads((directory/'manifest.json').read_text())
    review = json.loads((directory/'review.json').read_text())
    if manifest['kind'] != 'real_synthetic_memory_regression':
        raise ValueError('Simulation cannot approve model quality')
    if manifest['cases_sha256'] != hashlib.sha256(CASES.read_bytes()).hexdigest():
        raise ValueError('Dataset revision differs')
    if review['results_sha256'] != hashlib.sha256(results_path.read_bytes()).hexdigest():
        raise ValueError('Review refers to different responses')
    if not review.get('reviewer') or not review.get('reviewed_at') or review.get('blind') is not False or review.get('independent') is not False:
        raise ValueError('Missing or unsupported review provenance')
    cases = {case['id']: case for case in json.loads(CASES.read_text())}
    selection = manifest.get('case_set', 'all')
    if selection == 'all':
        expected = {(mode, case) for mode in ('FAST','PRIMARY') for case in cases}
    elif selection == 'primary-continuation':
        expected = {('PRIMARY', case) for case in
                    ('hypothesis_not_fact','corrected_name_current_revision','deleted_name_absent')}
    else:
        raise ValueError('Unknown fixed selection')
    if manifest['planned_cases'] != len(expected):
        raise ValueError('Incorrect planned count')
    by_record = {(row['mode'],row['case']):row for row in records}
    by_review = {(row['mode'],row['case']):row for row in review['rows']}
    if len(by_record) != len(records) or len(by_review) != len(review['rows']):
        raise ValueError('Duplicate case')
    if set(by_record)-expected or set(by_review) != set(by_record):
        raise ValueError('Missing or extra review')
    approved, complete, errors = Counter(), Counter(), Counter()
    for key, row in by_record.items():
        case, assessment = cases[key[1]], by_review[key]
        if row['rubric'] != case['rubric'] or row['query'] != case['query']:
            raise ValueError('Rubric or query differs')
        if not row['complete']:
            if assessment['criteria'] is not None or assessment['passed'] is not None or not row.get('error'):
                raise ValueError('Incomplete response cannot receive a score')
            errors[row['error']] += 1
            continue
        if row.get('error') or not row.get('response',{}).get('text') or row['response'].get('simulated') is not False:
            raise ValueError('Invalid completion')
        criteria = assessment['criteria']
        if set(criteria) != set(case['rubric']) or any(type(value) is not bool for value in criteria.values()) or not assessment.get('note'):
            raise ValueError('Criterion review missing')
        checks = row.get('code_checks',{})
        if set(checks) != {'cross_session_item_selection','state_preserved','tools_disabled','current_request_last'} or any(type(value) is not bool for value in checks.values()):
            raise ValueError('Code checks missing')
        verdict = all(criteria.values()) and all(checks.values())
        if assessment['passed'] is not verdict:
            raise ValueError('Review verdict inconsistent')
        complete[key[0]] += 1
        approved[key[0]] += verdict
    return {'reviewer':review['reviewer'], 'blind':False, 'independent':False,
            'planned':len(expected), 'attempted':len(records), 'completed':sum(complete.values()),
            'approved':sum(approved.values()), 'unattempted':len(expected)-len(records), 'errors':dict(errors),
            'modes':{mode:{'planned':sum(key[0]==mode for key in expected), 'completed':complete[mode], 'approved':approved[mode]} for mode in sorted({key[0] for key in expected})},
            'sample_gate_passed':sum(approved.values()) == len(expected),
            'scope':'fixed directed synthetic sample only; no universal or production acceptance'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    args = parser.parse_args()
    summary = summarize(args.directory)
    with (args.directory/'summary.json').open('x') as stream:
        json.dump(summary,stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == '__main__':
    main()
