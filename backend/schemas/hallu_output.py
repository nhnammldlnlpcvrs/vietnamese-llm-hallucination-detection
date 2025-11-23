from pydantic import BaseModel

class HalluOutput(BaseModel):
    label: str
    confidence: float