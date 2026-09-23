from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Employee(Base):
    __tablename__ = 'employees'
    employee_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)
    goal_mode: Mapped[str] = mapped_column(String(20), default='profile', server_default='profile')
    goal_override: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
