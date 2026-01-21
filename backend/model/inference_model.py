# backend/model/inference_model.py
import os
import numpy as np
from dotenv import load_dotenv
from typing import TYPE_CHECKING, Dict, Any, Union

if TYPE_CHECKING:
    import torch
    import lightgbm as lgb
    from transformers import (
        PreTrainedTokenizer, 
        PreTrainedModel,
        Pipeline as HFPipeline
    )

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

PHOBERT_FINETUNED_PATH = os.getenv("MODEL_PATH", "vinai/phobert-base")
LGBM_PATH = os.path.join(BASE_DIR, "models/lgbm_final_fold_0.txt")
NLI_MODEL_NAME = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
NER_MODEL_NAME = "undertheseanlp/vietnamese-ner-v1.4.0a2"
VISTRAL_MODEL_NAME = "Viet-Mistral/Vistral-7B-Chat"

MODEL_PATH = os.getenv("MODEL_PATH", "models/phobert_finetuned_model")
DISABLE_MODEL = os.getenv("DISABLE_MODEL", "false").lower() == "true"


class HallucinationPipeline:
    API_LABEL_MAP = {
        "No Hallucination": "no",
        "Intrinsic Hallucination": "intrinsic",
        "Extrinsic Hallucination": "extrinsic",
    }

    def __init__(self):
        self.disabled = DISABLE_MODEL
        self._is_loaded = False
        
        self.labels = {
            0: "Extrinsic Hallucination",
            1: "No Hallucination",
            2: "Intrinsic Hallucination"
        }

        self.embed_tokenizer = None
        self.embed_model = None
        self.nli_tokenizer = None
        self.nli_model = None
        self.ner_pipeline = None
        self.vistral_tokenizer = None
        self.vistral_model = None
        self.lgbm_model = None
        self.device_cpu = None
        self.torch_module = None

    def _load_models(self):
        if self._is_loaded or self.disabled:
            return

        print("Initializing HallucinationPipeline Resources (Lazy Loading)...")
        
        import torch
        import torch.nn.functional as F
        import lightgbm as lgb
        from transformers import (
            AutoTokenizer, 
            AutoModel, 
            AutoModelForCausalLM, 
            AutoModelForSequenceClassification, 
            pipeline, 
            BitsAndBytesConfig
        )
        from huggingface_hub import login

        self.torch_module = torch 
        self.device_cpu = torch.device("cpu")

        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            login(token=hf_token)

        try:
            print(f"- Loading PhoBERT (CPU)...")
            self.embed_tokenizer = AutoTokenizer.from_pretrained(PHOBERT_FINETUNED_PATH)
            self.embed_model = AutoModel.from_pretrained(PHOBERT_FINETUNED_PATH).to(self.device_cpu).eval()

            print(f"- Loading NLI (CPU)...")
            self.nli_tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)
            self.nli_model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL_NAME).to(self.device_cpu).eval()

            print(f"- Loading NER (CPU)...")
            try:
                self.ner_pipeline = pipeline("ner", model=NER_MODEL_NAME, tokenizer=NER_MODEL_NAME, 
                                             device=-1, aggregation_strategy="simple")
            except Exception:
                fallback = "NlpHUST/ner-bert-base"
                self.ner_pipeline = pipeline("ner", model=fallback, tokenizer=fallback, 
                                             device=-1, aggregation_strategy="simple")

            print(f"- Loading Vistral 7B (GPU/Offload)...")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                llm_int8_enable_fp32_cpu_offload=True
            )
            
            self.vistral_tokenizer = AutoTokenizer.from_pretrained(VISTRAL_MODEL_NAME)
            self.vistral_model = AutoModelForCausalLM.from_pretrained(
                VISTRAL_MODEL_NAME,
                quantization_config=bnb_config,
                device_map="auto", 
                offload_folder="offload"
            )

            print(f"- Loading LightGBM...")
            self.lgbm_model = lgb.Booster(model_file=LGBM_PATH)
            
            self._is_loaded = True
            print("System Ready!")

        except Exception as e:
            print(f"Critical Error loading models: {e}")
            raise e

    def _extract_embeddings(self, text_list):
        import torch 
        
        inputs = self.embed_tokenizer(text_list, padding=True, truncation=True, max_length=256, return_tensors="pt").to(self.device_cpu)
        with torch.no_grad():
            outputs = self.embed_model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
        return embeddings

    def _feat_engineer_simple(self, context, prompt, response):
        feats = []
        for text in [context, prompt, response]:
            s = str(text) if text else ""
            feats.append(len(s))
            feats.append(len(s.split()))
        return np.array([feats])

    def _get_entity_set(self, text):
        if not text: return set()
        try:
            entities = self.ner_pipeline(text)
            return {e['word'].replace(" ", "").lower() for e in entities}
        except: return set()

    def _get_ner_features(self, context, response):
        c_ents = self._get_entity_set(context)
        r_ents = self._get_entity_set(response)
        new_entity_count = len(r_ents - c_ents)
        union = len(c_ents.union(r_ents))
        overlap_ratio = len(c_ents.intersection(r_ents)) / union if union > 0 else 0.0
        return np.array([[new_entity_count, overlap_ratio]])

    def _get_nli_features(self, context, response):
        import torch # Lazy import reference

        premise = context if context else "no context"
        hypothesis = response if response else "no response"

        inputs = self.nli_tokenizer(
            premise,
            hypothesis,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device_cpu)

        with torch.no_grad():
            outputs = self.nli_model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()[0]

        id2label = self.nli_model.config.id2label

        p_entail = probs[[i for i, v in id2label.items() if "entail" in v.lower()][0]]
        p_neutral = probs[[i for i, v in id2label.items() if "neutral" in v.lower()][0]]
        p_contra = probs[[i for i, v in id2label.items() if "contradict" in v.lower()][0]]

        return p_entail, p_neutral, p_contra

    def _get_vistral_probs(self, context, prompt, response):
        import torch
        import torch.nn.functional as F

        sys_msg = """Bạn là chuyên gia thẩm định độ trung thực của AI (Hallucination Judge).
        Nhiệm vụ: Dựa vào 'Context', hãy phân loại 'Response' vào đúng 1 trong 3 nhãn: 0, 1, hoặc 2.
        
        === ĐỊNH NGHĨA NHÃN (HÃY TUÂN THỦ NGHIÊM NGẶT) ===
        
        1. NO Hallucination (Nhãn 1):
           Phản hồi là "no" KHI VÀ CHỈ KHI đáp ứng đủ cả 3 điều kiện:
           - Nó hoàn toàn nhất quán và đúng sự thật với thông tin được cung cấp trong context.
           - Nó không chứa bất kỳ thông tin nào sai lệch hoặc không thể suy luận trực tiếp từ context.
           - Nó trả lời đúng dựa trên context.
           
        2. EXTRINSIC Hallucination (Nhãn 0) - Lỗi Ngoại Lai:
           Phản hồi là "EXTRINSIC" khi đáp ứng tối thiểu 1 trong các điều kiện:
           - Nó bổ sung thông tin KHÔNG CÓ trong context.
           - Thông tin bổ sung không thể suy luận được từ context.
           - Thông tin bổ sung có thể đúng trong thế giới thực nhưng nó không được cung cấp trong context.
           - Phản hồi vẫn cố gắng trả lời prompt nhưng lại đưa thêm chi tiết không có nguồn gốc từ context.
           
        3. INTRINSIC Hallucination (Nhãn 2) - Lỗi Nội Tại:
           Phản hồi là "INTRINSIC" khi đáp ứng tối thiểu 1 trong các điều kiện:
           - Nó mâu thuẫn trực tiếp hoặc bóp méo thông tin đã được cung cấp rõ ràng trong context.
           - Nội dung của ảo giác vẫn dựa trên các thực thể hoặc khái niệm có trong context nhưng thông tin về chúng bị thay đổi, sai lệch.
           - LLM tạo ra một câu trả lời sai lệch nhưng nghe có vẻ khá hợp lý (plausible) trong ngữ cảnh đó.
        """

        user_msg = f"""Dựa vào các định nghĩa trên, hãy phân loại trường hợp sau:

        Context: {context}
        Prompt: {prompt}
        Response: {response}

        Chỉ trả lời duy nhất một con số đại diện cho nhãn (0, 1 hoặc 2):"""

        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg}
        ]
        
        input_text = self.vistral_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.vistral_tokenizer(input_text, return_tensors="pt").to(self.vistral_model.device)

        with torch.no_grad():
            outputs = self.vistral_model(**inputs)
            next_token_logits = outputs.logits[0, -1, :]
            
            def get_id(token_str):
                ids = self.vistral_tokenizer.encode(token_str, add_special_tokens=False)
                return ids[-1] if ids else -1

            id_0 = get_id("0")
            id_1 = get_id("1")
            id_2 = get_id("2")

            score_0 = next_token_logits[id_0].item()
            score_1 = next_token_logits[id_1].item()
            score_2 = next_token_logits[id_2].item()
            
            probs = F.softmax(torch.tensor([score_0, score_1, score_2]), dim=0).numpy()
            
            return np.array([[probs[0], probs[2], probs[1]]])
        
    def _normalize_label(self, label: str) -> str:
        label = label.lower()
        if "intrinsic" in label:
            return "intrinsic"
        if "extrinsic" in label:
            return "extrinsic"
        return "no"

    def predict(self, context, prompt, response) -> Dict[str, Union[str, float]]:
        if self.disabled:
            return {"label": "no", "confidence": 1.0}
        
        if not self._is_loaded:
            self._load_models()

        # lazy import
        from sklearn.metrics.pairwise import cosine_similarity
        
        print("\n--- PROCESSING REQUEST (GUARDRAIL V3: EXTRINSIC HUNTER) ---")
        c, p, r = str(context).strip(), str(prompt).strip(), str(response).strip()
        
        f_embed = self._extract_embeddings([f"{c} {p} {r}"])
        f_simple = self._feat_engineer_simple(c, p, r)
        
        c_emb = self._extract_embeddings([c])
        r_emb = self._extract_embeddings([r])
        f_sim = cosine_similarity(c_emb, r_emb)
        
        p_entail, p_neutral, p_contra = self._get_nli_features(c, r)
        f_nli = np.array([[p_entail, p_neutral, p_contra]])
        
        print(f"- [NLI Debug] Contra (Int): {p_contra:.4f} | Neu (Ext): {p_neutral:.4f} | Entail (No): {p_entail:.4f}")

        f_ner = self._get_ner_features(c, r)
        new_entity_count = f_ner[0][0]
        overlap_ratio = f_ner[0][1]
        print(f"- [NER Debug] New Entities: {new_entity_count} | Overlap: {overlap_ratio:.2f}")

        print("- Asking Vistral...")
        f_vistral = self._get_vistral_probs(c, p, r)
        print(f"- [Vistral Debug] Ext: {f_vistral[0][0]:.4f} | Int: {f_vistral[0][1]:.4f} | No: {f_vistral[0][2]:.4f}")

        x_final = np.hstack([f_embed, f_simple, f_sim, f_nli, f_ner, f_vistral])
        
        preds = self.lgbm_model.predict(x_final)
        
        class_id = np.argmax(preds[0])
        confidence = preds[0][class_id]
        original_label = self.labels.get(int(class_id), "Unknown")
        print(f"- [LightGBM Opinion] Label: {original_label} ({confidence:.4f})")

        # logic rules
        if p_contra > 0.5:
            print("GUARDRAIL: NLI Contradiction cao -> Force Intrinsic")
            return {
                "label": self._normalize_label("Intrinsic Hallucination"),
                "confidence": float(p_contra)
            }

        if p_neutral > 0.45 and p_entail < 0.5:
            print("GUARDRAIL: NLI Neutral cao (Thong tin ngoai le) -> Force Extrinsic")
            return {
                "label": self._normalize_label("Extrinsic Hallucination"),
                "confidence": float(p_neutral)
            }

        if new_entity_count >= 1 and class_id == 1:
            if p_entail < 0.9:
                print("GUARDRAIL: Có thuc the la va Entailment khong tuyet doi -> Force Extrinsic")
                return {
                    "label": "extrinsic",
                    "confidence": 0.85
                }

        if f_vistral[0][0] > 0.6:
             print("GUARDRAIL: Vistral vote Extrinsic rat cao -> Force Extrinsic")
             return {
                "label": "extrinsic",
                "confidence": float(f_vistral[0][0])
            }

        if p_contra > 0.35 and class_id == 1:
             print("Soft Warning: Co tin hieu mau thuan nhe. Tra ve Intrinsic.")
             return {
                "label": "intrinsic",
                "confidence": float(p_contra)
            }

        return {
            "label": self._normalize_label(original_label),
            "confidence": float(confidence)
        }
    
# Singleton Instance
_pipeline_instance = None

def get_hallu_model() -> HallucinationPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = HallucinationPipeline()
    return _pipeline_instance

hallu_model = get_hallu_model()