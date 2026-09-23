"""Round-three acceptance: entirely synthetic profiles; expectations declared before AI calls.
No real employee record is copied. Network payload excludes names and identifiers.
"""
import argparse
import asyncio
import csv
import io
import json
import time
from pathlib import Path
from uuid import uuid4
import httpx
from app.core.config import settings
from app.qa_demo import account, PASSWORD
from app.features.data_import.service import HISTORY_COLUMNS


def prepare():
    roles = json.loads((Path(settings().dataset_path) / 'skills.json').read_text())['role_profiles']
    prefix = 'QA_R3_' + uuid4().hex[:10]
    def profile(case, role, target_role=None, gaps=None):
        target_role = target_role or role
        target_grade = 'Middle' if case == 'CROSS' else 'Senior'
        skills = dict(next(r for r in roles if r['role'] == target_role and r['grade'] == target_grade)['required_skills'])
        skills.update(gaps or {})
        return dict(employee_id=prefix + '_' + case, full_name='QA Synthetic ' + case,
                    department='QA acceptance', role=role, grade='Middle', manager_id=None,
                    hire_date='2025-01-01', tenure_months=21, work_format='remote', preferred_language='ru',
                    career_goal={'target_role': target_role, 'target_grade': target_grade},
                    skills=skills, last_review_date='2026-09-01')
    profiles = [
        profile('FLOW', 'Backend Engineer', gaps={'SK_PYTHON': 2, 'SK_CLOUD': 1}),
        profile('CRITICAL', 'Backend Engineer', gaps={'SK_SYSTEM_DESIGN': 2, 'SK_PUBLIC_SPEAKING': 0}),
        profile('PREP', 'Frontend Engineer', gaps={'SK_TYPESCRIPT': 2, 'SK_WEB_PERFORMANCE': 3, 'SK_PUBLIC_SPEAKING': 0}),
        profile('BLOCKED', 'Data Analyst', gaps={'SK_STATISTICS': 0, 'SK_ML_BASICS': 0}),
        profile('CROSS', 'Data Analyst', target_role='Product Manager', gaps={'SK_PRODUCT_ANALYTICS': 2, 'SK_STATISTICS': 1}),
        profile('EMPTY', 'Backend Engineer'),
    ]
    history = [dict(record_id=prefix + '_MISS' + str(i), employee_id=profiles[1]['employee_id'],
                    event_id='EV_036', date=day, due_date='', status='no_show', completion_pct=0,
                    score='', feedback_rating='', assigned_by='self')
               for i, day in enumerate(['2026-09-10', '2026-09-17', '2026-09-24'])]
    out = io.StringIO(); w = csv.DictWriter(out, fieldnames=HISTORY_COLUMNS); w.writeheader(); w.writerows(history)
    return {'employee_id': profiles[0]['employee_id'], 'password': PASSWORD,
            'bundle': {'meta': {'dataset': 'Career Quest', 'version': '1.0', 'as_of_date': '2026-10-01'}, 'employees': profiles},
            'history_csv': out.getvalue()}


def quality(case, result, development):
    steps = result['steps']; ids = [s['activity']['event_id'] for s in steps]
    if case == 'EMPTY':
        return not steps and bool(development['availability_reasons']) and development['progress'] == 100
    valid = (result['source'] == 'ai' and not result['cached'] and not result['stale'] and 1 <= len(steps) <= 3
             and len(ids) == len(set(ids)) and set(ids) <= {o['event_id'] for o in development['available_events']}
             and all(len({f['factor'] for f in s['evidence']}) >= 3 for s in steps))
    if not valid: return False
    first = steps[0]['activity']
    if case == 'FLOW': return set(ids) <= {'EV_009', 'EV_012'} and first['format'] == 'self_paced'
    if case == 'CRITICAL': return any(g['skill_id'] == 'SK_SYSTEM_DESIGN' for g in first['gains'])
    if case == 'PREP': return first['event_id'] == 'EV_013' and 'EV_014' in first['preparatory_for'] and 'EV_014' not in ids
    if case == 'BLOCKED': return first['event_id'] == 'EV_020' and 'EV_024' not in ids and 'EV_021' not in ids
    if case == 'CROSS': return development['goal']['role'] == 'Product Manager' and any(g['skill_id'] == 'SK_PRODUCT_ANALYTICS' for g in first['gains'])
    return False


def verify_ai(repeats):
    data = prepare(); report = []
    with httpx.Client(base_url='http://localhost:8000/api/v1', timeout=12) as client:
        client.post('/auth/login', json={'username': 'hr', 'password': settings().hr_password}).raise_for_status()
        response = client.post('/hr/import', files={'employees': ('employees.json', json.dumps(data['bundle']), 'application/json'),
                                                   'history': ('history.csv', data['history_csv'], 'text/csv')})
        response.raise_for_status()
        for employee in data['bundle']['employees']:
            eid = employee['employee_id']; case = eid.rsplit('_', 1)[1]
            dev_response = client.get(f'/employees/{eid}/development'); dev_response.raise_for_status(); dev = dev_response.json()
            for attempt in range(1 if case == 'EMPTY' else repeats):
                started = time.monotonic()
                response = client.post(f'/employees/{eid}/recommendations?refresh=true'); response.raise_for_status(); result = response.json()
                seconds = round(time.monotonic() - started, 3)
                report.append({'case': case, 'attempt': attempt + 1, 'employee_id': eid, 'source': result['source'],
                               'cached': result['cached'], 'seconds': seconds, 'events': [s['activity']['event_id'] for s in result['steps']],
                               'quality_pass': bool(quality(case, result, dev)),
                               'factor_groups': [len({f['factor'] for f in s['evidence']}) for s in result['steps']]})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not all(r['quality_pass'] and r['seconds'] < 10 for r in report):
        raise SystemExit('Live acceptance failed; inspect individual cases, do not count fallback as AI.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=['prepare', 'account', 'verify-ai'])
    parser.add_argument('--employee-id'); parser.add_argument('--repeats', type=int, choices=range(1, 6), default=3)
    args = parser.parse_args()
    if args.command == 'prepare': print(json.dumps(prepare(), ensure_ascii=False))
    elif args.command == 'account': asyncio.run(account(args.employee_id or ''))
    else: verify_ai(args.repeats)
