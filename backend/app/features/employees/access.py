"""HR provisions a local login; import never resets existing credentials."""
from hashlib import sha256
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError
from app.core.state import get_state
from app.features.identity.models import User
from app.features.employees.service import get_employee


async def employee_access(db: AsyncSession, employee_id: str):
    await get_employee(db, employee_id)
    user = await db.scalar(select(User).where(User.employee_id == employee_id, User.role == 'employee'))
    return {'username': user.username if user else None}


async def create_access(db: AsyncSession, employee_id: str, password: str):
    await get_state(db, lock=True)
    current = await employee_access(db, employee_id)
    if current['username']:
        raise AppError('account_exists', 'У сотрудника уже есть доступ. Пароль не изменен.', 409, current)
    username = employee_id
    if await db.get(User, username):
        username = 'staff_' + sha256(employee_id.encode()).hexdigest()[:24]
    if await db.get(User, username):
        raise AppError('username_conflict', 'Не удалось назначить свободный логин', 409)
    db.add(User(username=username, password_hash=PasswordHasher().hash(password), role='employee', employee_id=employee_id))
    await db.commit()
    return {'username': username}
