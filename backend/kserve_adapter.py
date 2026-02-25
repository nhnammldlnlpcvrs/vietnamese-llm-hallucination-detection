# backend/kserve_adapter.py
import kserve
from typing import Dict


class HallucinationTransformer(kserve.Model):
    def __init__(self, name: str, predictor_host: str):
        super().__init__(name)
        self.predictor_host = predictor_host
        self.ready = True

    def preprocess(self, inputs: Dict) -> Dict:
        """Parse KServe v2 input format → backend format."""
        # KServe v2 format:
        # {"inputs": [{"name": "context", "data": ["..."]}, ...]}
        parsed = {}
        for inp in inputs.get("inputs", []):
            parsed[inp["name"]] = inp["data"][0]

        return {
            "context":  parsed.get("context", ""),
            "prompt":   parsed.get("prompt", ""),
            "response": parsed.get("response", ""),
        }

    def postprocess(self, outputs: Dict) -> Dict:
        """Parse predictor output → KServe v2 response format."""
        # outputs từ mlserver: {"predictions": [{"label": "no", "confidence": 0.95}]}
        prediction = outputs.get("predictions", [{}])[0]
        return {
            "outputs": [
                {
                    "name": "label",
                    "datatype": "BYTES",
                    "shape": [1],
                    "data": [prediction.get("label", "unknown")]
                },
                {
                    "name": "confidence",
                    "datatype": "FP32",
                    "shape": [1],
                    "data": [prediction.get("confidence", 0.0)]
                }
            ]
        }


if __name__ == "__main__":
    transformer = HallucinationTransformer(
        "hallucination-detector",
        predictor_host="localhost"
    )
    kserve.ModelServer().start([transformer])
