import pytest
from app.features.recommendations.service import validate_plan, model_payload
from app.features.recommendations.schemas import ModelPlan, ModelSelection, Evidence
from app.features.development.logic import calculate_development, rank_candidates


@pytest.mark.parametrize('ids', [[], ['unknown'], ['EV_005', 'EV_005'], ['a', 'b', 'c', 'd']])
def test_invalid_selections_rejected(ids):
    plan = ModelPlan(selections=[ModelSelection(event_id=i, fact_ids=[f'{i}:grade', f'{i}:skill_gap', f'{i}:history']) for i in ids])
    with pytest.raises(ValueError):
        validate_plan(plan, {k: [] for k in ['EV_005', 'a', 'b', 'c', 'd']})


def test_duplicate_factors_rejected():
    plan = ModelPlan(selections=[ModelSelection(event_id='EV_005', fact_ids=['EV_005:grade'] * 3)])
    with pytest.raises(ValueError):
        validate_plan(plan, {'EV_005': [Evidence(fact_id='EV_005:grade', factor='grade', text='Test')]})


def test_outbound_payload_excludes_employee_identity(dataset):
    employee, records, catalog = dataset[0][0], dataset[1], dataset[2]
    history = [r for r in records if r['employee_id'] == employee['employee_id']]
    development = calculate_development(employee, history, catalog, '2026-10-01', 1)
    payload = model_payload(employee, development, rank_candidates(development, history, catalog), history, catalog)
    import json
    encoded = json.dumps(payload)
    for forbidden in ['full_name', 'employee_id', 'manager_id', 'record_id', employee['full_name'], employee['employee_id']]:
        assert forbidden not in encoded


async def test_redis_connection_failure_is_optional(monkeypatch):
    from redis.exceptions import ConnectionError
    from app.core import cache as module
    async def failed(*args, **kwargs):
        raise ConnectionError('test offline')
    monkeypatch.setattr(module.cache, 'get', failed)
    monkeypatch.setattr(module.cache, 'set', failed)
    assert await module.cache_get('test') is None
    await module.cache_set('test', 'value')
