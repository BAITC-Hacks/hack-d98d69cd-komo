from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.catalog.models import Event, Skill, RoleProfile
from app.features.catalog.labels import EVENT_LABELS, SKILL_LABELS


@dataclass
class Catalog:
    skills: dict[str, dict]
    roles: dict[tuple[str, str], dict]
    events: dict[str, dict]


async def load_catalog(db: AsyncSession) -> Catalog:
    skills = (await db.scalars(select(Skill))).all()
    roles = (await db.scalars(select(RoleProfile))).all()
    events = (await db.scalars(select(Event))).all()
    localized_events = {}
    for event in events:
        title, description = EVENT_LABELS.get(event.event_id, (event.data['title'], event.data['description']))
        localized_events[event.event_id] = event.data | {'title': title, 'description': description}
    return Catalog({x.skill_id: x.data | {'name': SKILL_LABELS.get(x.skill_id, x.data['name'])} for x in skills},
                   {(x.role, x.grade): x.data for x in roles}, localized_events)
