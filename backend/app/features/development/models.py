from datetime import date
from sqlalchemy import String, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class ActivityRecord(Base):
    __tablename__ = 'activity_records'
    record_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey('employees.employee_id'))
    event_id: Mapped[str] = mapped_column(ForeignKey('events.event_id'))
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    data: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (Index('ix_history_employee_date', 'employee_id', 'date'),)


class CompletionReceipt(Base):
    __tablename__ = 'completion_receipts'
    employee_id: Mapped[str] = mapped_column(ForeignKey('employees.employee_id'), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('events.event_id'))
    response: Mapped[dict] = mapped_column(JSONB)
