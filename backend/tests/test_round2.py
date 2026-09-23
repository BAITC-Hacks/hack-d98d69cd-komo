import asyncio
import json
from copy import deepcopy
from uuid import uuid4
import pytest
from app.qa_demo import prepare, account, PASSWORD
from app.features.recommendations.schemas import ModelPlan, ModelSelection, Evidence
from app.features.recommendations.service import validate_plan
from conftest import login


@pytest.fixture
async def participant(client):
    data = prepare()
    await login(client, 'hr')
    files = {'employees': ('employees.json', json.dumps(data['bundle'])), 'history': ('history.csv', data['history_csv'])}
    r = await client.post('/api/v1/hr/import', files=files)
    assert r.status_code == 200, r.text
    await account(data['employee_id'])
    assert (await client.post('/api/v1/auth/login', json={'username': data['employee_id'], 'password': PASSWORD})).status_code == 200
    return data


def key(**kw):
    return dict(idempotency_key=str(uuid4()), **kw)


async def test_goal_permissions_auto_and_import_preservation(client, participant):
    eid = participant['employee_id']; path = f'/api/v1/employees/{eid}'
    before = (await client.get(path + '/development')).json()
    roles = await client.get('/api/v1/catalog/role-profiles')
    assert roles.status_code == 200 and len(roles.json()) == 32
    body = {'career_goal': {'target_role': 'Product Manager', 'target_grade': 'Middle'}}
    changed = await client.patch(path + '/career-goal', json=body)
    assert changed.status_code == 200, changed.text
    result = changed.json()
    assert result['goal']['source'] == 'manual' and result['goal']['role'] == 'Product Manager'
    assert {s['skill_id']: s['current'] for s in before['skills']} == {s['skill_id']: s['current'] for s in result['skills'] if s['skill_id'] in {v['skill_id'] for v in before['skills']}}
    again = await client.patch(path + '/career-goal', json=body)
    assert again.json()['revision'] == result['revision']
    assert (await client.patch(path + '/career-goal', json={'career_goal': {'target_role': 'Unknown', 'target_grade': 'Lead'}})).status_code == 422
    assert (await client.patch('/api/v1/employees/E0001/career-goal', json=body)).status_code == 403
    await login(client, 'hr')
    assert (await client.patch(path + '/career-goal', json=body)).status_code == 403
    assert (await client.post('/api/v1/hr/import', files={'employees': ('e.json', json.dumps(participant['bundle']))})).status_code == 200
    assert (await client.get(path)).json()['career_goal'] == body['career_goal']
    await client.post('/api/v1/auth/login', json={'username': eid, 'password': PASSWORD})
    auto = (await client.patch(path + '/career-goal', json={'career_goal': None})).json()
    assert auto['goal']['source'] == 'automatic' and auto['goal']['grade'] == 'Senior'
    assert auto['goal']['role'] == 'Backend Engineer'


async def test_start_complete_after_goal_change_and_concurrent_retry(client, participant):
    path = '/api/v1/employees/' + participant['employee_id']
    before = (await client.get(path + '/development')).json()
    body = key()
    a, b = await asyncio.gather(client.post(path + '/activities/EV_009/start', json=body), client.post(path + '/activities/EV_009/start', json=body))
    assert a.status_code == b.status_code == 200, a.text
    assert a.json() == b.json()
    started = a.json()
    assert started['development']['progress'] == before['progress']
    assert started['status'] == 'in_progress'
    other_key = (await client.post(path + '/activities/EV_009/start', json=key())).json()
    assert other_key['record_id'] == started['record_id']
    # A goal already satisfied must not strand an existing participation.
    target = {'career_goal': {'target_role': 'Backend Engineer', 'target_grade': 'Junior'}}
    changed = (await client.patch(path + '/career-goal', json=target)).json()
    assert any(p['record_id'] == started['record_id'] for p in changed['participations'])
    await client.post(path + '/recommendations')
    complete_body = key(record_id=started['record_id'])
    first, repeated = await asyncio.gather(client.post(path + '/activities/EV_009/complete', json=complete_body), client.post(path + '/activities/EV_009/complete', json=complete_body))
    assert first.status_code == repeated.status_code == 200, first.text
    assert first.json() == repeated.json()
    assert any(g['skill_id'] == 'SK_CLOUD' and g['after'] > g['before'] for g in first.json()['gains'])
    assert (await client.get(path + '/recommendations')).json()['status'] == 'stale'
    assert (await client.post(path + '/activities/EV_009/complete', json=key(record_id=started['record_id']))).status_code == 409
    assert (await client.post(path + '/activities/EV_009/complete', json=body)).status_code == 409
    assert sum(h['record_id'] == started['record_id'] for h in (await client.get(path + '/history')).json()) == 1


