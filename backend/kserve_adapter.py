# backend/kserve_adapter.py
import kserve
from typing import Dict

class HallucinationTransformer(kserve.Model):
    def __init__(self, name: str, predictor_host: str):
        super().__init__(name)
        self.predictor_host = predictor_host
        self.ready = True

    def preprocess(self, inputs: Dict) -> Dict:
        return {"instances": [inputs["context"] + " " + inputs["response"]]}

    def preprocess(self, inputs: Dict) -> Dict:
        return {
            "context": inputs.get("context", ""),
            "prompt": inputs.get("prompt", ""),
            "response": inputs.get("response", "")
        }

if __name__ == "__main__":
    transformer = HallucinationTransformer("hallucination-detector", predictor_host="localhost")
    kserve.ModelServer().start([transformer])