# backend/routers/predict.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.schemas.hallu_input import HalluInput
from backend.schemas.hallu_output import HalluOutput
from backend.model.inference_model import get_hallu_model

router = APIRouter()

hallu_model = get_hallu_model()


@router.post("/predict", response_model=HalluOutput)
def predict_hallu(data: HalluInput):
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
        raise HTTPException(
        status_code=500,
        detail=str(e)
    )



@router.post("/warmup")
def warmup_model(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(
            hallu_model.predict,
            "warmup context",
            "warmup prompt",
            "warmup response"
        )
        return {"message": "Model warmup triggered in background"}

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal model error"
        )