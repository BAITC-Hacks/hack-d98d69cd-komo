import json
import csv
from pathlib import Path
import pytest
import pytest_asyncio
import httpx
from app.core.config import settings
from app.features.catalog.service import Catalog


@pytest.fixture
def dataset():
    root = Path(settings().dataset_path)
    employees = json.loads((root / 'employees.json').read_text())['employees']
    skills = json.loads((root / 'skills.json').read_text())
    events = json.loads((root / 'events.json').read_text())['events']
    with (root / 'activity_history.csv').open() as file:
        records = list(csv.DictReader(file))
    catalog = Catalog({s['skill_id']: s for s in skills['skills']}, {(r['role'], r['grade']): r for r in skills['role_profiles']}, {e['event_id']: e for e in events})
    return employees, records, catalog


@pytest_asyncio.fixture
async def client(monkeypatch):
    from app.main import app
    from app.core.db import Session
    from app.core.state import get_state
    from app.features.recommendations import service
    from app.features.recommendations.schemas import ModelPlan, ModelSelection
    async def stub(payload):
        return ModelPlan(selections=[ModelSelection(event_id=c['event_id'], factors=['grade', 'skill_gap', 'history'], rationale='Тестовая фикстура провайдера') for c in payload['candidates'][:3]])
    monkeypatch.setattr(service, 'select_with_ai', stub)
    async with Session() as db:
        app.state.session_secret = (await get_state(db)).session_secret
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', timeout=15) as client:
        yield client


async def login(client, role='employee'):
    password = settings().employee_password if role == 'employee' else settings().hr_password
    response = await client.post('/api/v1/auth/login', json={'username': role, 'password': password})
    assert response.status_code == 200, response.text
