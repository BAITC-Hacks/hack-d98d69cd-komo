import json
from app.qa_demo import prepare
from conftest import login


async def test_qa_import_does_not_change_normal_hr_population(client):
    await login(client, 'hr')
    before = (await client.get('/api/v1/hr/overview')).json()
    people_before = (await client.get('/api/v1/employees')).json()
    assert people_before and all(not e['is_test'] and not e['employee_id'].startswith('QA_') for e in people_before)
    data = prepare()
    result = await client.post('/api/v1/hr/import', files={'employees': ('e.json', json.dumps(data['bundle'])), 'history': ('h.csv', data['history_csv'])})
    assert result.status_code == 200, result.text
    after = (await client.get('/api/v1/hr/overview')).json()
    for key in ['total_employees', 'total_participations', 'average_progress', 'completion_rate', 'participation', 'skill_gaps', 'employees_without_step']:
        assert before[key] == after[key], key
    assert after['excluded_test_employees'] == before['excluded_test_employees'] + 4
    eid = data['employee_id']
    assert (await client.get('/api/v1/employees', params={'q': eid})).json() == []
    visible = (await client.get('/api/v1/employees', params={'q': eid, 'include_test': True})).json()
    assert len(visible) == 1 and visible[0]['is_test']
    assert (await client.get(f'/api/v1/employees/{eid}')).json()['is_test']
    included = (await client.get('/api/v1/hr/overview?include_test=true')).json()
    assert included['includes_test_data'] and included['excluded_test_employees'] == 0
    assert included['total_employees'] == after['total_employees'] + after['excluded_test_employees']
    assert sum(p['total'] for p in included['participation']) == included['total_participations']
    assert (await client.post(f'/api/v1/employees/{eid}/recommendations?refresh=true')).json()['source'] == 'ai'
    included = (await client.get('/api/v1/hr/overview?include_test=true')).json()
    assert eid not in [e['employee_id'] for e in included['employees_without_step']]


async def test_employee_cannot_enable_hr_test_view(client):
    await login(client)
    assert (await client.get('/api/v1/hr/overview?include_test=true')).status_code == 403
    assert (await client.get('/api/v1/employees?include_test=true')).status_code == 403
