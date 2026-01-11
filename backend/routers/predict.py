# backend/routers/predict.py
from fastapi import APIRouter, HTTPException

from backend.schemas.hallu_input import HalluInput
from backend.schemas.hallu_output import HalluOutput
from backend.model.inference_model import hallu_model

router = APIRouter()

@router.post("/predict", response_model=HalluOutput)
async def predict_hallu(data: HalluInput):
    try:
        result = hallu_model.predict(
            context=data.context,
            prompt=data.prompt,
            response=data.response
        )
        return HalluOutput(
            label=result["label"],
            confidence=result["confidence"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))