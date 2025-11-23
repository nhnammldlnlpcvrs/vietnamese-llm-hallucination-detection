from fastapi import APIRouter
from backend.schemas.hallu_input import HalluInput
from backend.schemas.hallu_output import HalluOutput
from backend.model.inference_model import hallu_model
from backend.utils.preprocessing import clean_text

router = APIRouter()

@router.post("/predict", response_model=HalluOutput)
def predict(data: HalluInput):
    context = clean_text(data.context)
    prompt = clean_text(data.prompt)
    response = clean_text(data.response)

    output = hallu_model.predict(context, prompt, response)
    return HalluOutput(**output)