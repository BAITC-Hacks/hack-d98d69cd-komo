from pydantic import BaseModel


class GapCount(BaseModel):
    skill_id: str
    name: str
    employees: int
    critical_employees: int


class EmployeeStatus(BaseModel):
    employee_id: str
    full_name: str
    department: str
    role: str
    grade: str
    progress: float
    status: str


class EventParticipation(BaseModel):
    event_id: str
    title: str
    total: int
    completed: int
    missed: int
    in_progress: int
    overdue: int
    planned: int
    cancelled: int


class HROverview(BaseModel):
    as_of_date: str
    revision: int
    total_employees: int
    average_progress: float
    total_participations: int
    completion_rate: float
    skill_gaps: list[GapCount]
    employees_without_step: list[EmployeeStatus]
    participation: list[EventParticipation]
