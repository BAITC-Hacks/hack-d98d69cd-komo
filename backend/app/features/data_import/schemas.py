from datetime import date
from pydantic import BaseModel, Field
from app.features.employees.schemas import EmployeeProfile


class DatasetMeta(BaseModel):
    dataset: str
    version: str
    as_of_date: date


class EmployeeBundle(BaseModel):
    meta: DatasetMeta
    employees: list[EmployeeProfile] = Field(min_length=1, max_length=2000)


class ImportResult(BaseModel):
    employees_created: int
    employees_updated: int
    history_created: int
    history_updated: int
    revision: int
    employee_ids: list[str]
    message: str
