import json
from copy import deepcopy
from uuid import uuid4
import pytest
from app.features.recommendations import service
from app.features.development.context import context_version
from conftest import login


async def upload(client, profiles):
    response = await client.post('/api/v1/hr/import', files={'employees': ('e.json', json.dumps(profiles))})
    assert response.status_code == 200, response.text


@pytest.fixture
async def pair(client, dataset):
    await login(client, 'hr')
    base = next(e for e in dataset[0] if e['employee_id'] == 'E0028')
    profiles = [deepcopy(base) for _ in range(2)]
    for index, e in enumerate(profiles):
        e['employee_id'] = 'QA_R3_CONTEXT_' + uuid4().hex[:8] + str(index)
    await upload(client, profiles)
    return profiles


async def test_employee_context_cache_survives_other_employee_and_noop_import(client, pair):
    a, b = pair
    path = '/api/v1/employees/' + b['employee_id']
    first = (await client.post(path + '/recommendations?refresh=true')).json()
    assert first['source'] == 'ai'
    a['full_name'] += ' updated'
    await upload(client, [a])
    latest = (await client.get(path + '/recommendations')).json()
    assert latest['status'] == 'ready'
    cached = (await client.post(path + '/recommendations')).json()
    assert cached['cached'] and cached['run_id'] == first['run_id']
    await upload(client, [b])
    assert (await client.get(path + '/recommendations')).json()['status'] == 'ready'
    b['skills']['SK_CLOUD'] = min(5, b['skills']['SK_CLOUD'] + 1)
    await upload(client, [b])
    assert (await client.get(path + '/recommendations')).json()['status'] == 'stale'
    changed = (await client.post(path + '/recommendations')).json()
    assert not changed['cached'] and changed['context_version'] != first['context_version']


@pytest.mark.parametrize('same_employee', [True, False])
async def test_context_change_during_model_call(client, pair, monkeypatch, same_employee):
    original = service.select_with_ai
    async def change_then_select(payload):
        employee = pair[0 if same_employee else 1]
        employee['full_name'] += ' changed during AI'
        await upload(client, [employee])
        return await original(payload)
    monkeypatch.setattr(service, 'select_with_ai', change_then_select)
    response = await client.post(f"/api/v1/employees/{pair[0]['employee_id']}/recommendations?refresh=true")
    assert response.status_code == (409 if same_employee else 200), response.text
    if same_employee: assert response.json()['code'] == 'stale_context'


def test_context_ignores_json_order_but_tracks_catalog_date_and_logic(dataset, monkeypatch):
    from app.features.development import context
    e, records, catalog = deepcopy(dataset)
    profile = e[0]; history = [r for r in records if r['employee_id'] == profile['employee_id']]
    first = context_version(profile, history, catalog, '2026-10-01')
    assert context_version(dict(reversed(list(profile.items()))), list(reversed(history)), catalog, '2026-10-01') == first
    assert context_version(profile, history, catalog, '2026-10-02') != first
    catalog.events['EV_009']['description'] += ' updated'
    assert context_version(profile, history, catalog, '2026-10-01') != first
    second = context_version(profile, history, catalog, '2026-10-01')
    monkeypatch.setattr(context, 'LOGIC_VERSION', 'new-version')
    assert context_version(profile, history, catalog, '2026-10-01') != second
