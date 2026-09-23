from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.catalog.models import Event, Skill, RoleProfile


@dataclass
class Catalog:
    skills: dict[str, dict]
    roles: dict[tuple[str, str], dict]
    events: dict[str, dict]


async def load_catalog(db: AsyncSession) -> Catalog:
    skills = (await db.scalars(select(Skill))).all()
    roles = (await db.scalars(select(RoleProfile))).all()
    events = (await db.scalars(select(Event))).all()
    return Catalog({x.skill_id: x.data for x in skills}, {(x.role, x.grade): x.data for x in roles}, {x.event_id: x.data for x in events})
