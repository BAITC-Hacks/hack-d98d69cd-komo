from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.features.identity.models import User
from app.features.identity.service import current_user, require_employee_access
from app.features.employees.service import get_employee
from app.features.recommendations.service import recommend, latest
from app.features.recommendations.schemas import RecommendationResult, RecommendationState

router = APIRouter(prefix='/employees', tags=['recommendations'])


@router.get('/{employee_id}/recommendations', response_model=RecommendationState)
async def last_recommendation(employee_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    require_employee_access(user, employee_id)
    await get_employee(db, employee_id)
    return await latest(db, employee_id)


@router.post('/{employee_id}/recommendations', response_model=RecommendationResult)
async def generate_recommendation(employee_id: str, refresh: bool = False, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    require_employee_access(user, employee_id)
    return await recommend(db, employee_id, refresh=refresh)
