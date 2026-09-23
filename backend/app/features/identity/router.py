from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.db import get_db
from app.core.errors import AppError
from app.features.identity.models import User
from app.features.identity.schemas import LoginInput, Identity
from app.features.identity.service import current_user, signer

router = APIRouter(prefix='/auth', tags=['identity'])
hasher = PasswordHasher()


@router.post('/login', response_model=Identity)
async def login(body: LoginInput, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, body.username)
    try:
        valid = bool(user) and hasher.verify(user.password_hash, body.password)
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid:
        raise AppError('invalid_credentials', 'Неверный логин или пароль', 401)
    response.set_cookie('cq_session', signer(request).dumps({'sub': user.username}), max_age=43200,
                        httponly=True, secure=settings().app_origin.startswith('https://'), samesite='strict')
    return Identity(username=user.username, role=user.role, employee_id=user.employee_id)


@router.get('/me', response_model=Identity)
async def me(user: User = Depends(current_user)):
    return Identity(username=user.username, role=user.role, employee_id=user.employee_id)


@router.post('/logout')
async def logout(response: Response):
    response.delete_cookie('cq_session')
    return {'ok': True}
