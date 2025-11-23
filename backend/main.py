from fastapi import FastAPI
from backend.routers.predict import router as predict_router

app = FastAPI(
    title="LLM Hallucination Detection",
    version="1.0.0"
)

# include routes
app.include_router(predict_router, prefix="/api")