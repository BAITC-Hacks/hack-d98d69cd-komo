from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class HistoryInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    record_id: str = Field(min_length=1, max_length=100)
    employee_id: str = Field(min_length=1, max_length=100)
    event_id: str = Field(min_length=1, max_length=100)
    date: date
    due_date: date | None
    status: Literal['completed', 'in_progress', 'dropped', 'no_show', 'declined', 'overdue']
    completion_pct: int = Field(ge=0, le=100)
    score: int | None = Field(ge=0, le=100)
    feedback_rating: int | None = Field(ge=1, le=5)
    assigned_by: Literal['self', 'manager', 'hr']

    @model_validator(mode='after')
    def valid_completion(self):
        if self.status == 'completed' and self.completion_pct != 100:
            raise ValueError('Завершенная активность должна иметь completion_pct=100')
        if self.status in ('no_show', 'declined') and self.completion_pct != 0:
            raise ValueError('Для no_show/declined completion_pct должен быть 0')
        if self.status in ('in_progress', 'overdue') and self.completion_pct > 95:
            raise ValueError('Для незавершенной активности completion_pct не выше 95')
        if self.status == 'dropped' and not 5 <= self.completion_pct <= 95:
            raise ValueError('Для dropped completion_pct от 5 до 95')
        return self


class SkillState(BaseModel):
    skill_id: str
    name: str
    current: int
    required: int
    gap: int
    critical: bool


class SkillGain(BaseModel):
    skill_id: str
    name: str
    before: int
    after: int
    required: int


class LearningResource(BaseModel):
    title: str
    url: str = Field(pattern=r'^https://[^\s]+$')
    source: str
    description: str
    language: str


class ActivityOption(BaseModel):
    event_id: str
    title: str
    description: str
    format: str
    duration_hours: float
    resources: list[LearningResource] = Field(default_factory=list)
    next_session: str | None
    action: Literal['start', 'continue']
    gains: list[SkillGain]
    can_complete: bool
    record_id: str | None
    preparatory_for: list[str] = Field(default_factory=list)
    preparatory_critical_skills: list[str] = Field(default_factory=list)
    preparatory_sessions: dict[str, str] = Field(default_factory=dict)
    sessions: list[str] = Field(default_factory=list)
    participation_status: str | None = None
    can_cancel: bool = False
    expected_progress: float = 0


class Goal(BaseModel):
    role: str
    grade: str
    inferred: bool
    maintenance: bool
    source: Literal['profile', 'manual', 'automatic'] = 'profile'


class Development(BaseModel):
    employee_id: str
    as_of_date: str
    revision: int
    context_version: str = ''
    goal: Goal
    progress: float
    skills: list[SkillState]
    critical_gaps: int
    available_events: list[ActivityOption]
    participations: list[ActivityOption] = Field(default_factory=list)
    availability_reasons: list[str] = Field(default_factory=list)
    uncovered_critical_skills: list[str] = Field(default_factory=list)


class HistoryView(BaseModel):
    record_id: str
    event_id: str
    title: str
    date: str
    status: str
    completion_pct: int
    score: int | None
    feedback_rating: int | None


class CompletionInput(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100)
    record_id: str | None = None
    session_date: date | None = None


class ParticipationResult(BaseModel):
    record_id: str
    status: str
    development: Development


class CompletionResult(BaseModel):
    record_id: str
    gains: list[SkillGain]
    before_progress: float
    development: Development
