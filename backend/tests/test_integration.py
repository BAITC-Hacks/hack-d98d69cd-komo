import asyncio
import json
import uuid
from copy import deepcopy
from pathlib import Path
import pytest
from sqlalchemy import select, func
from app.core.config import settings
from app.core.db import Session
from app.features.employees.models import Employee
from app.features.development.models import ActivityRecord
from app.features.recommendations import service
from conftest import login


async def test_authentication_and_roles(client):
    assert (await client.get('/api/v1/employees/E0001')).status_code == 401
    assert (await client.post('/api/v1/auth/login', json={'username': 'hr', 'password': 'wrong'})).status_code == 401
    await login(client)
    assert (await client.get('/api/v1/employees/' + settings().employee_id)).status_code == 200
    assert (await client.get('/api/v1/employees/E0001')).status_code == 403
    assert (await client.get('/api/v1/hr/overview')).status_code == 403
    assert (await client.post('/api/v1/hr/import')).status_code == 403
    assert (await client.post('/api/v1/auth/logout', headers={'Origin': 'https://foreign.invalid'})).status_code == 403
    await login(client, 'hr')
    assert (await client.get('/api/v1/employees/E0002')).status_code == 200
    assert (await client.post('/api/v1/employees/E0001/activities/EV_005/complete', json={'idempotency_key': 'hr-cannot-write'})).status_code == 403


async def test_completion_concurrent_retry_and_stale_recommendation(client, dataset):
    from argon2 import PasswordHasher
    from app.features.identity.models import User
    await login(client, 'hr')
    e = deepcopy(next(x for x in dataset[0] if x['employee_id'] == 'E0028'))
    e['employee_id'] = 'TEST_COMPLETE_' + uuid.uuid4().hex[:8]
    employee_id = e['employee_id']
    bundle = {'meta': {'dataset': 'Career Quest', 'version': '1.0', 'as_of_date': '2026-10-01'}, 'employees': [e]}
    assert (await client.post('/api/v1/hr/import', files={'employees': ('employees.json', json.dumps(bundle))})).status_code == 200
    async with Session() as db:
        db.add(User(username=employee_id, role='employee', employee_id=employee_id, password_hash=PasswordHasher().hash('test-local-only')))
        await db.commit()
    assert (await client.post('/api/v1/auth/login', json={'username': employee_id, 'password': 'test-local-only'})).status_code == 200
    rec = await client.post(f'/api/v1/employees/{employee_id}/recommendations')
    assert rec.status_code == 200 and rec.json()['source'] == 'ai'
    assert all(len(s['evidence']) >= 3 for s in rec.json()['steps'])
    before = (await client.get(f'/api/v1/employees/{employee_id}/development')).json()
    option = next(o for o in before['available_events'] if o['can_complete'])
    path = f"/api/v1/employees/{employee_id}/activities/{option['event_id']}/complete"
    body = {'idempotency_key': str(uuid.uuid4()), 'record_id': option['record_id']}
    first, repeated = await asyncio.gather(client.post(path, json=body), client.post(path, json=body))
    assert first.status_code == repeated.status_code == 200, (first.text, repeated.text)
    assert first.json() == repeated.json()
    assert first.json()['development']['progress'] > before['progress']
    changed = (await client.get(f'/api/v1/employees/{employee_id}/development')).json()
    assert changed['progress'] == first.json()['development']['progress']
    rec_state = (await client.get(f'/api/v1/employees/{employee_id}/recommendations')).json()
    assert rec_state['status'] == 'stale'
    rejected = await client.post(path, json={'idempotency_key': str(uuid.uuid4())})
    assert rejected.status_code == 409
    rows = (await client.get(f'/api/v1/employees/{employee_id}/history')).json()
    assert sum(r['record_id'] == first.json()['record_id'] for r in rows) == 1


async def test_import_new_profile_history_and_atomic_error(client, dataset):
    await login(client, 'hr')
    e = deepcopy(dataset[0][0]); e['employee_id'] = 'TEST_' + uuid.uuid4().hex[:10]; e['full_name'] = 'Synthetic Test Profile'
    bundle = {'meta': {'dataset': 'Career Quest', 'version': '1.0', 'as_of_date': '2026-10-01'}, 'employees': [e]}
    csv = 'record_id,employee_id,event_id,date,due_date,status,completion_pct,score,feedback_rating,assigned_by\n' + f"TEST_R_{uuid.uuid4().hex},{e['employee_id']},EV_005,2026-09-29,,dropped,40,,,self\n"
    files = {'employees': ('employees.json', json.dumps(bundle), 'application/json'), 'history': ('history.csv', csv, 'text/csv')}
    result = await client.post('/api/v1/hr/import', files=files)
    assert result.status_code == 200, result.text
    assert result.json()['employees_created'] == result.json()['history_created'] == 1
    again = await client.post('/api/v1/hr/import', files=files)
    assert again.json()['employees_created'] == again.json()['history_created'] == 0
    assert again.json()['revision'] == result.json()['revision']
    assert (await client.post(f"/api/v1/employees/{e['employee_id']}/recommendations")).json()['source'] == 'ai'
    # A profile and invalid history must never be partially applied.
    e['employee_id'] = 'INVALID_' + uuid.uuid4().hex[:10]
    broken = await client.post('/api/v1/hr/import', files={'employees': ('employees.json', json.dumps(bundle)), 'history': ('history.csv', csv.replace('EV_005', 'UNKNOWN'))})
    assert broken.status_code == 422
    assert (await client.get(f"/api/v1/employees/{e['employee_id']}")).status_code == 404


async def test_fallback_and_redis_failure(client, monkeypatch):
    await login(client, 'hr')
    async def unavailable(*args, **kwargs):
        raise TimeoutError()
    async def cache_miss(*args, **kwargs):
        return None
    monkeypatch.setattr(service, 'select_with_ai', unavailable)
    monkeypatch.setattr(service, 'cache_get', cache_miss)
    result = await client.post('/api/v1/employees/E0002/recommendations')
    assert result.status_code == 200 and result.json()['source'] == 'fallback'
    assert result.json()['steps']
    assert all(len(s['evidence']) >= 3 for s in result.json()['steps'])


async def test_hr_aggregates_match_database(client):
    await login(client, 'hr')
    result = await client.get('/api/v1/hr/overview')
    assert result.status_code == 200, result.text
    data = result.json()
    async with Session() as db:
        assert data['total_employees'] == await db.scalar(select(func.count()).select_from(Employee))
        assert data['total_participations'] == await db.scalar(select(func.count()).select_from(ActivityRecord))
    assert sum(e['total'] for e in data['participation']) == data['total_participations']


async def test_seed_does_not_reset_data(client):
    from app.seed import seed
    async with Session() as db:
        before = await db.scalar(select(func.count()).select_from(ActivityRecord))
    await seed()
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(ActivityRecord)) == before
