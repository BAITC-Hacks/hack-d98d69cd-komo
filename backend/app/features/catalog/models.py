from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Skill(Base):
    __tablename__ = 'skills'
    skill_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)


class RoleProfile(Base):
    __tablename__ = 'role_profiles'
    role: Mapped[str] = mapped_column(String(100), primary_key=True)
    grade: Mapped[str] = mapped_column(String(20), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)


class Event(Base):
    __tablename__ = 'events'
    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)
