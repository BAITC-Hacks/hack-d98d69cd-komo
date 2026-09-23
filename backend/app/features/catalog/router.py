from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.features.catalog.service import load_catalog
from app.features.employees.schemas import RoleOption
from app.features.identity.models import User
from app.features.identity.service import current_user

router = APIRouter(prefix='/catalog', tags=['catalog'])


@router.get('/role-profiles', response_model=list[RoleOption])
async def roles(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    catalog = await load_catalog(db)
    return [RoleOption(**r, skill_names={k: catalog.skills[k]['name'] for k in r['required_skills']}) for r in catalog.roles.values()]
