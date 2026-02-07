# backend/model/mlflow_loader.py
import os
import mlflow
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "vihallu-lightgbm")
MODEL_STAGE = os.getenv("MLFLOW_MODEL_STAGE", "Production")

_model = None 


def load_model_from_mlflow():
    global _model

    if _model is not None:
        return _model

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI is not set")

    mlflow.set_tracking_uri(tracking_uri)

    model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"

    logger.info(f"Loading MLflow model from registry: {model_uri}")

    _model = mlflow.pyfunc.load_model(model_uri)

    logger.info("MLflow model loaded successfully")

    return _model