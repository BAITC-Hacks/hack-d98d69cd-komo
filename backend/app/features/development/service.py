from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError
from app.core.state import get_state
from app.features.catalog.service import load_catalog
from app.features.employees.service import get_employee
from app.features.development.logic import calculate_development, effective_skills, event_gains
from app.features.development.models import ActivityRecord, CompletionReceipt
from app.features.development.schemas import CompletionInput, CompletionResult


async def load_history(db: AsyncSession, employee_id: str) -> list[dict]:
    rows = await db.scalars(select(ActivityRecord).where(ActivityRecord.employee_id == employee_id).order_by(ActivityRecord.date, ActivityRecord.record_id))
    return [r.data for r in rows]


async def context_for(db: AsyncSession, employee_id: str):
    state = await get_state(db)
    employee = await get_employee(db, employee_id)
    catalog = await load_catalog(db)
    history = await load_history(db, employee_id)
    development = calculate_development(employee, history, catalog, state.as_of_date.isoformat(), state.revision)
    return employee, history, catalog, development


async def complete(db: AsyncSession, employee_id: str, event_id: str, body: CompletionInput) -> CompletionResult:
    # All data mutations acquire this small dataset lock in the same order.
    state = await get_state(db, lock=True)
    receipt = await db.get(CompletionReceipt, (employee_id, body.idempotency_key))
    if receipt:
        if receipt.event_id != event_id:
            raise AppError('idempotency_conflict', 'Этот ключ запроса уже использован для другой активности', 409)
        return CompletionResult.model_validate(receipt.response)
    employee, history, catalog, before = await context_for(db, employee_id)
    option = next((e for e in before.available_events if e.event_id == event_id), None)
    if option is None:
        raise AppError('activity_unavailable', 'Активность недоступна или уже завершена', 409)
    if not option.can_complete:
        raise AppError('future_session', 'Сессия еще не состоялась. Выберите доступную самостоятельную активность.', 409)
    record_id = body.record_id or option.record_id
    record = await db.get(ActivityRecord, record_id) if record_id else None
    if record_id and (not record or record.employee_id != employee_id or record.event_id != event_id or record.status != 'in_progress'):
        raise AppError('invalid_participation', 'Участие не соответствует сотруднику и активности', 409)
    today = state.as_of_date.isoformat()
    if body.session_date and body.session_date > state.as_of_date:
        raise AppError('future_session', 'Нельзя завершить будущую сессию', 409)
    if not record and catalog.events[event_id]['format'] != 'self_paced':
        session_date = body.session_date.isoformat() if body.session_date else today
        if session_date not in catalog.events[event_id]['upcoming_sessions']:
            raise AppError('invalid_session', 'Дата не соответствует сессии активности', 422)
        if any(r['event_id'] == event_id and r['date'] == session_date and r['status'] == 'completed' for r in history):
            raise AppError('already_completed', 'Эта сессия уже завершена', 409)
    else:
        session_date = today
    record_id = record.record_id if record else 'APP_' + uuid4().hex
    data = dict(record.data) if record else {'record_id': record_id, 'employee_id': employee_id, 'event_id': event_id,
                                             'date': session_date, 'due_date': None, 'score': None, 'feedback_rating': None, 'assigned_by': 'self'}
    data.update(status='completed', completion_pct=100, effective_date=today, completed_at=datetime.now(timezone.utc).isoformat())
    if record:
        record.data, record.status = data, 'completed'
    else:
        from datetime import date
        db.add(ActivityRecord(record_id=record_id, employee_id=employee_id, event_id=event_id, date=date.fromisoformat(session_date), status='completed', data=data))
    state.revision += 1
    await db.flush()
    after_history = await load_history(db, employee_id)
    after = calculate_development(employee, after_history, catalog, today, state.revision)
    gains = event_gains(catalog.events[event_id], effective_skills(employee, history, catalog),
                       catalog.roles[(before.goal.role, before.goal.grade)]['required_skills'], catalog)
    result = CompletionResult(record_id=record_id, gains=gains, before_progress=before.progress, development=after)
    db.add(CompletionReceipt(employee_id=employee_id, idempotency_key=body.idempotency_key, event_id=event_id, response=result.model_dump(mode='json')))
    await db.commit()
    return result
