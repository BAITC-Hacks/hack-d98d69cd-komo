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
        profile('ONLINE', 'Backend Engineer', gaps={'SK_SYSTEM_DESIGN': 3}),
        profile('OFFLINE', 'Backend Engineer', gaps={'SK_SYSTEM_DESIGN': 3}),
        profile('RECENTONLINE', 'Backend Engineer', gaps={'SK_SYSTEM_DESIGN': 3}),
        profile('RECENTOFFLINE', 'Backend Engineer', gaps={'SK_SYSTEM_DESIGN': 3}),
    ]
    history = [dict(record_id=prefix + '_MISS' + str(i), employee_id=profiles[1]['employee_id'],
                    event_id='EV_036', date=day, due_date='', status='no_show', completion_pct=0,
                    score='', feedback_rating='', assigned_by='self')
               for i, day in enumerate(['2026-09-10', '2026-09-17', '2026-09-24'])]
    # Counterfactual pairs: identical skills/candidates, opposite participation history.
    # Expectations are fixed here before the model is called.
    for p in profiles[6:]:
        case = p['employee_id'].rsplit('_', 1)[1]
        bad_event = 'EV_006' if case.endswith('ONLINE') else 'EV_007'
        good_event = 'EV_007' if bad_event == 'EV_006' else 'EV_006'
        attempts = [(bad_event, day) for day in ('2026-09-10', '2026-09-17', '2026-09-24')]
        if case.startswith('RECENT'):
            # Old negative history for the alternative must not dominate recent evidence.
            attempts += [(good_event, day) for day in ('2025-06-01', '2025-07-01', '2025-08-01')]
        history.extend(dict(record_id=p['employee_id'] + '_MISS' + str(i), employee_id=p['employee_id'],
                            event_id=event, date=day, due_date='', status='no_show', completion_pct=0,
                            score='', feedback_rating='', assigned_by='self') for i, (event, day) in enumerate(attempts))
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
    if case in ('ONLINE', 'OFFLINE', 'RECENTONLINE', 'RECENTOFFLINE'):
        expected = 'EV_007' if case.endswith('ONLINE') else 'EV_006'
        candidates = {o['event_id'] for o in development['available_events']}
        return {'EV_006', 'EV_007'} <= candidates and first['event_id'] == expected and any(f['factor'] == 'history' for f in steps[0]['evidence'])
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
                               'candidate_count': len(dev['available_events']),
                               'factor_groups': [len({f['factor'] for f in s['evidence']}) for s in result['steps']]})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not all(r['quality_pass'] and r['seconds'] < 10 for r in report):
        raise SystemExit('Live acceptance failed; inspect individual cases, do not count fallback as AI.')


async def verify_history():
    """Hold candidate order constant, then reverse it: the model must use context."""
    from app.core.db import Session
    from app.features.catalog.service import load_catalog
    from app.features.data_import.service import parse_history
    from app.features.development.logic import calculate_development
    from app.features.recommendations.service import model_payload, select_with_ai, validate_plan, evidence_for
    data = prepare(); history = parse_history(data['history_csv'].encode()); report = []
    async with Session() as db:
        catalog = await load_catalog(db)
    for profile in data['bundle']['employees'][6:]:
        case = profile['employee_id'].rsplit('_', 1)[1]
        records = [r for r in history if r['employee_id'] == profile['employee_id']]
        development = calculate_development(profile, records, catalog, '2026-10-01', 1)
        for reverse in (False, True):
            ordered = sorted(development.available_events, key=lambda e: e.event_id, reverse=reverse)
            payload = model_payload(profile, development, ordered, records, catalog)
            started = time.monotonic()
            plan = await select_with_ai(payload)
            ids = validate_plan(plan, {e.event_id: evidence_for(profile, development, e, records, catalog) for e in ordered})
            expected = 'EV_007' if case.endswith('ONLINE') else 'EV_006'
            valid = len(ordered) >= 2 and ids[0] == expected and expected + ':history' in plan.selections[0].fact_ids
            report.append({'case': case, 'candidate_order': [e.event_id for e in ordered], 'chosen': ids,
                           'expected_first': expected, 'quality_pass': valid, 'seconds': round(time.monotonic() - started, 3)})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not all(r['quality_pass'] and r['seconds'] < 10 for r in report):
        raise SystemExit('History/order acceptance failed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=['prepare', 'account', 'verify-ai', 'verify-history'])
    parser.add_argument('--employee-id'); parser.add_argument('--repeats', type=int, choices=range(1, 6), default=3)
    args = parser.parse_args()
    if args.command == 'prepare': print(json.dumps(prepare(), ensure_ascii=False))
    elif args.command == 'account': asyncio.run(account(args.employee_id or ''))
    elif args.command == 'verify-history': asyncio.run(verify_history())
    else: verify_ai(args.repeats)
