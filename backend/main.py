from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.predict import router as predict_router


app = FastAPI(title="Vietnamese Hallucination Detection API", version="1.0")

# Cấu hình CORS (Cho phép frontend gọi vào)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router, prefix="/api", tags=["Hallucination"])

@app.get("/")
def read_root():
    return {"message": "Hallucination Detection API is running"}
