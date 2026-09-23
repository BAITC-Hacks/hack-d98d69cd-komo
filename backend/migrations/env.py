import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.db import Base
from app.core.state import DatasetState
from app.features.catalog.models import Skill, RoleProfile, Event
from app.features.employees.models import Employee
from app.features.identity.models import User
from app.features.development.models import ActivityRecord, CompletionReceipt
from app.features.recommendations.models import RecommendationRun


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run():
    engine = create_async_engine(settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()


asyncio.run(run())
