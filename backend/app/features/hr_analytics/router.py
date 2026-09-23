from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.features.identity.models import User
from app.features.identity.service import hr_user
from app.features.hr_analytics.service import overview
from app.features.hr_analytics.schemas import HROverview

router = APIRouter(prefix='/hr', tags=['hr_analytics'])


@router.get('/overview', response_model=HROverview)
async def hr_overview(include_test: bool = False, user: User = Depends(hr_user), db: AsyncSession = Depends(get_db)):
    return await overview(db, include_test=include_test)
