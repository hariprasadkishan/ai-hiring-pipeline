import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

class OpeningCreateSchema(BaseModel):
    title: str
    program_type: str  # 'MTech' or 'PhD'
    department: str
    description: Optional[str] = None
    research_areas: Optional[List[str]] = []
    preferred_skills: Optional[List[str]] = []
    min_gpa: float = Field(gt=0, le=10.0)
    min_gate_score: Optional[float] = None
    prerequisites: List[str]
    syllabus_topics: List[str]
    start_date: datetime.datetime
    end_date: datetime.datetime

    @model_validator(mode='after')
    def validate_dates(self) -> 'OpeningCreateSchema':
        if self.end_date <= self.start_date:
            raise ValueError('End date must be after start date')
        return self
