"""Explicit synthetic QA data. No reset/delete; every run gets new QA_R2_ IDs."""
import argparse
import asyncio
import csv
import io
import json
import time
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import httpx
from argon2 import PasswordHasher
from app.core.config import settings
from app.core.db import Session
from app.features.employees.models import Employee
from app.features.identity.models import User

PASSWORD = 'qa-demo-r2'


def prepare():
    root = Path(settings().dataset_path)
    employees = json.loads((root / 'employees.json').read_text())['employees']
    roles = json.loads((root / 'skills.json').read_text())['role_profiles']
    prefix = 'QA_R2_' + uuid4().hex[:10]
    flow = deepcopy(next(e for e in employees if e['employee_id'] == 'E0028'))
    flow.update(employee_id=prefix + '_FLOW', full_name='QA Round Two Flow', career_goal=None)
    critical = deepcopy(flow)
    critical.update(employee_id=prefix + '_CRITICAL', full_name='QA Critical Gap', last_review_date='2026-09-01', career_goal={'target_role': 'Backend Engineer', 'target_grade': 'Senior'})
    critical['skills'].update(next(r for r in roles if r['role'] == 'Backend Engineer' and r['grade'] == 'Senior')['required_skills'])
    critical['skills'].update(SK_SYSTEM_DESIGN=2, SK_PUBLIC_SPEAKING=0)
    blocked = deepcopy(critical)
    blocked.update(employee_id=prefix + '_PREREQ', full_name='QA Prerequisites')
    blocked['skills'].update(SK_SYSTEM_DESIGN=1, SK_CLOUD=5, SK_CICD=5)
    cross = deepcopy(next(e for e in employees if e['role'] == 'Data Analyst' and e['grade'] == 'Middle'))
    cross.update(employee_id=prefix + '_CROSS', full_name='QA Cross Role', career_goal={'target_role': 'Product Manager', 'target_grade': 'Middle'})
    with (root / 'activity_history.csv').open() as f:
        reader = csv.DictReader(f); columns = reader.fieldnames
        history = [dict(r, employee_id=flow['employee_id'], record_id=prefix + '_' + r['record_id']) for r in reader if r['employee_id'] == 'E0028']
    for i, day in enumerate(['2026-09-10', '2026-09-17', '2026-09-24']):
        history.append(dict(record_id=prefix + '_MISS' + str(i), employee_id=critical['employee_id'], event_id='EV_036', date=day, due_date='', status='no_show', completion_pct='0', score='', feedback_rating='', assigned_by='self'))
    out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=columns); writer.writeheader(); writer.writerows(history)
    return {'employee_id': flow['employee_id'], 'password': PASSWORD, 'bundle': {'meta': {'dataset': 'Career Quest', 'version': '1.0', 'as_of_date': '2026-10-01'}, 'employees': [flow, critical, blocked, cross]}, 'history_csv': out.getvalue()}


async def account(employee_id):
    if not employee_id.startswith('QA_R2_'):
        raise ValueError('QA account must use QA_R2_ prefix')
    async with Session() as db:
        if await db.get(Employee, employee_id) is None:
            raise ValueError('Import the QA profile first')
        if await db.get(User, employee_id) is None:
            db.add(User(username=employee_id, employee_id=employee_id, role='employee', password_hash=PasswordHasher().hash(PASSWORD)))
            await db.commit()
    print(json.dumps({'username': employee_id, 'password': PASSWORD}))


def verify_ai():
    data = prepare(); report = []
    with httpx.Client(base_url='http://localhost:8000/api/v1', timeout=12) as client:
        client.post('/auth/login', json={'username': 'hr', 'password': settings().hr_password}).raise_for_status()
        response = client.post('/hr/import', files={'employees': ('employees.json', json.dumps(data['bundle']), 'application/json'), 'history': ('history.csv', data['history_csv'], 'text/csv')})
        response.raise_for_status()
        for employee in data['bundle']['employees']:
            eid = employee['employee_id']
            dev = client.get(f'/employees/{eid}/development').json()
            started = time.monotonic()
            r = client.post(f'/employees/{eid}/recommendations?refresh=true'); r.raise_for_status(); result = r.json()
            steps = result['steps']; ids = [s['activity']['event_id'] for s in steps]
            valid = result['source'] == 'ai' and not result['cached'] and 1 <= len(steps) <= 3 and all(len({f['factor'] for f in s['evidence']}) >= 3 for s in steps)
            valid &= set(ids) <= {o['event_id'] for o in dev['available_events']}
            if eid.endswith('_CRITICAL'):
                valid &= bool(steps) and any(g['skill_id'] == 'SK_SYSTEM_DESIGN' for g in steps[0]['activity']['gains'])
            if eid.endswith('_PREREQ'):
                valid &= 'EV_006' not in ids and 'EV_009' not in ids
            if eid.endswith('_CROSS'):
                valid &= dev['goal']['role'] == 'Product Manager'
            report.append({'employee_id': eid, 'source': result['source'], 'cached': result['cached'], 'seconds': round(time.monotonic() - started, 3), 'events': ids, 'quality_pass': bool(valid), 'factors': [len(s['evidence']) for s in steps]})
    print(json.dumps(report, ensure_ascii=False))
    if not all(r['quality_pass'] and r['seconds'] < 10 for r in report):
        raise SystemExit('Live quality verification failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare', 'account', 'verify-ai'])
    parser.add_argument('--employee-id')
    args = parser.parse_args()
    if args.command == 'prepare': print(json.dumps(prepare(), ensure_ascii=False))
    elif args.command == 'account': asyncio.run(account(args.employee_id or ''))
    else: verify_ai()
