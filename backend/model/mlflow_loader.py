# backend/model/mlflow_loader.py
import mlflow
import os

MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "vihallu-lgbm")
MODEL_STAGE = os.getenv("MLFLOW_MODEL_STAGE", "Production")

def load_model_from_mlflow():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))

    model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"
    model = mlflow.pyfunc.load_model(model_uri)

    return model