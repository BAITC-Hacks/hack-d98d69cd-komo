from typing import Literal
from pydantic import BaseModel, Field
from app.features.development.schemas import ActivityOption


class ModelSelection(BaseModel):
    event_id: str
    fact_ids: list[str]


class ModelPlan(BaseModel):
    selections: list[ModelSelection]


class Evidence(BaseModel):
    fact_id: str
    factor: Literal['grade', 'skill_gap', 'history', 'target_requirements']
    text: str


class RecommendedStep(BaseModel):
    activity: ActivityOption
    explanation: str
    evidence: list[Evidence]


class RecommendationResult(BaseModel):
    run_id: str
    employee_id: str
    revision: int
    source: Literal['ai', 'fallback']
    model: str
    prompt_version: str
    created_at: str
    duration_ms: int
    cached: bool = False
    stale: bool = False
    message: str
    steps: list[RecommendedStep]
    actions: list[str]


class RecommendationState(BaseModel):
    status: Literal['not_generated', 'stale', 'ready', 'no_eligible_step']
    result: RecommendationResult | None
