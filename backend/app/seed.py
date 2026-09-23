import asyncio
import csv
import json
import secrets
from datetime import date
from pathlib import Path
from argon2 import PasswordHasher
from sqlalchemy import select, text
from app.core.config import settings
from app.core.db import Session, engine
from app.core.state import DatasetState
from app.features.catalog.models import Skill, RoleProfile, Event
from app.features.employees.models import Employee
from app.features.identity.models import User
from app.features.development.models import ActivityRecord
from app.features.development.schemas import HistoryInput
from app.features.employees.schemas import EmployeeProfile


async def ensure_demo_users(db, config):
    from argon2.exceptions import VerificationError
    if await db.get(Employee, config.employee_id) is None:
        raise RuntimeError('EMPLOYEE_ID does not reference a loaded employee')
    hasher = PasswordHasher()
    for username, role, employee_id, password in [('employee', 'employee', config.employee_id, config.employee_password), ('hr', 'hr', None, config.hr_password)]:
        user = await db.get(User, username)
        if user:
            user.employee_id = employee_id
            try:
                hasher.verify(user.password_hash, password)
            except VerificationError:
                user.password_hash = hasher.hash(password)
        else:
            db.add(User(username=username, role=role, employee_id=employee_id, password_hash=hasher.hash(password)))


async def seed():
    config = settings()
    root = Path(config.dataset_path)
    async with Session() as db:
        await db.execute(text('SELECT pg_advisory_xact_lock(817241)'))
        if await db.get(DatasetState, 1):
            await ensure_demo_users(db, config)
            await db.commit()
            print('Dataset already initialized; existing data preserved.')
            return
        employees = json.loads((root / 'employees.json').read_text())
        skills = json.loads((root / 'skills.json').read_text())
        events = json.loads((root / 'events.json').read_text())
        db.add(DatasetState(id=1, as_of_date=date.fromisoformat(employees['meta']['as_of_date']), revision=1, session_secret=config.session_secret or secrets.token_urlsafe(48)))
        db.add_all([Skill(skill_id=s['skill_id'], data=s) for s in skills['skills']])
        db.add_all([RoleProfile(role=r['role'], grade=r['grade'], data=r) for r in skills['role_profiles']])
        db.add_all([Event(event_id=e['event_id'], data=e) for e in events['events']])
        for e in employees['employees']:
            db.add(Employee(employee_id=e['employee_id'], data=EmployeeProfile.model_validate(e).model_dump(mode='json')))
        await db.flush()
        with (root / 'activity_history.csv').open() as handle:
            for raw in csv.DictReader(handle):
                raw = {k: None if v == '' and k in ('due_date', 'score', 'feedback_rating') else v for k, v in raw.items()}
                r = HistoryInput.model_validate(raw).model_dump(mode='json')
                db.add(ActivityRecord(record_id=r['record_id'], employee_id=r['employee_id'], event_id=r['event_id'], date=date.fromisoformat(r['date']), status=r['status'], data=r))
        await ensure_demo_users(db, config)
        await db.commit()
        print('Loaded 200 synthetic employees, 40 events, 60 skills and 2743 activity records.')
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(seed())
