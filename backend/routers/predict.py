from fastapi import APIRouter, HTTPException
from schemas.hallu_input import HalluInput
from schemas.hallu_output import HalluOutput
from model.inference_model import hallu_model

router = APIRouter()

@router.post("/predict", response_model=HalluOutput)
async def predict_hallu(data: HalluInput):
    """
    Endpoint nhận Context, Prompt, Response và trả về nhãn Hallucination.
    """
    try:
        result = hallu_model.predict(
            context=data.context,
            prompt=data.prompt,
            response=data.response
        )
        
        # Map kết quả từ dict sang Pydantic Schema
        return HalluOutput(
            label=result["label"],
            confidence=result["confidence"]
        )
        
    except Exception as e:
        # Log lỗi ra terminal để debug
        print(f"Error during prediction: {e}")
        # Trả về lỗi 500 cho client
        raise HTTPException(status_code=500, detail=str(e))