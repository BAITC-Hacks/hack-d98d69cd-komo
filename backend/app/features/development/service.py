from datetime import date, datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError
from app.core.state import get_state
from app.features.catalog.service import load_catalog
from app.features.employees.models import Employee
from app.features.employees.service import get_employee
from app.features.development.logic import calculate_development, effective_skills, event_gains
from app.features.development.models import ActivityRecord, CompletionReceipt
from app.features.development.schemas import CompletionInput, CompletionResult, ParticipationResult


async def load_history(db: AsyncSession, employee_id: str) -> list[dict]:
    rows = await db.scalars(select(ActivityRecord).where(ActivityRecord.employee_id == employee_id).order_by(ActivityRecord.date, ActivityRecord.record_id))
    return [r.data for r in rows]


async def context_for(db: AsyncSession, employee_id: str):
    state = await get_state(db)
    employee = await get_employee(db, employee_id)
    catalog = await load_catalog(db)
    history = await load_history(db, employee_id)
    development = calculate_development(employee, history, catalog, state.as_of_date.isoformat(), state.revision)
    row = await db.get(Employee, employee_id)
    development.goal.source = row.goal_mode if row.goal_mode != 'profile' else ('automatic' if development.goal.inferred else 'profile')
    return employee, history, catalog, development


async def change_goal(db, employee_id, body):
    state = await get_state(db, lock=True)
    await get_employee(db, employee_id)
    catalog = await load_catalog(db)
    goal = body.career_goal
    if goal and (goal.target_role, goal.target_grade) not in catalog.roles:
        raise AppError('invalid_goal', 'Выберите существующую роль и грейд из каталога', 422)
    row = await db.get(Employee, employee_id)
    mode, value = ('manual', goal.model_dump()) if goal else ('automatic', None)
    if row.goal_mode != mode or row.goal_override != value:
        row.goal_mode, row.goal_override = mode, value
        state.revision += 1
    await db.flush()
    result = (await context_for(db, employee_id))[3]
    await db.commit()
    return result


async def existing_receipt(db, employee_id, event_id, action, body):
    receipt = await db.get(CompletionReceipt, (employee_id, body.idempotency_key))
    if receipt:
        if receipt.event_id != event_id or receipt.action != action or (receipt.request_data is not None and receipt.request_data != body.model_dump(mode='json')):
            raise AppError('idempotency_conflict', 'Ключ запроса уже использован для другого действия или участия', 409)
        return receipt.response
    return None


def add_receipt(db, employee_id, event_id, action, body, result):
    db.add(CompletionReceipt(employee_id=employee_id, idempotency_key=body.idempotency_key, event_id=event_id,
                            action=action, request_data=body.model_dump(mode='json'), response=result.model_dump(mode='json')))


async def start(db, employee_id, event_id, body: CompletionInput) -> ParticipationResult:
    state = await get_state(db, lock=True)
    cached = await existing_receipt(db, employee_id, event_id, 'start', body)
    if cached:
        return ParticipationResult.model_validate(cached)
    _, history, catalog, development = await context_for(db, employee_id)
    option = next((e for e in development.available_events if e.event_id == event_id), None)
    active = next((r for r in history if r['event_id'] == event_id and r['status'] in ('in_progress', 'planned')), None)
    if active:
        if body.session_date and active['date'] != body.session_date.isoformat():
            raise AppError('participation_exists', 'Сначала отмените текущее участие, чтобы выбрать другую сессию', 409)
        result = ParticipationResult(record_id=active['record_id'], status=active['status'], development=development)
    else:
        if not option:
            raise AppError('activity_unavailable', 'Активность недоступна или уже завершена', 409)
        today = state.as_of_date.isoformat()
        if option.format == 'self_paced':
            if body.session_date:
                raise AppError('invalid_session', 'Самостоятельный курс не требует даты сессии', 422)
            session_date, status = today, 'in_progress'
        else:
            session_date = body.session_date.isoformat() if body.session_date else option.next_session
            if session_date not in option.sessions:
                raise AppError('invalid_session', 'Выберите доступную сессию из каталога', 422)
            status = 'planned' if session_date > today else 'in_progress'
        record_id = 'APP_' + uuid4().hex
        data = dict(record_id=record_id, employee_id=employee_id, event_id=event_id, date=session_date, due_date=None,
                    status=status, completion_pct=0, score=None, feedback_rating=None, assigned_by='self', origin='local')
        db.add(ActivityRecord(record_id=record_id, employee_id=employee_id, event_id=event_id, date=date.fromisoformat(session_date), status=status, data=data))
        state.revision += 1
        await db.flush()
        result = ParticipationResult(record_id=record_id, status=status, development=(await context_for(db, employee_id))[3])
    add_receipt(db, employee_id, event_id, 'start', body, result)
    await db.commit()
    return result


