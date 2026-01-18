# backend/kserve_adapter.py
import kserve
from typing import Dict
from backend.model.inference_model import get_hallu_model

class HallucinationModel(kserve.Model):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name
        self.model_wrapper = get_hallu_model()
        self.load()

    def load(self):
        print("KServe: Loading Hallucination Pipeline...")
        self.model_wrapper._load_models()
        self.ready = True

    def predict(self, payload: Dict, headers: Dict[str, str] = None) -> Dict:
        try:
            inputs = payload.get("inputs", [])

            data = inputs[0]["data"][0] 
            
            result = self.model_wrapper.predict(
                context=data.get("context"),
                prompt=data.get("prompt"),
                response=data.get("response")
            )
            
            return {
                "predictions": [result]
            }
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    model = HallucinationModel("phobert-hallucination")
    kserve.ModelServer().start([model])