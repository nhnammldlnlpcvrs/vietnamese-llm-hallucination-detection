# backend/schemas/hallu_output.py
from pydantic import BaseModel

class HalluOutput(BaseModel):
    label: str
    confidence: float
