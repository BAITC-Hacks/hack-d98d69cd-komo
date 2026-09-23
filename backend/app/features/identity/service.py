from fastapi import Depends, Request
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.errors import AppError
from app.features.identity.models import User


def signer(request: Request) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(request.app.state.session_secret, salt='career-quest-session-v1')


async def current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    try:
        payload = signer(request).loads(request.cookies.get('cq_session', ''), max_age=43200)
        username = payload['sub']
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        raise AppError('unauthenticated', 'Войдите в аккаунт', 401)
    user = await db.get(User, username)
    if not user:
        raise AppError('unauthenticated', 'Учетная запись не найдена', 401)
    return user


async def hr_user(user: User = Depends(current_user)) -> User:
    if user.role != 'hr':
        raise AppError('forbidden', 'Доступно только HR', 403)
    return user


def require_employee_access(user: User, employee_id: str, write: bool = False) -> None:
    if user.employee_id == employee_id and user.role == 'employee':
        return
    if user.role == 'hr' and not write:
        return
    raise AppError('forbidden', 'Нет доступа к данным этого сотрудника', 403)