async def cancel(db, employee_id, record_id, body: CompletionInput) -> ParticipationResult:
    state = await get_state(db, lock=True)
    record = await db.get(ActivityRecord, record_id)
    if not record or record.employee_id != employee_id:
        raise AppError('participation_not_found', 'Участие не найдено', 404)
    body = body.model_copy(update={'record_id': record_id})
    cached = await existing_receipt(db, employee_id, record.event_id, 'cancel', body)
    if cached:
        return ParticipationResult.model_validate(cached)
    if record.data.get('origin') != 'local' or record.status not in ('planned', 'in_progress', 'cancelled'):
        raise AppError('cannot_cancel', 'Можно отменить только свое незавершенное локальное участие', 409)
    if record.status != 'cancelled':
        record.status = 'cancelled'
        record.data = dict(record.data, status='cancelled')
        state.revision += 1
    await db.flush()
    result = ParticipationResult(record_id=record_id, status='cancelled', development=(await context_for(db, employee_id))[3])
    add_receipt(db, employee_id, record.event_id, 'cancel', body, result)
    await db.commit()
    return result


async def complete(db: AsyncSession, employee_id: str, event_id: str, body: CompletionInput) -> CompletionResult:
    state = await get_state(db, lock=True)
    cached = await existing_receipt(db, employee_id, event_id, 'complete', body)
    if cached:
        return CompletionResult.model_validate(cached)
    employee, history, catalog, before = await context_for(db, employee_id)
    # Existing participation is independent of the current recommendation/goal.
    option = next((e for e in before.participations if e.event_id == event_id and (not body.record_id or e.record_id == body.record_id)), None)
    option = option or next((e for e in before.available_events if e.event_id == event_id), None)
    if option is None:
        raise AppError('activity_unavailable', 'Активность недоступна или уже завершена', 409)
    if not option.can_complete:
        raise AppError('future_session', 'Сессия еще не состоялась. Завершение пока недоступно.', 409)
    record_id = body.record_id or option.record_id
    record = await db.get(ActivityRecord, record_id) if record_id else None
    if record_id and (not record or record.employee_id != employee_id or record.event_id != event_id or record.status not in ('in_progress', 'planned')):
        raise AppError('invalid_participation', 'Участие не соответствует сотруднику и активности', 409)
    if any(r['event_id'] == event_id and r['status'] == 'completed' for r in history) and event_id != 'EV_036':
        raise AppError('already_completed', 'Активность уже завершена', 409)
    today = state.as_of_date.isoformat()
    if body.session_date and body.session_date > state.as_of_date:
        raise AppError('future_session', 'Нельзя завершить будущую сессию', 409)
    if record and record.date > state.as_of_date:
        raise AppError('future_session', 'Нельзя завершить будущую сессию', 409)
    if record and body.session_date and body.session_date != record.date:
        raise AppError('invalid_session', 'Дата не соответствует выбранному участию', 422)
    session_date = record.date.isoformat() if record else (body.session_date.isoformat() if body.session_date else today)
    if catalog.events[event_id]['format'] != 'self_paced':
        if not record and session_date not in catalog.events[event_id]['upcoming_sessions']:
            raise AppError('invalid_session', 'Дата не соответствует сессии активности', 422)
        if any(r['event_id'] == event_id and r['date'] == session_date and r['status'] == 'completed' for r in history):
            raise AppError('already_completed', 'Эта сессия уже завершена', 409)
    record_id = record.record_id if record else 'APP_' + uuid4().hex
    data = dict(record.data) if record else dict(record_id=record_id, employee_id=employee_id, event_id=event_id,
                                               date=session_date, due_date=None, score=None, feedback_rating=None, assigned_by='self')
    data.update(status='completed', completion_pct=100, origin='local', effective_date=today, completed_at=datetime.now(timezone.utc).isoformat())
    if record:
        record.data, record.status = data, 'completed'
    else:
        db.add(ActivityRecord(record_id=record_id, employee_id=employee_id, event_id=event_id, date=date.fromisoformat(session_date), status='completed', data=data))
    state.revision += 1
    await db.flush()
    after = (await context_for(db, employee_id))[3]
    gains = event_gains(catalog.events[event_id], effective_skills(employee, history, catalog),
                       catalog.roles[(before.goal.role, before.goal.grade)]['required_skills'], catalog)
    result = CompletionResult(record_id=record_id, gains=gains, before_progress=before.progress, development=after)
    add_receipt(db, employee_id, event_id, 'complete', body, result)
    await db.commit()
    return result
