from datetime import date
from sqlalchemy import Integer, String, Date, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import Base


class DatasetState(Base):
    __tablename__ = 'dataset_state'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of_date: Mapped[date] = mapped_column(Date)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    session_secret: Mapped[str] = mapped_column(String(128))


async def get_state(db: AsyncSession, lock: bool = False) -> DatasetState:
    statement = select(DatasetState).where(DatasetState.id == 1).execution_options(populate_existing=True)
    if lock:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one()
