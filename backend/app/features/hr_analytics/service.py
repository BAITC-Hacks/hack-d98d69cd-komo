from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.state import get_state
from app.core.config import settings
from app.features.catalog.service import load_catalog
from app.features.employees.models import Employee
from app.features.employees.service import effective_profile
from app.features.development.models import ActivityRecord
from app.features.development.logic import calculate_development
from app.features.recommendations.models import RecommendationRun
from app.features.recommendations.service import PROMPT_VERSION
from app.features.hr_analytics.schemas import HROverview, GapCount, EmployeeStatus, EventParticipation


async def overview(db: AsyncSession) -> HROverview:
    state = await get_state(db)
    catalog = await load_catalog(db)
    employees = (await db.scalars(select(Employee).order_by(Employee.employee_id))).all()
    records = (await db.scalars(select(ActivityRecord).order_by(ActivityRecord.date, ActivityRecord.record_id))).all()
    runs = (await db.scalars(select(RecommendationRun).order_by(RecommendationRun.created_at))).all()
    latest = {r.employee_id: r for r in runs}
    histories = defaultdict(list)
    participations = defaultdict(list)
    for row in records:
        histories[row.employee_id].append(row.data)
        participations[row.event_id].append(row.data)
    gaps = defaultdict(lambda: [0, 0])
    without = []
    progress = []
    for row in employees:
        employee = effective_profile(row)
        development = calculate_development(employee, histories[row.employee_id], catalog, state.as_of_date.isoformat(), state.revision)
        progress.append(development.progress)
        for skill in development.skills:
            if skill.gap > 0:
                gaps[skill.skill_id][0] += 1
                gaps[skill.skill_id][1] += int(skill.critical)
        run = latest.get(row.employee_id)
        if not development.available_events:
            status = 'no_eligible_step'
        elif not run:
            status = 'not_generated'
        elif run.revision != state.revision or run.data['model'] != settings().openai_model or run.data['prompt_version'] != PROMPT_VERSION:
            status = 'stale'
        elif run.data['steps']:
            status = 'ready'
        else:
            status = 'not_generated'
        if status != 'ready':
            without.append(EmployeeStatus(**{k: employee[k] for k in ('employee_id', 'full_name', 'department', 'role', 'grade')}, progress=development.progress, status=status))
    participation = []
    for event_id, event in catalog.events.items():
        rows = participations[event_id]
        participation.append(EventParticipation(event_id=event_id, title=event['title'], total=len(rows), completed=sum(r['status'] == 'completed' for r in rows),
                                               missed=sum(r['status'] in ('no_show', 'declined', 'dropped') for r in rows), in_progress=sum(r['status'] == 'in_progress' for r in rows), overdue=sum(r['status'] == 'overdue' for r in rows), planned=sum(r['status'] == 'planned' for r in rows), cancelled=sum(r['status'] == 'cancelled' for r in rows)))
    return HROverview(as_of_date=state.as_of_date.isoformat(), revision=state.revision, total_employees=len(employees),
                      average_progress=round(sum(progress) / max(1, len(progress)), 1), total_participations=len(records),
                      completion_rate=round(100 * sum(r.status == 'completed' for r in records) / max(1, sum(r.status not in ('planned', 'cancelled') for r in records)), 1),
                      skill_gaps=sorted([GapCount(skill_id=k, name=catalog.skills[k]['name'], employees=v[0], critical_employees=v[1]) for k, v in gaps.items()], key=lambda x: (-x.employees, x.name)),
                      employees_without_step=without, participation=sorted(participation, key=lambda x: (-x.total, x.title)))
