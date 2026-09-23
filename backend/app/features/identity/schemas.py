from typing import Literal
from pydantic import BaseModel, Field


class LoginInput(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=200)


class Identity(BaseModel):
    username: str
    role: Literal['employee', 'hr']
    employee_id: str | None
