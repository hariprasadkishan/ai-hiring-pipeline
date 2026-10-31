from typing import Optional
from pydantic import BaseModel, Field

class EvaluateResumesSchema(BaseModel):
    positions_available: int = Field(gt=0, description="Number of positions faculty wants to fill")
    force_reevaluate: Optional[bool] = Field(default=False, description="Whether to re-evaluate resumes that already have scores")

