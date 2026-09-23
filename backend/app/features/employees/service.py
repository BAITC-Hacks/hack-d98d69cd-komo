from sqlalchemy.ext.asyncio import AsyncSession
from app.features.employees.models import Employee
from app.core.errors import AppError


async def get_employee(db: AsyncSession, employee_id: str) -> dict:
    employee = await db.get(Employee, employee_id)
    if employee is None:
        raise AppError('employee_not_found', 'Сотрудник не найден', 404)
    return employee.data
