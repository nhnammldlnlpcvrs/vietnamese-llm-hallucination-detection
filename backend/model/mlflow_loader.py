import os
import mlflow
import mlflow.pyfunc
import logging

logger = logging.getLogger(__name__)

MODEL_NAME  = os.getenv("MLFLOW_MODEL_NAME", "vihallu-detector")
MODEL_ALIAS = os.getenv("MLFLOW_MODEL_ALIAS", "production")

_model = None


def load_model_from_mlflow():
    global _model
    if _model is not None:
        return _model

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError(
            "MLFLOW_TRACKING_URI env var is not set. "
            "Set it in your K8s deployment manifest."
        )

    mlflow.set_tracking_uri(tracking_uri)

    model_uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"
    logger.info(f"Loading MLflow model: {model_uri}")

    try:
        _model = mlflow.pyfunc.load_model(model_uri)
    except Exception as e:
        logger.error(f"Failed to load model '{model_uri}': {e}")
        raise RuntimeError(
            f"Could not load model '{MODEL_NAME}' alias '{MODEL_ALIAS}' "
            f"from {tracking_uri}. "
            f"Ensure auto_promote_registry.py has been run. Error: {e}"
        )

    logger.info(f"Model '{MODEL_NAME}@{MODEL_ALIAS}' loaded successfully.")
    return _model


def get_model():
    return load_model_from_mlflow()