async def test_plan_cancel_session_and_local_import_protection(client, participant):
    eid = participant['employee_id']; path = '/api/v1/employees/' + eid
    before = (await client.get(path + '/development')).json()
    option = next(e for e in before['available_events'] if e['format'] != 'self_paced')
    endpoint = path + '/activities/' + option['event_id']
    planned = await client.post(endpoint + '/start', json=key(session_date=option['sessions'][0]))
    assert planned.status_code == 200, planned.text
    result = planned.json(); rid = result['record_id']
    assert result['status'] == 'planned' and result['development']['progress'] == before['progress']
    assert (await client.post(endpoint + '/complete', json=key(record_id=rid))).status_code == 409
    await login(client, 'hr')
    assert (await client.post(endpoint + '/start', json=key())).status_code == 403
    assert (await client.post(path + f'/participations/{rid}/cancel', json=key())).status_code == 403
    overview = (await client.get('/api/v1/hr/overview')).json()
    assert all(e['total'] == sum(e[k] for k in ['completed', 'missed', 'in_progress', 'overdue', 'planned', 'cancelled']) for e in overview['participation'])
    # Imported history cannot overwrite a local planned record even with valid source-schema fields.
    csv = 'record_id,employee_id,event_id,date,due_date,status,completion_pct,score,feedback_rating,assigned_by\n' + f'{rid},{eid},{option["event_id"]},2026-09-29,,in_progress,0,,,self\n'
    assert (await client.post('/api/v1/hr/import', files={'history': ('h.csv', csv)})).status_code == 409
    await client.post('/api/v1/auth/login', json={'username': eid, 'password': PASSWORD})
    cancel_body = key()
    cancelled = await client.post(path + f'/participations/{rid}/cancel', json=cancel_body)
    assert cancelled.status_code == 200
    assert cancelled.json()['status'] == 'cancelled'
    assert cancelled.json() == (await client.post(path + f'/participations/{rid}/cancel', json=cancel_body)).json()
    assert not any(p['record_id'] == rid for p in cancelled.json()['development']['participations'])
    assert (await client.post(endpoint + '/complete', json=key(record_id=rid))).status_code == 409


async def test_refresh_bypasses_cache_and_selected_facts(client, participant, monkeypatch):
    from app.features.recommendations import service
    async def forbidden_cache(*a, **kw):
        raise AssertionError('refresh must not read cache')
    monkeypatch.setattr(service, 'cache_get', forbidden_cache)
    r = await client.post('/api/v1/employees/' + participant['employee_id'] + '/recommendations?refresh=true')
    assert r.status_code == 200, r.text
    assert not r.json()['cached'] and r.json()['source'] == 'ai'
    for step in r.json()['steps']:
        assert len({e['factor'] for e in step['evidence']}) >= 3
        assert all(e['fact_id'].startswith(step['activity']['event_id'] + ':') for e in step['evidence'])


def test_cross_event_facts_are_rejected():
    facts = [Evidence(fact_id='A:' + f, factor=f, text='test') for f in ['grade', 'skill_gap', 'history']]
    plan = ModelPlan(selections=[ModelSelection(event_id='A', fact_ids=['A:grade', 'A:skill_gap', 'B:history'])])
    with pytest.raises(ValueError): validate_plan(plan, {'A': facts})


@pytest.mark.parametrize('status', ['planned', 'cancelled'])
def test_new_statuses_do_not_award_skills(dataset, status):
    from app.features.development.logic import effective_skills
    e = dataset[0][0]
    assert effective_skills(e, [{'record_id': 'QA', 'event_id': 'EV_004', 'date': '2026-10-01', 'status': status}], dataset[2]) == e['skills']


async def test_unknown_model_facts_fall_back(client, participant, monkeypatch):
    from app.features.recommendations import service
    async def invalid(payload):
        return ModelPlan(selections=[ModelSelection(event_id=payload['candidates'][0]['event_id'], fact_ids=['invented'])])
    monkeypatch.setattr(service, 'select_with_ai', invalid)
    r = await client.post('/api/v1/employees/' + participant['employee_id'] + '/recommendations?refresh=true')
    assert r.status_code == 200 and r.json()['source'] == 'fallback'
    assert r.json()['steps'] and 'ai сейчас недоступен' in r.json()['message'].lower()


def test_repeat_club_uses_different_session(dataset):
    from app.features.development.logic import calculate_development
    employee = deepcopy(dataset[0][0]); catalog = deepcopy(dataset[2])
    employee['last_review_date'] = '2026-09-30'
    employee['career_goal'] = {'target_role': 'Backend Engineer', 'target_grade': 'Senior'}
    employee['skills']['SK_PUBLIC_SPEAKING'] = 0
    catalog.events['EV_036']['upcoming_sessions'] = ['2026-10-01', '2026-10-08']
    history = [{'record_id': 'QA_R2_SESSION_A', 'event_id': 'EV_036', 'date': '2026-10-01', 'status': 'completed'}]
    development = calculate_development(employee, history, catalog, '2026-10-01', 1)
    club = next(e for e in development.available_events if e.event_id == 'EV_036')
    assert club.sessions == ['2026-10-08'] and not club.can_complete


async def test_explicit_origin_allowlist(client):
    from app.core.config import settings
    for origin in settings().allowed_origins:
        assert (await client.post('/api/v1/auth/login', headers={'Origin': origin}, json={'username': 'no-user', 'password': 'wrong'})).status_code == 401
    assert (await client.post('/api/v1/auth/login', headers={'Origin': 'https://unknown.invalid'}, json={'username': 'no-user', 'password': 'wrong'})).status_code == 403


def test_future_selected_session_not_completable_when_another_is_today(dataset):
    from app.features.development.logic import calculate_development
    employee = deepcopy(dataset[0][0]); catalog = deepcopy(dataset[2])
    employee['skills']['SK_PUBLIC_SPEAKING'] = 0
    catalog.events['EV_036']['upcoming_sessions'] = ['2026-10-01', '2026-10-08']
    history = [{'record_id': 'QA_R2_FUTURE', 'event_id': 'EV_036', 'date': '2026-10-08', 'status': 'planned', 'origin': 'local'}]
    development = calculate_development(employee, history, catalog, '2026-10-01', 1)
    club = next(e for e in development.participations if e.event_id == 'EV_036')
    assert club.next_session == '2026-10-08' and not club.can_complete
