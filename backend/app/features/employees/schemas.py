from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

Grade = Literal['Junior', 'Middle', 'Senior', 'Lead']
Level = Annotated[int, Field(strict=True, ge=0, le=5)]


class CareerGoal(BaseModel):
    target_role: str
    target_grade: Grade


class GoalInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    career_goal: CareerGoal | None


class AccessInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    password: str = Field(min_length=10, max_length=128)


class EmployeeAccess(BaseModel):
    username: str | None


class RoleOption(BaseModel):
    role: str
    grade: Grade
    required_skills: dict[str, int]
    critical_skills: list[str]
    skill_names: dict[str, str]


class EmployeeProfile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    employee_id: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')
    full_name: str = Field(min_length=1, max_length=200)
    department: str = Field(min_length=1, max_length=200)
    role: str
    grade: Grade
    manager_id: str | None
    hire_date: date
    tenure_months: int = Field(ge=0)
    work_format: Literal['office', 'hybrid', 'remote']
    preferred_language: Literal['kk', 'ru', 'en']
    career_goal: CareerGoal | None
    skills: dict[str, Level]
    last_review_date: date

    @model_validator(mode='after')
    def dates(self):
        if self.hire_date > self.last_review_date:
            raise ValueError('Дата оценки не может предшествовать приему на работу')
        return self


class EmployeeView(EmployeeProfile):
    is_test: bool = False
