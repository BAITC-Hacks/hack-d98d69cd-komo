from sqlalchemy.ext.asyncio import AsyncSession
from app.features.employees.models import Employee
from app.core.errors import AppError


async def get_employee(db: AsyncSession, employee_id: str) -> dict:
    employee = await db.get(Employee, employee_id, populate_existing=True)
    if employee is None:
        raise AppError('employee_not_found', 'Сотрудник не найден', 404)
    return effective_profile(employee)


def effective_profile(employee: Employee) -> dict:
    data = dict(employee.data)
    if employee.goal_mode != 'profile':
        data['career_goal'] = employee.goal_override if employee.goal_mode == 'manual' else None
    return data
