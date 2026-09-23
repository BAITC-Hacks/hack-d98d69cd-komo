from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.features.identity.models import User
from app.features.identity.service import current_user, hr_user, require_employee_access
from app.features.employees.models import Employee
from app.features.employees.schemas import EmployeeProfile, GoalInput
from app.features.employees.service import get_employee, effective_profile
from app.features.development.service import context_for, complete, start, cancel, change_goal
from app.features.development.schemas import Development, HistoryView, CompletionInput, CompletionResult, ParticipationResult

router = APIRouter(prefix='/employees', tags=['employees'])


@router.get('', response_model=list[EmployeeProfile])
async def employees(q: str = Query('', max_length=100), user: User = Depends(hr_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Employee).order_by(Employee.employee_id))).all()
    needle = q.casefold()
    return [effective_profile(r) for r in rows if not needle or any(needle in str(r.data[k]).casefold() for k in ('employee_id', 'full_name', 'department', 'role'))]


@router.get('/{employee_id}', response_model=EmployeeProfile)
async def employee(employee_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    require_employee_access(user, employee_id)
    return await get_employee(db, employee_id)


@router.get('/{employee_id}/development', response_model=Development)
async def development(employee_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    require_employee_access(user, employee_id)
    return (await context_for(db, employee_id))[3]


@router.get('/{employee_id}/history', response_model=list[HistoryView])
async def history(employee_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    require_employee_access(user, employee_id)
    _, records, catalog, _ = await context_for(db, employee_id)
    return [HistoryView(**{k: r[k] for k in ('record_id', 'event_id', 'date', 'status', 'completion_pct', 'score', 'feedback_rating')},
                        title=catalog.events[r['event_id']]['title']) for r in reversed(records)]


@router.post('/{employee_id}/activities/{event_id}/complete', response_model=CompletionResult)
async def completion(employee_id: str, event_id: str, body: CompletionInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    require_employee_access(user, employee_id, write=True)
    return await complete(db, employee_id, event_id, body)


@router.patch('/{employee_id}/career-goal', response_model=Development)
async def goal(employee_id: str, body: GoalInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    require_employee_access(user, employee_id, write=True)
    return await change_goal(db, employee_id, body)


@router.post('/{employee_id}/activities/{event_id}/start', response_model=ParticipationResult)
async def begin(employee_id: str, event_id: str, body: CompletionInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    require_employee_access(user, employee_id, write=True)
    return await start(db, employee_id, event_id, body)


@router.post('/{employee_id}/participations/{record_id}/cancel', response_model=ParticipationResult)
async def cancel_participation(employee_id: str, record_id: str, body: CompletionInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    require_employee_access(user, employee_id, write=True)
    return await cancel(db, employee_id, record_id, body)
