from pydantic import BaseModel

class HalluInput(BaseModel):
    context: str
    prompt: str
    response: str
