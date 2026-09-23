import json
from copy import deepcopy
from uuid import uuid4
from app.qa_acceptance import prepare
from app.features.development.logic import effective_skills, completion_identity
from conftest import login


def completed(eid, event='EV_012', day='2026-09-20'):
    return dict(record_id='QA_R4_' + uuid4().hex, employee_id=eid, event_id=event,
                date=day, due_date=None, status='completed', completion_pct=100,
                score=90, feedback_rating=5, assigned_by='self')


async def upload(client, profiles, history):
    return await client.post('/api/v1/hr/import', files={'employees': ('all.json', json.dumps({'employees': profiles, 'history': history}))})


async def test_duplicate_completion_is_atomic_across_imports(client):
    await login(client, 'hr')
    p = prepare()['bundle']['employees'][0]; eid = p['employee_id']
    first, duplicate = completed(eid), completed(eid, day='2026-09-21')
    rejected = await upload(client, [p], [first, duplicate])
    assert rejected.status_code == 422 and rejected.json()['code'] == 'duplicate_completion'
    assert (await client.get(f'/api/v1/employees/{eid}')).status_code == 404
    assert (await upload(client, [p], [first])).status_code == 200
    before = (await client.get(f'/api/v1/employees/{eid}/development')).json()
    changed = dict(p, full_name='Must not be saved')
    rejected = await upload(client, [changed], [duplicate])
    assert rejected.status_code == 422
    assert (await client.get(f'/api/v1/employees/{eid}')).json()['full_name'] == p['full_name']
    assert (await client.get(f'/api/v1/employees/{eid}/development')).json()['progress'] == before['progress']
    repeated = await upload(client, [p], [first])
    assert repeated.status_code == 200 and repeated.json()['history_created'] == 0
    # A formerly incomplete record cannot be updated to duplicate a completion.
    pending = dict(duplicate, status='in_progress', completion_pct=30)
    assert (await upload(client, [], [pending])).status_code == 200
    assert (await upload(client, [], [duplicate])).status_code == 422


async def test_recurring_sessions_and_compliance_keep_distinct_dates(client):
    await login(client, 'hr')
    p = prepare()['bundle']['employees'][0]; eid = p['employee_id']
    records = [completed(eid, event, day) for event in ('EV_036', 'EV_001') for day in ('2026-09-10', '2026-09-17')]
    assert (await upload(client, [p], records)).status_code == 200
    assert (await upload(client, [], [completed(eid, 'EV_036', '2026-09-17')])).status_code == 422


def test_semantic_duplicates_do_not_inflate_skills(dataset):
    p = deepcopy(dataset[0][0]); p['skills']['SK_PYTHON'] = 1; p['last_review_date'] = '2026-09-01'
    first, second = completed(p['employee_id']), completed(p['employee_id'], day='2026-09-21')
    assert effective_skills(p, [first, second], dataset[2]) == effective_skills(p, [first], dataset[2])
    first['date'] = '2026-08-01'
    assert effective_skills(p, [first, second], dataset[2]) == p['skills']


def test_original_completed_history_has_no_semantic_duplicates(dataset):
    keys = [completion_identity(r, dataset[2]) for r in dataset[1] if r['status'] == 'completed']
    assert len(keys) == len(set(keys))
