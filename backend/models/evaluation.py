from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional
from datetime import datetime

class EvaluationBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    route_id: str
    human_journal: str

class EvaluationCreate(EvaluationBase):
    pass

class EvaluationStats(BaseModel):
    mean_f1: float
    min_f1: float
    max_f1: float
    sample_count: int
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

class EvaluationResponse(BaseModel):
    bertscore_f1: float
    bertscore_precision: float
    bertscore_recall: float
    is_equivalent: bool
    human_sentiment: float
    ai_sentiment: float
    human_journal: Optional[str] = None
    ai_travelogue: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    bertscore_model: Optional[str] = None
    travelogue_id: Optional[str] = None
    prompt_type: Optional[str] = None
    is_truncated: bool = False
    pair_f1: list[float] = []
    pair_precision: list[float] = []
    pair_recall: list[float] = []
    pair_is_truncated: list[bool] = []
    human_waypoint_count: Optional[int] = None
    ai_paragraph_count: Optional[int] = None
    stats: Optional[EvaluationStats] = None

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)
