from pydantic import BaseModel, Field

class EvaluateResumesSchema(BaseModel):
    positions_available: int = Field(gt=0, description="Number of positions faculty wants to fill")
